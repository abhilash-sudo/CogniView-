import os
import whisper
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load AI Model
print("⏳ Loading Whisper Model...")
model = whisper.load_model("base")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No filename"}), 400

    # Save video
    filepath = os.path.join(UPLOAD_FOLDER, "uploaded_video.mp4")
    file.save(filepath)

    # Run AI
    print("🎬 Transcribing...")
    result = model.transcribe(filepath)
    
    return jsonify({
        "status": "success",
        "segments": result['segments']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)