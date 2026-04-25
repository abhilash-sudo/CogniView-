from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
import json
import re
import hashlib
from datetime import datetime
from gtts import gTTS
from fpdf import FPDF
from deep_translator import GoogleTranslator
from duckduckgo_search import DDGS

from config import (
    UPLOAD_FOLDER, AUDIO_FOLDER, REPORTS_FOLDER, SLIDES_FOLDER, 
    DB_FILE, CHROMA_DB_PATH
)
from services import db_service, ai_service, media_service

app = Flask(__name__)

# --- INITIALIZATION ---
print("✅ Server Imports Complete. Initializing DB...")
db_service.init_db()
ddgs = DDGS()

current_video_data = {} 

def clean_json_output(text):
    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1: return text[start:end]
        return "[]"
    except: return "[]"

def api_ok(data=None, status=200):
    return jsonify({"ok": True, "data": data, "error": None}), status

def api_error(message, status=400, code="bad_request"):
    return jsonify({"ok": False, "data": None, "error": {"code": code, "message": message}}), status

# --- ROUTES ---
@app.route("/")
def index():
    with db_service.sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = db_service.sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, title, date_added FROM videos ORDER BY id DESC")
        library = c.fetchall()
    return render_template("index.html", library=library)

@app.route("/search", methods=["POST"])
def global_search():
    query = request.json.get("query", "").lower()
    if not query: return jsonify([])
    with db_service.sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = db_service.sqlite3.Row
        c = conn.cursor()
        c.execute("""SELECT id, title, date_added FROM videos 
                    WHERE lower(title) LIKE ? OR lower(transcript) LIKE ? OR lower(ocr_text) LIKE ?""", 
                (f'%{query}%', f'%{query}%', f'%{query}%'))
        rows = c.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/load/<int:video_id>")
def load_video(video_id):
    global current_video_data
    video = db_service.get_video_by_id(video_id)

    if video:
        combined_memory = video["transcript"] + "\n\n=== TRANSCRIPT OF VISUAL ELEMENTS ===\n" + (video["ocr_text"] or "")
        current_video_data = {
            "id": video["id"],
            "title": video["title"], "memory": combined_memory,
            "filename": video["filename"], "slides": json.loads(video["slides"])
        }
        segments = []
        for line in video["transcript"].strip().split('\n'):
            match = re.match(r"\[(\d+):(\d+)\] (.*)", line)
            if match:
                m, s, txt = match.groups()
                segments.append({"start": int(m)*60 + int(s), "text": txt})
        return render_template("result.html", segments=segments, video_file=video["filename"], slides=current_video_data["slides"], video_id=video["id"])
    return redirect(url_for("index"))

@app.route("/load/<video_id>")
def load_video_fallback(video_id):
    """
    Friendly fallback when users visit placeholder URLs like /load/<video_id>.
    """
    cleaned = (video_id or "").strip()

    # Common placeholder patterns from docs/examples
    if cleaned in {"<video_id>", "{video_id}", ":video_id"}:
        latest = db_service.get_latest_video()
        if latest:
            return redirect(url_for("load_video", video_id=latest["id"]))
        return redirect(url_for("index"))

    # If it's numeric but did not match int route for any reason
    if cleaned.isdigit():
        return redirect(url_for("load_video", video_id=int(cleaned)))

    return redirect(url_for("index"))

@app.route("/load/mediapipe/<path:asset>")
def mediapipe_asset_fallback(asset):
    """
    Compatibility route for stale frontend bundles that resolve MediaPipe assets
    relative to /load/<id>, causing /load/mediapipe/... 404s.
    """
    safe_asset = (asset or "").lstrip("/")
    face_prefix = "face_mesh/"
    hands_prefix = "hands/"
    if safe_asset.startswith(face_prefix):
        rel = safe_asset[len(face_prefix):]
        return redirect(f"https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/{rel}", code=302)
    if safe_asset.startswith(hands_prefix):
        rel = safe_asset[len(hands_prefix):]
        return redirect(f"https://cdn.jsdelivr.net/npm/@mediapipe/hands/{rel}", code=302)
    return redirect(f"https://cdn.jsdelivr.net/npm/@mediapipe/{safe_asset}", code=302)

import threading
import uuid
import time

# --- ASYNC TASK STORAGE ---
TASKS = {}

def background_processor(task_id, filepath, title, youtube_url=None):
    try:
        def update_progress(msg):
            TASKS[task_id]["status"] = msg
            print(f"[{task_id}] {msg}")

        TASKS[task_id]["status"] = "Starting..."
        timestamped_text = None
        segments = None
        filename = os.path.basename(filepath)

        # 1. YouTube Download (if needed)
        if youtube_url:
            update_progress("Downloading YouTube Video...")
            # We already have the filepath from the main thread, but let's ensure consistency
            # If logic required fetching logic here, we'd do it. 
            pass 

        # 2. Audio Processing
        update_progress("Transcribing Audio (Whisper)...")
        if not timestamped_text:
            timestamped_text, segments = media_service.process_audio(filepath, update_progress)

        # 3. Visual Processing
        update_progress("Analyzing Visuals (OCR)...")
        slides, ocr_text = media_service.process_visuals(filepath, update_progress)

        # 4. Database
        update_progress("Saving to Database...")
        vid_id = db_service.save_to_db(title, filename, timestamped_text, slides, ocr_text)

        # 5. Vectorization
        update_progress("Vectorizing Knowledge...")
        combined_memory = timestamped_text + "\n" + ocr_text
        db_service.vectorize_and_store(vid_id, title, combined_memory)
        
        # 6. Concept Extraction (Graph)
        update_progress("Building Knowledge Graph...")
        concepts = ai_service.extract_concepts(combined_memory)
        db_service.save_concepts(vid_id, concepts)

        TASKS[task_id]["status"] = "Completed"
        TASKS[task_id]["video_id"] = vid_id
        TASKS[task_id]["progress"] = 100
        
    except Exception as e:
        TASKS[task_id]["status"] = f"Error: {str(e)}"
        print(f"Task {task_id} failed: {e}")

@app.route("/status/<task_id>")
def get_status(task_id):
    return jsonify(TASKS.get(task_id, {"status": "Unknown Task"}))

@app.route("/graph")
def get_graph():
    data = db_service.get_graph_data()
    return jsonify(data)

@app.route("/mindmap_data", methods=["POST"])
def mindmap_data():
    started = time.time()
    data = request.get_json(silent=True) or {}
    video_id = data.get("video_id")
    
    mem = ""
    title = "Knowledge Graph"
    
    # Prefer explicit video_id from request (most reliable)
    if video_id:
        video = db_service.get_video_by_id(video_id)
        if video:
            title = video["title"]
            mem = (video["transcript"] or "") + "\n\n" + (video["ocr_text"] or "")
    
    # Fallback to in-memory session data
    if not mem and current_video_data:
        mem = current_video_data.get("memory", "")
        title = current_video_data.get("title", title)
    
    # Last resort: latest video in DB
    if not mem:
        vid = db_service.get_latest_video()
        if vid:
            title = vid["title"]
            mem = (vid["transcript"] or "") + "\n\n" + (vid["ocr_text"] or "")
    
    if not mem.strip():
        return jsonify({"error": "No transcript data found. Please process a video first."})
    
    print(f"[MindMap] Building graph for: {title} ({len(mem)} chars)")
    result = ai_service.extract_mindmap_json(mem[:22000])
    print(f"[MindMap] Completed in {time.time() - started:.2f}s")
    result["video_title"] = title  # pass title to frontend for display
    return jsonify(result)


def _get_video_memory(video_id=None):
    """Helper: get transcript memory for a given video_id or current session."""
    if video_id:
        video = db_service.get_video_by_id(video_id)
        if video:
            return video["title"], (video["transcript"] or "") + "\n\n" + (video["ocr_text"] or "")
    if current_video_data:
        return current_video_data.get("title",""), current_video_data.get("memory","")
    vid = db_service.get_latest_video()
    if vid:
        return vid["title"], (vid["transcript"] or "") + "\n\n" + (vid["ocr_text"] or "")
    return "", ""

@app.route("/flashcards_data", methods=["POST"])
def flashcards_data():
    started = time.time()
    data = request.get_json(silent=True) or {}
    title, mem = _get_video_memory(data.get("video_id"))
    if not mem.strip():
        return jsonify({"error": "No transcript found."})
    cards = ai_service.generate_flashcards(mem[:18000])
    print(f"[Flashcards] Completed in {time.time() - started:.2f}s")
    return jsonify({"cards": cards, "title": title})

@app.route("/summary_data", methods=["POST"])
def summary_data():
    started = time.time()
    data = request.get_json(silent=True) or {}
    title, mem = _get_video_memory(data.get("video_id"))
    if not mem.strip():
        return jsonify({"error": "No transcript found."})
    summary = ai_service.generate_summary(mem[:18000])
    print(f"[Summary] Completed in {time.time() - started:.2f}s")
    summary["title"] = title
    return jsonify(summary)

@app.route("/process", methods=["POST"])
def process_video():
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "Queued", "progress": 0}
    
    filename = f"video_{int(datetime.now().timestamp())}.mp4"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    title = "Uploaded Video"
    
    youtube_url = request.form.get("youtube_url")
    
    # Handle Upload/Download synchronously just to get the file
    # Ideally download mimics async too, but keeping it simple:
    # We download first, then async process content.
    try:
        if youtube_url:
            title = f"YouTube: {youtube_url[-11:]}"
            TASKS[task_id]["status"] = "Downloading YouTube..."
            timestamped_text, segments = media_service.get_youtube_transcript_fast(youtube_url) # Try fast fetch first
            # If we got transcript fast, great, but we still need the video for visuals
            # For UX, we do the heavy download here or in thread?
            # Let's do download here so we validate URL immediately.
            filename = media_service.download_youtube_video(youtube_url, filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
        elif "video" in request.files:
            f = request.files["video"]
            f.save(filepath)
            title = f.filename
            
        # Spawn Thread
        thread = threading.Thread(target=background_processor, args=(task_id, filepath, title, youtube_url))
        thread.start()
        
        return jsonify({"task_id": task_id})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/chat", methods=["POST"])
def chat():
    global current_video_data 
    if not current_video_data:
        vid = db_service.get_latest_video()
        if vid:
             current_video_data = {
                "id": vid["id"], "title": vid["title"], 
                "memory": vid["transcript"] + "\n" + (vid["ocr_text"] or ""),
                "filename": vid["filename"], "slides": json.loads(vid["slides"])
             }
        else: return jsonify({"response": "No video loaded."})
    
    user_q = request.json.get("message")
    user_time = request.json.get("timestamp", 0) 
    lang = request.json.get("lang", "en") 

    m, s = divmod(int(user_time), 60)
    time_str = f"{m:02d}:{s:02d}"
    safe_mem = current_video_data["memory"][:30000] 

    if "mind map" in user_q.lower():
        sys = f"""CONTEXT: "{safe_mem}"
TASK: Create a visual, hierarchical text-based Mind Map summarizing the core concepts.
CRITICAL RULES:
1. DO NOT use mermaid or code blocks.
2. Use emojis and bold text to represent main branches and sub-branches.
3. Keep it concise.
Example Format:
🧠 **[Main Topic]**
  ├─ 📂 **[Subtopic 1]**
  │    ├─ [Detail A]
  │    └─ [Detail B]
  └─ 📂 **[Subtopic 2]**
       └─ [Detail C]"""
        res = ai_service.ask_ai(sys, "Create a mind map.")
        return jsonify({"response": res})

    sys = f"""
    You are CogniView. 
    CURRENT STATUS: User at [{time_str}].
    CONTEXT: "{safe_mem}"
    CRITICAL: If user says "Explain this", explain content at [{time_str}].
    Reply in {lang}.
    """
    ai_reply = ai_service.ask_ai(sys, user_q).strip()

    if ai_reply.startswith("SEARCH:"):
        query = ai_reply.replace("SEARCH:", "").strip()
        print(f"🌍 SEARCHING: {query}")
        results = ddgs.text(query, max_results=3)
        search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results]) if results else "No results."
        final_sys = f"You are CogniView. Found these web results:\n{search_context}\nTASK: Answer user in {lang}. Start with 'I found online...'."
        ai_reply = ai_service.ask_ai(final_sys, user_q)

    if lang != "en":
        try: ai_reply = GoogleTranslator(source='auto', target=lang).translate(ai_reply)
        except: pass 
            
    return jsonify({"response": ai_reply})

@app.route("/global_chat", methods=["POST"])
def global_chat():
    user_q = request.json.get("message")
    
    # 1. Semantic Search
    print(f"🧠 Hive Mind Query: {user_q}")
    results = db_service.search_vectors(user_q)
    
    if not results['documents'][0]:
        return jsonify({"response": "I couldn't find any relevant info in your video library. Try uploading more videos!"})

    # 2. Build Context
    combined_context = ""
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        combined_context += f"\n\n--- SOURCE: {meta['title']} ---\n{doc}..."

    # 3. Ask AI
    sys = f"""
    You are the "Hive Mind" of the user's video library.
    USER QUERY: "{user_q}"
    RELEVANT KNOWLEDGE (Retrieved via Semantic Search):
    {combined_context}
    INSTRUCTIONS:
    - Synthesize an answer based ONLY on the Retrieved Knowledge.
    - Cite the video titles (e.g. "According to 'Biology 101'...")
    - Explain the connection between the concepts.
    """
    
    ai_reply = ai_service.ask_ai(sys, user_q)
    return jsonify({"response": ai_reply})

@app.route("/get_notes/<int:video_id>")
def get_notes(video_id):
    with db_service.sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = db_service.sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM notes WHERE video_id = ? ORDER BY timestamp ASC", (video_id,))
        notes = [dict(r) for r in c.fetchall()]
    return jsonify(notes)

@app.route("/save_note", methods=["POST"])
def save_note():
    data = request.json
    with db_service.sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO notes (video_id, timestamp, text, created_at) VALUES (?, ?, ?, ?)",
                (data['video_id'], data['timestamp'], data['text'], datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
    return jsonify({"status": "saved"})

@app.route("/health")
def health():
    diagnostics = {"db": "ok", "vector": "ok", "ai": "ok", "media": "ok"}
    try:
        with db_service.sqlite3.connect(DB_FILE) as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        diagnostics["db"] = f"error: {e}"
    try:
        _ = db_service.vector_collection.count()
    except Exception as e:
        diagnostics["vector"] = f"error: {e}"
    return jsonify({
        "status": "ok" if all(v == "ok" for v in diagnostics.values()) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": diagnostics
    })

def _wrap_api(handler):
    try:
        data = handler()
        return api_ok(data)
    except Exception as e:
        return api_error(str(e), status=500, code="internal_error")

@app.route("/api/v1/chat", methods=["POST"])
def api_v1_chat():
    def _handler():
        response = chat().get_json()
        return response
    return _wrap_api(_handler)

@app.route("/api/v1/summary", methods=["POST"])
def api_v1_summary():
    return _wrap_api(lambda: summary_data().get_json())

@app.route("/api/v1/flashcards", methods=["POST"])
def api_v1_flashcards():
    return _wrap_api(lambda: flashcards_data().get_json())

@app.route("/api/v1/mindmap", methods=["POST"])
def api_v1_mindmap():
    return _wrap_api(lambda: mindmap_data().get_json())

@app.route("/api/v1/notes/<int:video_id>", methods=["GET"])
def api_v1_get_notes(video_id):
    return _wrap_api(lambda: get_notes(video_id).get_json())

@app.route("/api/v1/notes", methods=["POST"])
def api_v1_save_note():
    return _wrap_api(lambda: save_note().get_json())

@app.route("/magic_fix", methods=["POST"])
def magic_fix():
    user_note = request.json.get("text")
    if not current_video_data: return jsonify({"response": user_note})
    sys = f"CONTEXT: {current_video_data['memory'][:20000]}\nTASK: Rewrite user note '{user_note}' to be academic and accurate."
    polished = ai_service.ask_ai(sys, "Rewrite.")
    return jsonify({"response": polished})

@app.route("/get_pdf")
def get_pdf():
    global current_video_data
    if not current_video_data: return "No video loaded", 400
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Study Guide: {current_video_data.get('title', 'Video')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("Arial", '', 11)
    try:
        sys_sum = f"Summarize lecture in 5 bullets.\nCONTEXT: {current_video_data['memory'][:20000]}"
        summary = ai_service.ask_ai(sys_sum, "Summarize").encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, summary)
    except: pdf.multi_cell(0, 8, "Summary failed.")
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Your Notes", ln=True)
    pdf.set_font("Arial", '', 11)
    try:
        conn = db_service.sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM notes WHERE video_id = ? ORDER BY timestamp ASC", (current_video_data['id'],))
        notes = c.fetchall()
        for n in notes:
            m, s = divmod(int(n[2]), 60)
            note_txt = f"[{m:02d}:{s:02d}] {n[3]}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, note_txt)
        conn.close()
    except: pass
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Key Visual Notes", ln=True)
    slides = current_video_data.get("slides", [])
    for i, slide in enumerate(slides[:6]):
        img_path = os.path.join(SLIDES_FOLDER, slide)
        if os.path.exists(img_path):
            pdf.image(img_path, w=100)
            pdf.ln(2)
            pdf.set_font("Arial", 'I', 9)
            pdf.cell(0, 5, f"Figure {i+1}", ln=True)
            pdf.ln(5)
    
    report_path = os.path.join(REPORTS_FOLDER, "StudyGuide.pdf")
    pdf.output(report_path)
    return send_file(report_path, as_attachment=True)

@app.route("/quiz", methods=["POST"])
def generate_quiz():
    global current_video_data
    if not current_video_data:
        vid = db_service.get_latest_video()
        if vid:
             current_video_data = {
                "title": vid["title"], "memory": vid["transcript"] + "\n" + (vid["ocr_text"] or ""),
                "filename": vid["filename"], "slides": json.loads(vid["slides"])
             }
        else: return jsonify({"error": "No video loaded."})
    sys = f"""CONTEXT: "{current_video_data['memory'][:25000]}"
    TASK: Generate 5 multiple-choice questions. STRICT JSON FORMAT: [{{"q":"?","options":["A","B"],"correct":0}}]"""
    res = ai_service.ask_ai(sys, "Generate Quiz")
    return jsonify({"quiz_data": clean_json_output(res)})

@app.route("/chapters", methods=["POST"])
def generate_chapters():
    global current_video_data
    if not current_video_data:
        vid = db_service.get_latest_video()
        if vid:
             current_video_data = {
                "title": vid["title"], "memory": vid["transcript"] + "\n" + (vid["ocr_text"] or ""),
                "filename": vid["filename"], "slides": json.loads(vid["slides"])
             }
        else: return jsonify({"error": "No video loaded."})
    sys = f"""CONTEXT: "{current_video_data['memory'][:25000]}"
    TASK: Identify 4-8 chapters. STRICT JSON FORMAT: [{{"timestamp": "02:15", "seconds": 135, "title": "Topic Name"}}]"""
    res = ai_service.ask_ai(sys, "Generate Chapters")
    return jsonify({"chapters": clean_json_output(res)})

@app.route("/podcast", methods=["POST"])
def generate_podcast():
    global current_video_data
    if not current_video_data:
        vid = db_service.get_latest_video()
        if vid:
             current_video_data = {
                "title": vid["title"], "memory": vid["transcript"] + "\n" + (vid["ocr_text"] or ""),
                "filename": vid["filename"], "slides": json.loads(vid["slides"])
             }
        else: return jsonify({"error": "No video loaded."})
    
    script = ai_service.generate_podcast_script(current_video_data['memory'])
    return jsonify({"script": script})

@app.route("/speak", methods=["POST"])
def generate_audio():
    text = request.json.get("text")
    if not text: return jsonify({"error": "No text"})
    try:
        clean = re.sub(r'\[\d+:\d+\]', '', text).replace("*", "")
        fname = f"summary_{int(datetime.now().timestamp())}.mp3"
        fpath = os.path.join(AUDIO_FOLDER, fname)
        tts = gTTS(text=clean, lang='en')
        tts.save(fpath)
        return jsonify({"audio_url": f"/static/audio/{fname}"})
    except Exception as e: return jsonify({"error": str(e)})

@app.route("/explain_context", methods=["POST"])
def explain_context():
    global current_video_data
    if not current_video_data:
        vid = db_service.get_latest_video()
        if vid:
             current_video_data = {
                "title": vid["title"], "memory": vid["transcript"] + "\n" + (vid["ocr_text"] or ""),
                "filename": vid["filename"], "slides": json.loads(vid["slides"])
             }
        else: return jsonify({"error": "No video loaded."})
        
    current_time = float(request.json.get("timestamp", 0))
    # We need a chunk of text around this timestamp.
    # The transcript doesn't have exact timestamps per word in this simplified version,
    # but we can do a rough estimation based on length, or just pass the whole memory
    # and ask the AI to explain the topic being discussed around that time.
    
    m, s = divmod(int(current_time), 60)
    time_str = f"{m:02d}:{s:02d}"
    
    # We will pass a chunk of the transcript to the AI service
    mem = current_video_data['memory'][:20000]
    
    # Modify the simplify function slightly in-prompt to handle timestamps if needed, 
    # but for now, passing the memory is okay.
    # Actually, let's just use ask_ai directly here since it's very context specific
    sys = f"""
    You are CogniView's 'Emotion Engine'. The user's facial expression indicates they are HIGHLY CONFUSED by what is currently happening in the video around the timestamp [{time_str}].
    CONTEXT (Video Transcript): "{mem}"
    
    TASK: Look at the context around the {time_str} mark (if timestamps exist) or the general theme.
    Provide a VERY SIMPLE, ELI5 (Explain Like I'm 5) breakdown of the current topic.
    Use an analogy. Be encouraging. Do not exceed 3 sentences.
    Start with: "You look a bit confused! Let me simplify this:"
    """
    
    explanation = ai_service.ask_ai(sys, "Explain the current context simply.")
    return jsonify({"explanation": explanation})

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)