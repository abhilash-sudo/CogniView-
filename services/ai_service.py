from groq import Groq
from config import GROQ_API_KEY
import json, re, hashlib, time

client = Groq(api_key=GROQ_API_KEY)

FAST_MODEL  = "llama-3.1-8b-instant"     # ~500 tok/s — flashcards, quiz, summary, chapters
POWER_MODEL = "llama-3.3-70b-versatile"  # deep reasoning — mindmap, chat Q&A

TASK_MODEL = {
    "chat": POWER_MODEL,
    "mindmap": POWER_MODEL,
    "summary": FAST_MODEL,
    "flashcards": FAST_MODEL,
    "quiz": FAST_MODEL,
    "podcast": FAST_MODEL,
    "concepts": FAST_MODEL,
}

_CACHE = {}
_CACHE_TTL_SECONDS = 900

def _cache_key(task, text):
    digest = hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()
    return f"{task}:{digest}"

def _cache_get(task, text):
    key = _cache_key(task, text)
    item = _CACHE.get(key)
    if not item:
        return None
    if (time.time() - item["ts"]) > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return item["value"]

def _cache_set(task, text, value):
    _CACHE[_cache_key(task, text)] = {"ts": time.time(), "value": value}

def _model_for(task):
    return TASK_MODEL.get(task, POWER_MODEL)

def ask_ai(system_prompt, user_prompt, model=None):
    """Primary AI call — defaults to POWER model."""
    use_model = model or POWER_MODEL
    try:
        r = client.chat.completions.create(
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            model=use_model, temperature=0.3
        )
        return r.choices[0].message.content
    except Exception as e:
        print(f"[AI] {use_model} failed ({e}). Falling back to fast model...")
        try:
            r = client.chat.completions.create(
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
                model=FAST_MODEL, temperature=0.3
            )
            return r.choices[0].message.content
        except Exception as e2:
            return f"Error: AI overloaded. ({e2})"

def ask_ai_for_task(task, system_prompt, user_prompt):
    return ask_ai(system_prompt, user_prompt, model=_model_for(task))

def ask_ai_fast(system_prompt, user_prompt):
    """Cognitive tasks — uses the 8b instant model for maximum speed."""
    return ask_ai(system_prompt, user_prompt, model=FAST_MODEL)


def extract_concepts(text):
    sys = "TASK: Extract top 5 key concepts (single words or short phrases) from the text. Return comma-separated."
    try:
        res = ask_ai_for_task("concepts", sys, text[:15000])
        concepts = [c.strip().title() for c in res.split(',') if c.strip()]
        return concepts[:8]
    except: return []

def extract_mindmap_json(text):
    """
    Returns a structured JSON object for vis.js mind map rendering.
    Format: { "title": "...", "branches": [ { "name": "...", "items": ["...", "..."] } ] }
    """
    # Aggressively clean the context to be useful
    # Remove timestamps like [00:01] at start of lines
    import re as _re
    clean_text = _re.sub(r'\[\d+:\d+\]\s*', '', text)
    # Remove blank lines and strip
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
    clean_text = ' '.join(lines)[:18000]
    
    sys = """You are a knowledge extraction engine. Your ONLY job is to output valid JSON.
ANALYZE the text and produce a hierarchical mind map.

OUTPUT RULES — CRITICAL:
- Output ONE JSON object. Nothing else. No explanation. No markdown. No code fences.
- "title": short central topic (3-5 words) derived from the TEXT
- "branches": 5-7 main categories found in the TEXT, each with 3-5 "items" (specific sub-points)
- Items must contain REAL SPECIFIC INFORMATION from the text (names, dates, concepts, definitions)
- Labels must be SHORT: 3-6 words max per item

EXAMPLE (for a video about Photosynthesis):
{"title":"Photosynthesis Process","branches":[{"name":"Light Reactions","items":["Chlorophyll absorbs sunlight","ATP synthesis","Water molecules split","Oxygen released"]},{"name":"Calvin Cycle","items":["CO2 fixation","Glucose production","NADPH consumed"]},{"name":"Chloroplast Structure","items":["Thylakoid membrane","Stroma region","Grana stacks"]},{"name":"Factors Affecting Rate","items":["Light intensity","CO2 concentration","Temperature effects"]},{"name":"Products & Uses","items":["Glucose for energy","Oxygen byproduct","Biomass creation"]}]}

Now analyze the following text and produce JSON in exactly this format:"""

    def try_parse(raw):
        raw = _re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start == -1 or end == 0:
            return None
        try:
            data = json.loads(raw[start:end])
            # Validate structure
            if 'title' in data and 'branches' in data and len(data['branches']) > 0:
                return data
        except:
            pass
        return None

    cached = _cache_get("mindmap", clean_text)
    if cached is not None:
        return cached
    try:
        raw = ask_ai_for_task("mindmap", sys, clean_text)
        result = try_parse(raw)
        if result:
            print(f"[MindMap] Parsed successfully: {result['title']} ({len(result['branches'])} branches)")
            _cache_set("mindmap", clean_text, result)
            return result
        
        # Retry with simpler/faster model and even more explicit prompt
        print("[MindMap] First parse failed, retrying with strict prompt...")
        retry_sys = 'Output ONLY valid JSON. No text before or after. Format: {"title":"TOPIC","branches":[{"name":"BRANCH","items":["item1","item2","item3"]}]}'
        retry_prompt = f"Create a mind map JSON for this content (extract real key points): {clean_text[:8000]}"
        raw2 = ask_ai_for_task("mindmap", retry_sys, retry_prompt)
        result2 = try_parse(raw2)
        if result2:
            print(f"[MindMap] Retry succeeded: {result2['title']}")
            _cache_set("mindmap", clean_text, result2)
            return result2
        
        print(f"[MindMap] Both attempts failed. Raw output: {raw[:300]}")
        # Generate a basic one from the text directly without AI
        first_line = lines[0][:50] if lines else "Lecture Notes"
        fallback = {"title": first_line, "branches": [{"name": "Key Content", "items": [l[:40] for l in lines[1:6]]}]}
        _cache_set("mindmap", clean_text, fallback)
        return fallback
    except Exception as e:
        print(f"[MindMap] Exception: {e}")
        fallback = {"title": "Processing Error", "branches": [{"name": "Error", "items": [str(e)[:50]]}]}
        _cache_set("mindmap", clean_text, fallback)
        return fallback


def generate_podcast_script(text):
    sys = """TASK: Convert the text into a lively 2-person podcast script between Alex (Host) and Sam (Expert).
    - Format: STRICT JSON ARRAY: [{"speaker":"Alex", "text":"..."}, {"speaker":"Sam", "text":"..."}]
    - Style: Conversational, witty, use analogies. Alex asks dumb questions, Sam explains.
    - Length: 6-10 exchanges."""
    try:
        res = ask_ai_for_task("podcast", sys, text[:25000])
        return clean_json(res)
    except: return "[]"
    
def clean_json(text):
    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        return text[start:end]
    except: return "[]"

def simplify_context(text):
    sys = """TASK: The user is confused by the video they are currently watching. 
    Explain the following segment of the transcript extremely simply, as if to a smart 10-year-old.
    Use an analogy if helpful. Keep it under 3 concise sentences. Tone: Encouraging and clear."""
    try:
        res = ask_ai_for_task("chat", sys, text[:5000])
        return res
    except: return "I'm sorry, I encountered an error trying to process that segment."

def generate_flashcards(text):
    """Returns a JSON array of {front, back} flashcard objects from the transcript."""
    sys = """You are a flashcard generator. Create exactly 10 study flashcards from the content.
OUTPUT RULES:
- Output ONLY a valid JSON object with a "cards" array. No markdown, no explanation.
- Format: {"cards": [{"front": "question (max 12 words)", "back": "answer (max 30 words)"}]}
- Questions must test real, specific knowledge from the text.
- Vary difficulty.
Now generate 10 flashcards from this content:"""
    cached = _cache_get("flashcards", text)
    if cached is not None:
        if isinstance(cached, list) and len(cached) > 0 and cached[0].get("front") != "Error generating flashcards":
            return cached
    try:
        raw = ask_ai_for_task("flashcards", sys, text)
        import re as _re, json as _json
        raw = _re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object")
        data = _json.loads(raw[start:end])
        cards = data.get("cards", [])
        valid = [c for c in cards if 'front' in c and 'back' in c]
        if not valid: raise ValueError("No valid cards generated")
        print(f"[Flashcards] Generated {len(valid)} cards")
        _cache_set("flashcards", text, valid)
        return valid
    except Exception as e:
        print(f"[Flashcards] Failed: {e}")
        fallback = [{"front": "Error generating flashcards", "back": str(e)[:80]}]
        _cache_set("flashcards", text, fallback)
        return fallback

def generate_summary(text):
    """Returns a structured summary: tldr, sections, bullets, key_terms, difficulty."""
    sys = """You are a smart study assistant. Analyze the text and output a structured study summary as STRICT JSON.
OUTPUT ONLY the JSON object. No markdown, no explanation.
FORMAT:
{
  "tldr": "One sentence (max 25 words) capturing the core point of the entire content",
  "sections": [
    {"header": "Section Title", "content": "Detailed paragraph explaining this section's core concepts"}
  ],
  "bullets": ["Key point 1 (max 15 words)", "Key point 2", "Key point 3"],
  "key_terms": [{"term": "Term Name", "definition": "Short definition (max 15 words)"}],
  "difficulty": "Beginner|Intermediate|Advanced"
}
- sections: Break the content into 3-5 logical sections. Provide a rich paragraph for each.
- bullets: exactly 4-6 specific, actionable key points from the text
- key_terms: exactly 4-6 important technical terms defined
Now generate the summary for:"""
    cached = _cache_get("summary", text)
    if cached is not None:
        if isinstance(cached, dict) and cached.get("tldr") != "Could not generate summary." and "sections" in cached:
            return cached
    try:
        raw = ask_ai_for_task("summary", sys, text)
        import re as _re, json as _json
        raw = _re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object")
        data = _json.loads(raw[start:end])
        print(f"[Summary] Generated summary: {data.get('difficulty','?')} difficulty")
        _cache_set("summary", text, data)
        return data
    except Exception as e:
        print(f"[Summary] Failed: {e}")
        fallback = {"tldr": "Could not generate summary.", "sections": [], "bullets": [], "key_terms": [], "difficulty": "Unknown"}
        _cache_set("summary", text, fallback)
        return fallback

def generate_quiz_v2(text):
    sys_prompt = (
        "You are a quiz master. Generate exactly 5 MCQs. "
        "OUTPUT ONLY a valid JSON object with a 'questions' array. "
        'Format: {"questions": [{"q":"Question?","options":["A. o1","B. o2","C. o3","D. o4"],"correct":0,"explanation":"reason","difficulty":"Easy|Medium|Hard"}]} '
        "correct is 0-indexed. Mix Easy/Medium/Hard. Generate from content:"
    )
    cached = _cache_get("quiz", text)
    if cached is not None:
        if isinstance(cached, list) and len(cached) > 0 and "generation failed" not in cached[0].get("q", ""):
            return cached
    try:
        import re as _re, json as _json
        raw = ask_ai_for_task("quiz", sys_prompt, text[:20000])
        raw = _re.sub(r"```(?:json)?", "", raw).strip().strip("`")
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s == -1 or e == 0:
            raise ValueError("No JSON object")
        data = _json.loads(raw[s:e])
        qs = data.get("questions", [])
        valid = [q for q in qs if "q" in q and "options" in q and "correct" in q]
        if not valid: raise ValueError("No valid questions generated")
        print(f"[Quiz] Generated {len(valid)} questions")
        _cache_set("quiz", text, valid)
        return valid
    except Exception as ex:
        print(f"[Quiz] Failed: {ex}")
        fallback = [{"q": "Quiz generation failed.", "options": ["A. Retry"], "correct": 0, "explanation": str(ex)[:60], "difficulty": "Unknown"}]
        _cache_set("quiz", text, fallback)
        return fallback

def generate_debate(context, query):
    sys_prompt = """You are a panel of 3 distinct AI Personas:
1. "Tutor" (Encouraging, Socratic, asks guiding questions)
2. "ELI5" (Uses extremely simple analogies)
3. "Critic" (Devil's advocate, challenges assumptions)

The user has asked a question. Generate a short, multi-agent debate/discussion answering the user.
OUTPUT ONLY a valid JSON array.
FORMAT: [{"persona": "Tutor", "text": "..."}, {"persona": "ELI5", "text": "..."}]
Include 2 to 4 exchanges in the array."""
    try:
        import re as _re, json as _json
        user_prompt = f"Context: {context[:5000]}\n\nUser Question: {query}"
        raw = ask_ai_for_task("chat", sys_prompt, user_prompt)
        raw = _re.sub(r"```(?:json)?", "", raw).strip().strip("`")
        s, e = raw.find("["), raw.rfind("]") + 1
        if s == -1 or e == 0:
            raise ValueError("No JSON array")
        data = _json.loads(raw[s:e])
        return data
    except Exception as ex:
        print(f"[Debate] Failed: {ex}")
        return [{"persona": "System", "text": "Sorry, the multi-agent panel is offline."}]
