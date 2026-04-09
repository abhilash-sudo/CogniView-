import sqlite3
import json
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer
from config import DB_FILE, CHROMA_DB_PATH

# --- VECTOR DATABASE SETUP ---
print("🧠 Loading Vector Brain (ChromaDB)...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
vector_collection = chroma_client.get_or_create_collection(name="video_knowledge")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2') 

# --- SQLITE DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, filename TEXT, 
                  transcript TEXT, slides TEXT, ocr_text TEXT, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id INTEGER, 
                  timestamp INTEGER, text TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS concepts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id INTEGER, 
                  concept TEXT, UNIQUE(video_id, concept))''')
    conn.commit()
    conn.close()

def save_concepts(video_id, concepts):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for concept in concepts:
        try:
            c.execute("INSERT OR IGNORE INTO concepts (video_id, concept) VALUES (?, ?)", (video_id, concept))
        except: pass
    conn.commit()
    conn.close()

def get_graph_data():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Nodes: Videos (Type 1) and Concepts (Type 2)
    c.execute("SELECT id, title FROM videos")
    videos = c.fetchall()
    
    c.execute("SELECT DISTINCT concept FROM concepts")
    concepts = c.fetchall()
    
    nodes = []
    edges = []
    
    # Video Nodes
    for v in videos:
        nodes.append({"id": f"v_{v['id']}", "label": v['title'], "group": "video", "value": 20})
        
    # Concept Nodes
    for con in concepts:
        c_id = f"c_{con['concept']}"
        nodes.append({"id": c_id, "label": con['concept'], "group": "concept", "value": 10})
        
    # Edges (Connections)
    c.execute("SELECT video_id, concept FROM concepts")
    links = c.fetchall()
    for l in links:
        edges.append({"from": f"v_{l['video_id']}", "to": f"c_{l['concept']}"})
        
    conn.close()
    return {"nodes": nodes, "edges": edges}

def save_to_db(title, filename, transcript, slides, ocr_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO videos (title, filename, transcript, slides, ocr_text, date_added) VALUES (?, ?, ?, ?, ?, ?)",
              (title, filename, transcript, json.dumps(slides), ocr_text, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    vid = c.lastrowid
    conn.close()
    return vid

def get_latest_video():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM videos ORDER BY id DESC LIMIT 1")
    video = c.fetchone()
    conn.close()
    return video

def get_video_by_id(video_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    video = c.fetchone()
    conn.close()
    return video

def vectorize_and_store(video_id, title, text):
    """Chunks text and stores semantic vectors."""
    print(f"🧠 Vectorizing video: {title}...")
    
    # Split text into chunks (e.g., 1000 characters)
    chunk_size = 1000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    ids = [f"{video_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"video_id": video_id, "title": title, "chunk_index": i} for i in range(len(chunks))]
    
    # Generate Embeddings
    embeddings = embedding_model.encode(chunks).tolist()
    
    # Store in ChromaDB
    vector_collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )
    print(f"✅ Stored {len(chunks)} knowledge chunks in Vector Brain.")

def search_vectors(query, n_results=5):
    query_embedding = embedding_model.encode([query]).tolist()
    results = vector_collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    return results
