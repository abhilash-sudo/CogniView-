# PROJECT SYNOPSIS: COGNIVIEW - NEURAL INTERFACE FOR SMART LEARNING

## INTRODUCTION
The CogniView system aims to digitally enhance traditional video-based learning by integrating secure, intelligent, and neurologically-aware automation tools. The platform provides AI-based video comprehension, including automated transcription, optical character recognition (OCR), and semantic search across a vast video library using Chroma DB. Advanced computer vision technology powered by MediaPipe Face Mesh drives the "Emotion Engine," which reads user facial expressions to detect confusion (furrowed brow) and provides proactive AI-based context simplification. The "Focus Guard" monitors physical gaze, pausing content when distraction is detected. Smart automation manages timestamped note-taking, multiple-choice quiz generation, and intelligent chapter segmentation. Machine learning-based summarization converts lengthy video lectures into concise, readable Study Guide PDFs and engaging 2-person Neural Podcasts. The system provides a real-time AI Chatbot ("Hive Mind") for instant contextual guidance and global library semantic searches.

## EXISTING SYSTEM
- Standard digital platforms for video playback (e.g., standard media players, basic browser players).
- Passive learning experience with limited interactivity.
- High cognitive load and manual effort required for note-taking and summarization.
- Maintains basic chronological watch history without context retrieval.
- No real-time assessment of user understanding, attention, or psychological state.
- No automated study aid generation (quizzes, podcasts, interactive mind maps).
- Disconnected information retrieval requiring manual web searches.

## DRAWBACKS
- Inefficient study material preparation and high administrative burden on learners.
- Lack of real-time understanding-support tools (if a student is confused, the video keeps playing).
- Delayed learning processes and information overload.
- No engagement verification; users can easily lose focus without intervention.
- No automated mechanisms for knowledge synthesis across multiple video sources.
- No intelligent auditory or visual transformation options (like dynamic podcasts or smart chapters).
- The overall cognitive retention of complex video material is less efficient.

## PROPOSED SYSTEM
- AI-based Emotion Engine detects confusion in real-time, pausing the video to provide extremely simplified, ELI5 (Explain Like I'm 5) breakdowns of the current topic.
- Focus Guard using automated human-gaze tracking to ensure continuous learner engagement.
- AI-based document and video summarization for quick review via auto-generated Study Guide PDFs.
- Semantic Vector Library (Hive Mind) allowing users to chat with their entire database of watched videos.
- AI-powered Neural Podcast generator that transforms video transcripts into lively, 2-person audio dialogues for alternative auditory learning.
- Speed Learn (RSVP - Rapid Serial Visual Presentation) matrix overlays and Binaural Beats (Cerebral Hertz) to optimize brainwave states for relaxation or hyper-focus.
- Faster learning processing through automated quiz generation, mind map creation, and smart video chaptering.

## MODULES

### LEARNER (User)
Ø Secure Video Upload & YouTube Import
Ø Interactive Transcript Viewing
Ø Smart Timestamped Notes
Ø Note Polishing ("Magic Fix")
Ø AI Interactive Chat (Local & Hive Mind)
Ø Study Guide Generation & Download
Ø Neural Podcast Listening
Ø Quiz & Mind Map Generation

### COGNITIVE ENGINE (Monitoring)
Ø Emotion Tracking (Confusion/Furrowed Brow Detection)
Ø Focus Guard (Gaze Tracking)
Ø Telekinesis (Gesture-Based Video Control via Hand Tracking)
Ø Cerebral Hertz (Binaural Beats for Alpha/Theta/Gamma states)
Ø Speed Read (RSVP Matrix Display)

### AI ASSISTANT (Processing)
Ø Audio Transcription (Whisper) & OCR
Ø Context Simplification & Explanation
Ø Smart Chapter Segmentation 
Ø Semantic Vector Embedding (Chroma DB)
Ø Internet Search Integration (DuckDuckGo)
Ø Knowledge Graph Concept Extraction

## WORKFLOW
### DFD
- **LEVEL 0 CONTEXT DIAGRAM:** Overall System Architecture
- **LEVEL 1 LEARNER:** Manage Media & Learning Aids
- **LEVEL 2 LEARNER (Video Processing):** File Upload, Audio Extraction, Transcription, OCR
- **LEVEL 1 AI ASSISTANT:** Natural Language Processing & Summarization
- **LEVEL 2 AI ASSISTANT (Knowledge Query):** Hive Mind Semantic Search & Podcast Generation
- **LEVEL 1 COGNITIVE ENGINE:** Real-Time User Monitoring
- **LEVEL 2 COGNITIVE ENGINE (Feedback Loop):** Face Mesh Analysis -> Confusion Detection -> Auto-Pause -> AI Simplification

## TABLES

**Table : Videos**
| Field Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | int | Primary Key | Video identification number |
| title | varchar | NOT NULL | Title of the video |
| filename | varchar | NOT NULL | Local path for the video file |
| transcript | text | NOT NULL | Full timestamped audio transcript |
| slides | text | NOT NULL | JSON array of extracted visual slides |
| ocr_text | text | NOT NULL | Text extracted via OCR from video frames |
| date_added | varchar | NOT NULL | Upload timestamp |

**Table : Notes**
| Field Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | int | Primary Key | Note ID |
| video_id | int | Foreign Key | Associated Video ID |
| timestamp | float | NOT NULL | Specific video time of the note |
| text | text | NOT NULL | User's note content |
| created_at | varchar | NOT NULL | Note creation date |

**Table : Concepts**
| Field Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | int | Primary Key | Concept ID |
| video_id | int | Foreign Key | Associated Video ID |
| concept_name| varchar | NOT NULL | Extracted knowledge graph phrase |

## TECHNOLOGIES USED
- **Front-end:** HTML, CSS, JavaScript, WebGazer.js, MediaPipe (Face Mesh, Hands)
- **Back-end:** Python, Flask Framework
- **AI/ML:** LLaMA (Groq API), Whisper ASR, gTTS, MediaPipe
- **Database:** SQLite (Relational), ChromaDB (Vector Knowledge Base)
- **Tools:** Visual Studio Code, FPDF, DuckDuckGo Search API

## DATASET USED
- **Custom Knowledge Dataset**
- **Dataset Source:** User-Uploaded Educational Videos and YouTube Transcripts
- **Dataset Type:** Audiovisual streams, timestamped text, OCR extracted frames.
- **Contents:** Lecture videos, presentations, spoken transcripts, and textbook excerpts.
- **Purpose in Project:**
  - Semantic vector search (Hive Mind).
  - Training context for the Emotion Engine's ELI5 simplifications.
  - Generating dynamic quizzes, smart chapters, and interactive podcasts.

## SCREENSHOTS
*(To be attached in the final documentation based on UI rendering)*

## CONCLUSION
The CogniView Neural Interface effectively revolutionizes the digital learning experience. It provides a centralized, highly intelligent platform for learners, researchers, and professionals. Innovative AI features such as real-time context simplification, dynamic summarization, Neural Podcast generation, and Hive Mind chat assist in vastly accelerated learning and knowledge retention. The integration of the Emotion Engine and Focus Guard ensures an unprecedented level of human-computer interaction, monitoring user engagement and adapting the learning environment dynamically. Overall, the proposed system creates a smarter, highly responsive, and efficient educational workflow.

## FUTURE ENHANCEMENT
Ø Mobile Application for easy access and on-the-go biometric tracking.
Ø Integration with real academic repositories for cross-referencing and live fact-checking.
Ø Multilingual AI voice synthesis for real-time video dubbing.
Ø Voice-based interface control for entirely hands-free operation.
Ø Real-time learning analytics dashboard utilizing historical eye-tracking and emotion data.
Ø Integration with AR/VR headsets for immersive 3D learning environments.

## CORE IMPLEMENTATION DETAILS (FOR AI CONTEXT)

*(Note: Provide the following details to the AI assisting you with writing the full documentation to ensure it understands the underlying code mechanics.)*

### 1. Dual-Model AI Architecture (High Availability)
- The system primarily uses the **LLaMA-3.3-70b-versatile** model via the Groq API for heavy conceptual tasks (summarization, podcast generation).
- It features an automatic failover/fallback mechanism to the faster, lighter **LLaMA-3.1-8b-instant** model if the primary "brain" fails, ensuring uninterrupted learning assistance.

### 2. Specific AI AI Agent Prompts & Logic
- **Neural Podcast Generator:** Explicitly formats the transcript into a lively 6-10 exchange JSON-array script between "Alex" (curious host) and "Sam" (expert), using analogies.
- **Emotion Engine Trigger (ELI5 Simplification):** When the frontend Face Mesh detects a furrowed brow (confusion), the backend `explain_context` route is triggered with the timestamp. The prompt forces a 3-sentence, encouraging 10-year-old level breakdown using analogies ("You look a bit confused! Let me simplify this:").
- **Mind Map Logic:** Uses text-based hierarchical branching with emojis (no mermaid rendering issues) directly in the chat UI.
- **Global Web Search Fallback:** If the local video knowledge library (Hive Mind) lacks answers, the `DDGS` (DuckDuckGo Search) API triggers and injects web results into the AI's prompt as context.

### 3. Backend Asynchronous Processing Pipeline
- When a video or YouTube link is submitted, the server spawns an asynchronous `threading.Thread` generating a unique `task_id` (UUID).
- The pipeline executes sequentially in the background without blocking the UI: 
  1. *Audio Processing* (Whisper transcription -> timestamped segments)
  2. *Visual Processing* (OCR on video frames -> JSON slides)
  3. *Database Storage* (SQLite)
  4. *Vectorization* (ChromaDB for semantic search)
  5. *Concept Extraction* (Knowledge Graph generation).
- The frontend continuously polls `/status/<task_id>` to update a real-time progress bar.

### 4. Study Aid Generation Tools
- **PDF Generation:** Utilizes `FPDF` to automatically compile a branded "Study Guide" containing an Executive Summary, the user's timestamped notes, and extracted visual slide frames.
- **Audio Synthesis:** Uses Google Text-to-Speech (`gTTS`) to synthesize summaries or podcast scripts into MP3s dynamically.
