import os
import shutil
from dotenv import load_dotenv

print("--- 🔍 COGNIVIEW DIAGNOSTIC TOOL (UPDATED) ---")

# 1. CHECK CONFIGURATION
print("\n[Step 1] Checking Configuration...")
load_dotenv()
key = os.getenv("GROQ_API_KEY")
if key:
    print(f"✅ API Key found: {key[:4]}...{key[-4:]}")
else:
    print("❌ API Key NOT found in .env!")

# 2. CHECK FFMPEG
print("\n[Step 2] Checking FFmpeg...")
ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path:
    print(f"✅ FFmpeg found at: {ffmpeg_path}")
else:
    print("❌ FFmpeg NOT found in system PATH.")
    print("   Please install FFmpeg or add it to your PATH variables.")

# 3. CHECK SERVICES
print("\n[Step 3] Verifying Service Imports...")
try:
    from services import ai_service, media_service, db_service
    print("✅ Services imported successfully.")
except Exception as e:
    print(f"❌ Service Import Failed: {e}")

print("\nDiagnostic complete.")