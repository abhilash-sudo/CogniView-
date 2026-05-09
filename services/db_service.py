import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
import chromadb
from sentence_transformers import SentenceTransformer
from config import DB_FILE, CHROMA_DB_PATH

# --- VECTOR DATABASE SETUP ---
print("[VectorBrain] Loading ChromaDB...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
vector_collection = chroma_client.get_or_create_collection(name="video_knowledge")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2') 

# --- SQLITE DATABASE ---
@contextmanager
def get_conn(row_factory=False):
    conn = sqlite3.connect(DB_FILE)
    if row_factory:
        conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
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
        c.execute('''CREATE TABLE IF NOT EXISTS cognitive_events
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id INTEGER,
                    timestamp REAL, event_type TEXT, signal TEXT, value REAL,
                    payload TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mastery_events
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id INTEGER,
                    concept TEXT, event_type TEXT, score_delta REAL,
                    confidence REAL, timestamp REAL, created_at TEXT)''')
        conn.commit()

def save_concepts(video_id, concepts):
    with get_conn() as conn:
        c = conn.cursor()
        for concept in concepts:
            try:
                c.execute("INSERT OR IGNORE INTO concepts (video_id, concept) VALUES (?, ?)", (video_id, concept))
            except: pass
        conn.commit()

def get_graph_data():
    with get_conn(row_factory=True) as conn:
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
        
        return {"nodes": nodes, "edges": edges}

def save_to_db(title, filename, transcript, slides, ocr_text):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO videos (title, filename, transcript, slides, ocr_text, date_added) VALUES (?, ?, ?, ?, ?, ?)",
                (title, filename, transcript, json.dumps(slides), ocr_text, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        vid = c.lastrowid
    return vid

def get_latest_video():
    with get_conn(row_factory=True) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM videos ORDER BY id DESC LIMIT 1")
        video = c.fetchone()
    return video

def get_video_by_id(video_id):
    with get_conn(row_factory=True) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        video = c.fetchone()
    return video

def get_notes_for_video(video_id):
    with get_conn(row_factory=True) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM notes WHERE video_id = ? ORDER BY timestamp ASC", (video_id,))
        return [dict(r) for r in c.fetchall()]

def get_concepts_for_video(video_id):
    with get_conn(row_factory=True) as conn:
        c = conn.cursor()
        c.execute("SELECT concept FROM concepts WHERE video_id = ? ORDER BY concept ASC", (video_id,))
        return [r["concept"] for r in c.fetchall()]

def get_video_profile(video_id):
    video = get_video_by_id(video_id)
    if not video:
        return None
    notes = get_notes_for_video(video_id)
    concepts = get_concepts_for_video(video_id)
    return {
        "video": dict(video),
        "notes": notes,
        "concepts": concepts,
    }

def save_cognitive_event(video_id, timestamp, event_type, signal="", value=None, payload=None):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO cognitive_events
                    (video_id, timestamp, event_type, signal, value, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (video_id, timestamp, event_type, signal, value,
                   json.dumps(payload or {}), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return c.lastrowid

def get_cognitive_events(video_id, limit=120):
    with get_conn(row_factory=True) as conn:
        c = conn.cursor()
        c.execute("""SELECT * FROM cognitive_events
                    WHERE video_id = ? ORDER BY id DESC LIMIT ?""", (video_id, limit))
        rows = [dict(r) for r in c.fetchall()]
    for row in rows:
        try:
            row["payload"] = json.loads(row.get("payload") or "{}")
        except Exception:
            row["payload"] = {}
    return list(reversed(rows))

def save_mastery_event(video_id, concept, event_type, score_delta=0, confidence=0.5, timestamp=0):
    concept = (concept or "General").strip()[:120] or "General"
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO mastery_events
                    (video_id, concept, event_type, score_delta, confidence, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (video_id, concept, event_type, score_delta, confidence, timestamp,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return c.lastrowid

def get_mastery_snapshot(video_id):
    concepts = get_concepts_for_video(video_id)
    mastery = {c: {"concept": c, "score": 48, "events": 0, "confidence": 0.35} for c in concepts}
    with get_conn(row_factory=True) as conn:
        c = conn.cursor()
        c.execute("""SELECT concept, event_type, score_delta, confidence
                    FROM mastery_events WHERE video_id = ?""", (video_id,))
        rows = c.fetchall()
    for row in rows:
        concept = row["concept"] or "General"
        item = mastery.setdefault(concept, {"concept": concept, "score": 48, "events": 0, "confidence": 0.35})
        item["score"] += float(row["score_delta"] or 0)
        item["events"] += 1
        item["confidence"] = max(item["confidence"], float(row["confidence"] or 0.35))
    for item in mastery.values():
        item["score"] = max(0, min(100, round(item["score"])))
        if item["score"] >= 76:
            item["state"] = "strong"
        elif item["score"] >= 55:
            item["state"] = "building"
        else:
            item["state"] = "weak"
        item["confidence"] = round(max(0, min(1, item["confidence"])), 2)
    ordered = sorted(mastery.values(), key=lambda x: (x["score"], -x["events"], x["concept"]))
    return {
        "items": ordered,
        "weak": [x for x in ordered if x["state"] == "weak"][:6],
        "strong": [x for x in reversed(ordered) if x["state"] == "strong"][:6],
        "average": round(sum(x["score"] for x in ordered) / len(ordered)) if ordered else 0,
    }

def vectorize_and_store(video_id, title, text):
    """Chunks text and stores semantic vectors."""
    print(f"[VectorBrain] Vectorizing video: {title}...")
    
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
    print(f"[VectorBrain] Stored {len(chunks)} knowledge chunks.")

def search_vectors(query, n_results=5):
    query_embedding = embedding_model.encode([query]).tolist()
    results = vector_collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    return results
