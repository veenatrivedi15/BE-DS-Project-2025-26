"""
AgriAid+ Simplified Chatbot Engine
Uses Google Gemini API with direct PDF text extraction (no PyTorch/Transformers)
"""
import os
import json
import traceback
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBlksM9lytoDAUwpnQGfvM1eXr-3A01Jxk").strip()
KNOWLEDGE_BASE_DIR = 'Knowleadge_base/'

# Try importing Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"⚠️ Google Generative AI not available: {e}")

# Try importing PyPDF for text extraction
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except Exception:
    PYPDF_AVAILABLE = False

# Global knowledge base cache
_knowledge_base_text = None

def initialize_knowledge_base():
    """Load knowledge base once at startup"""
    global _knowledge_base_text
    if _knowledge_base_text is None:
        print("🔄 Loading knowledge base for the first time...")
        _knowledge_base_text = extract_pdf_texts()
        print(f"✅ Knowledge base loaded: {len(_knowledge_base_text)} characters")
    return _knowledge_base_text

def get_knowledge_base_text():
    """Get cached knowledge base text"""
    global _knowledge_base_text
    if _knowledge_base_text is None:
        return initialize_knowledge_base()
    return _knowledge_base_text

def extract_pdf_texts():
    """Extract text from all PDFs in knowledge base (without embeddings)"""
    if not PYPDF_AVAILABLE:
        print("⚠️ pypdf not available. Cannot extract PDF texts.")
        return []
    
    print("📚 Extracting text from knowledge base PDFs...")
    
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"⚠️ Knowledge base folder '{KNOWLEDGE_BASE_DIR}' not found.")
        return []
    
    all_texts = []
    pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("⚠️ No PDF files found in knowledge base folder.")
        return []
    
    print(f"  Found {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        try:
            pdf_path = os.path.join(KNOWLEDGE_BASE_DIR, pdf_file)
            reader = PdfReader(pdf_path)
            text_content = f"\n--- SOURCE: {pdf_file} ---\n"
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_content += f"\n[Page {page_num + 1}]\n{text}\n"
            
            all_texts.append(text_content)
            print(f"  ✓ Extracted from {pdf_file} ({len(reader.pages)} pages)")
        
        except Exception as e:
            print(f"  ✗ Error extracting {pdf_file}: {e}")
    
    combined_text = "\n".join(all_texts)
    print(f"✅ Total text extracted: {len(combined_text)} characters")
    return combined_text



def search_knowledge_base(query, knowledge_text="", max_chars=3000):
    """
    Search knowledge base for relevant information without using embeddings
    Returns only relevant excerpts to reduce token usage
    """
    if not knowledge_text:
        return "(No knowledge base available)"
    
    # Split into paragraphs and search for relevant ones
    paragraphs = knowledge_text.split('\n')
    query_words = set(query.lower().split())
    
    relevant = []
    for para in paragraphs:
        if len(para) > 10:  # Skip short lines
            # Score paragraph based on keyword matches
            score = sum(1 for word in query_words if word in para.lower())
            if score > 0:
                relevant.append((score, para[:500]))  # Keep first 500 chars
    
    # Sort by relevance and take top results
    relevant.sort(reverse=True)
    result = "\n".join([p[1] for p in relevant[:5]])  # Top 5 paragraphs
    
    # Limit total size to reduce tokens
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    
    return result if result.strip() else "(No relevant information found in knowledge base)"


def get_rag_response(user_message, knowledge_text=""):
    """
    Generate RAG response using Gemini API with PDF knowledge base
    Optimized for token usage
    """
    if not GEMINI_AVAILABLE:
        return "Google Generative AI not available. Please install google-generativeai package."
    
    try:
        # Extract knowledge base if not provided
        if not knowledge_text:
            knowledge_text = extract_pdf_texts()
        
        # Search for relevant content (reduce token usage)
        relevant_context = search_knowledge_base(user_message, knowledge_text, max_chars=2000)
        
        # Prepare prompt with improved formatting instructions
        prompt = f"""You are an expert agricultural assistant for the AgriAid+ platform.

EXPERTISE: Crop cultivation, soil health, weather, pest & disease management, government schemes, market trends

RESPONSE FORMAT:

For Disease/Pest Questions:
### 📋 SYMPTOMS:
[Clear visible signs]

### 🌍 CONDITIONS FAVORING DISEASE:
[When/why/where - weather, humidity, temperature conditions]

### 🛡️ PREVENTION & CONTROL:
- [Prevention method]
- [Control measure]

### 💊 TREATMENT OPTIONS:
- [Treatment with dosage if known]

### ✅ MONITORING:
[How to scout and track]

---

For Government Schemes:
### 💰 BENEFITS:
[What farmers get - use **bold** for amounts like **₹6,000**]

### 📋 ELIGIBILITY:
[Who qualifies]

### � APPLY:
- Step 1: [...]
- Step 2: [...]

### ⏰ TIMELINE:
[Important dates]

---

FORMATTING RULES:
- Use ### for main headings ONLY
- Use bullet points with dashes
- Bold important numbers: **₹6,000**, **3-5 days**
- Keep answers practical and clear
- Add SUMMARY section
- Reply in user's language
- Be encouraging to farmers

KNOWLEDGE BASE EXCERPT:
{relevant_context}

QUESTION: {user_message}

RESPOND:"""

        # Call Gemini API with simplified prompt
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1500
            )
        )
        
        return response.text if response.text else "Unable to generate response. Please try again."
    
    except Exception as e:
        error_str = str(e)
        print(f"❌ Error: {error_str}")
        
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            return "⚠️ API quota limit reached. Please try again in 12+ hours."
        elif "API key" in error_str:
            return "⚠️ API key configuration error."
        else:
            return "Error: Unable to process request."


# For backwards compatibility, keep the original function names
def create_vector_db():
    """Compatibility function - extracts PDFs without vector DB"""
    print("📚 Preparing knowledge base...")
    text = extract_pdf_texts()
    return bool(text)



# Only build vector DB when run directly
if __name__ == '__main__':
    create_vector_db()