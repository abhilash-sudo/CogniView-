from groq import Groq
from config import GROQ_API_KEY

# Initialize Client
client = Groq(api_key=GROQ_API_KEY)

def ask_ai(system_prompt, user_prompt):
    try:
        completion = client.chat.completions.create(
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            model="llama-3.3-70b-versatile", temperature=0.3
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Primary Brain Failed ({e}). Switching to Backup Brain...")
        try:
            completion = client.chat.completions.create(
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
                model="llama-3.1-8b-instant", temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e2:
            return f"Error: All systems overloaded. ({e2})"

def extract_concepts(text):
    sys = "TASK: Extract top 5 key concepts (single words or short phrases) from the text. Return comma-separated."
    try:
        res = ask_ai(sys, text[:15000]) # Limit context
        # Clean up response
        concepts = [c.strip().title() for c in res.split(',') if c.strip()]
        return concepts[:8] # Limit to top 8
    except: return []

def generate_podcast_script(text):
    sys = """TASK: Convert the text into a lively 2-person podcast script between Alex (Host) and Sam (Expert).
    - Format: STRICT JSON ARRAY: [{"speaker":"Alex", "text":"..."}, {"speaker":"Sam", "text":"..."}]
    - Style: Conversational, witty, use analogies. Alex asks dumb questions, Sam explains.
    - Length: 6-10 exchanges."""
    
    try:
        res = ask_ai(sys, text[:25000])
        return clean_json(res) # reusing a helper if needed, or just return res
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
        res = ask_ai(sys, text[:5000])
        return res
    except: return "I'm sorry, I encountered an error trying to process that segment."
