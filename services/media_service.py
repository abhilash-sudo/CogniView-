import os
import re
import cv2
import numpy as np
import whisper
import easyocr
import torch
import yt_dlp
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from config import UPLOAD_FOLDER, SLIDES_FOLDER

# --- INITIALIZATION ---
print("[Media] Initializing media systems...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[Media] Hardware detected: {device.upper()}")

print("[Media] Loading OCR...")
reader = easyocr.Reader(['en'], gpu=(device == "cuda")) 

print("[Media] Loading Whisper...")
model = whisper.load_model("tiny", device=device)

print("[Media] Systems ready.")

# --- FUNCTIONS ---
def get_youtube_transcript_fast(video_url):
    print("[Transcript] Attempting instant transcript fetch...")
    try:
        video_id = re.search(r"(?:v=|\/)([\w-]{11})", video_url)
        if not video_id: return None, None
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id.group(1))
        formatted_text = ""
        segments = []
        for t in transcript_list:
            start = int(t['start'])
            text = t['text']
            m, s = divmod(start, 60)
            formatted_text += f"[{m:02d}:{s:02d}] {text}\n"
            segments.append({"start": start, "text": text})
        print("[Transcript] Instant transcript loaded.")
        return formatted_text, segments
    except: return None, None

def process_audio(video_path, progress_callback=None):
    if progress_callback: progress_callback("Processing Audio (Whisper)...")
    print("[Whisper] Audio processing started...")
    try:
        use_fp16 = (device == "cuda")
        result = model.transcribe(video_path, fp16=use_fp16)
        timestamped_text = ""
        for segment in result["segments"]:
            m, s = divmod(int(segment['start']), 60)
            timestamped_text += f"[{m:02d}:{s:02d}] {segment['text']}\n"
        print("[Whisper] Audio complete.")
        return timestamped_text, result["segments"]
    except Exception as e: 
        print(f"Audio processing error: {e}")
        return "", []

def process_visuals(video_path, progress_callback=None):
    if progress_callback: progress_callback("Scanning Visuals (OCR)...")
    print("[Vision] Visual processing started...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[Vision] Error: Could not open video for visuals processing.")
        return [], ""

    saved_slides = []
    full_ocr_text = ""
    last_frame_small = None
    slide_count = 0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0: fps = 24 
    frame_interval = fps * 2 

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame_id = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        
        # Update progress occasionally
        if progress_callback and frame_id % (frame_interval * 5) == 0:
            percent = int((frame_id / total_frames) * 100)
            progress_callback(f"Scanning Visuals: {percent}%")

        if frame_id % frame_interval != 0: continue
        try:
            small_frame = cv2.resize(frame, (64, 64))
            gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            if last_frame_small is None: is_unique = True
            else:
                score = np.mean(np.abs(gray_small - last_frame_small))
                is_unique = score > 10 
            if is_unique:
                seconds = frame_id / fps
                m, s = divmod(int(seconds), 60)
                time_str = f"{m:02d}:{s:02d}"
                timestamp = int(datetime.now().timestamp())
                fname = f"slide_{timestamp}_{slide_count}.jpg"
                cv2.imwrite(os.path.join(SLIDES_FOLDER, fname), frame)
                saved_slides.append(fname)
                results = reader.readtext(frame, detail=0)
                text = " ".join(results)
                if text.strip(): full_ocr_text += f"[Visual Note {slide_count+1} @ {time_str}]: {text}\n"
                last_frame_small = gray_small
                slide_count += 1
        except: continue
    cap.release()
    print(f"[Vision] Visuals complete. Found {len(saved_slides)} slides.")
    return saved_slides, full_ocr_text

def download_youtube_video(url, output_filename=None):
    print(f"[YouTube] Downloading: {url}")
    if not output_filename:
        output_filename = f"video_{int(datetime.now().timestamp())}.mp4"
    filepath = os.path.join(UPLOAD_FOLDER, output_filename)
    
    # Removed hardcoded ffmpeg_location, relying on system PATH
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': filepath,
        'merge_output_format': 'mp4', 'quiet': True, 'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    return output_filename
