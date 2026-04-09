import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static')
SLIDES_FOLDER = os.path.join(UPLOAD_FOLDER, 'slides')
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')
REPORTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'reports')
DB_FILE = os.path.join(BASE_DIR, "cogniview.db")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# Create directories if they don't exist
for f in [UPLOAD_FOLDER, SLIDES_FOLDER, AUDIO_FOLDER, REPORTS_FOLDER]:
    os.makedirs(f, exist_ok=True)
