import json
import time
import chromadb
from chromadb.utils import embedding_functions

# --- STEP 0: CONFIGURE CHROMADB ---
DB_PATH = "./summary_db"
client = chromadb.PersistentClient(path=DB_PATH)

# Embedding function: sentence transformer
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client.get_or_create_collection(name="vlm_documents", embedding_function=emb_fn)

# --- STEP 1: FUNCTION TO INGEST VLM JSON ---
def ingest_vlm_json(vlm_responses, collection = collection):
    """
    vlm_responses: list of dicts (VLM JSON outputs)
    collection: Chroma collection object
    """
    for i, raw in enumerate(vlm_responses):
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw

            # Build document text for embedding
            doc_text = f"{data.get('summary', '')}."
            if data.get('activity'):
                doc_text += f" Activity: {data['activity']}."
            if data.get('clothing'):
                doc_text += f" Clothing: {', '.join(data['clothing'])}."
            if data.get('carrying_items'):
                doc_text += f" Items: {', '.join(data['carrying_items'])}."
            doc_text += f" Time: {time.strftime('%Y-%m-%d %H:%M:%S')}."
            

            # Metadata for filtering or reference
            metadata = {
                "people_count": data.get("people_count"),
                "location": data.get("location"),
                "activity": data.get("activity"),
                "timestamp": time.time()
            }

            # Unique ID
            doc_id = f"vlm_{i}_{int(time.time()*1000)}"

            # Add to ChromaDB
            collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print(f"✅ Stored: {doc_id}")

        except Exception as e:
            print(f"❌ Error storing frame {i}: {e}")

# --- STEP 2: FUNCTION TO QUERY AND RETURN FULL DOCUMENTS ---
def retrieve_documents(query, collection = collection, top_k=3):
    """
    query: user query string
    collection: Chroma collection object
    top_k: number of relevant documents to retrieve
    Returns: concatenated text of top documents
    """
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    # Chroma returns dict of lists
    docs = results['documents'][0]  # top_k docs
    return "\n\n".join(docs)

# --- STEP 3: EXAMPLE USAGE ---
def main():
    print("--- VLM → Chroma → LLM PIPELINE ---\n")

    # Example: ingest JSON responses from Gemini/VLM
    # Replace this with your actual VLM JSON list
    vlm_responses = [
        # Add more JSON frames here
        {
            "people_count": 1,
            "people_description": [
                "An adult person with short dark hair and light skin"
            ],
            "vehicle_count": 0,
            "vehicle_type": "null",
            "vehicle_color": "null",
            "clothing": [
                "striped t-shirt",
                "dark shorts"
            ],
            "carrying_items": [],
            "activity": "standing in a doorway",
            "interaction": "null",
            "location": "indoor room",
            "time_of_day": "null",
            "anomaly": "null",
            "summary": "A person is standing in a doorway of an indoor room. The room contains two beds, a chair with a backpack, and a small stool. The person is wearing a striped t-shirt and dark shorts."
        },
        {
            "people_count": 1,
            "people_description": [
                "A male individual, with dark hair, is standing on a small red stool with a green top. He is looking down at an item in his hands."
            ],
            "vehicle_count": 0,
            "vehicle_type": "null",
            "vehicle_color": "null",
            "clothing": [
                "striped t-shirt",
                "dark shorts"
            ],
            "carrying_items": [
                "a light-colored item (possibly a book or container)"
            ],
            "activity": "standing on a stool and examining an item",
            "interaction": "null",
            "location": "indoors, likely a room or hallway with a bed and curtains",
            "time_of_day": "null",
            "anomaly": "null",
            "summary": "A male individual is standing on a stool in an indoor setting, wearing a striped t-shirt and dark shorts, while focusing on an item he is holding."
        },
        {
            "people_count": 1,
            "people_description": [
                "A man, standing on a red stool."
            ],
            "vehicle_count": 0,
            "vehicle_type": "null",
            "vehicle_color": "null",
            "clothing": [
                "striped t-shirt",
                "dark shorts"
            ],
            "carrying_items": [
                "an open book or notebook"
            ],
            "activity": "standing on a stool and reading a book/notebook",
            "interaction": "null",
            "location": "indoors, likely a room",
            "time_of_day": "null",
            "anomaly": "null",
            "summary": "A man is standing on a red stool, holding and looking at an open book or notebook in a room."
        },
        {
            "people_count": 1,
            "people_description": [
                "adult male, standing, facing right"
            ],
            "vehicle_count": 0,
            "vehicle_type": "null",
            "vehicle_color": "null",
            "clothing": [
                "striped short-sleeved t-shirt",
                "dark shorts",
                "sandals"
            ],
            "carrying_items": [],
            "activity": "standing",
            "interaction": "null",
            "location": "indoor room",
            "time_of_day": "daytime",
            "anomaly": "null",
            "summary": "An adult male is standing in an indoor room, wearing a striped t-shirt, dark shorts, and sandals. The room contains beds, a chair, and a small stool."
        },
        {
            "people_count": 1,
            "people_description": [
                "man, seen from behind"
            ],
            "vehicle_count": 0,
            "vehicle_type": "null",
            "vehicle_color": "null",
            "clothing": [
                "striped t-shirt",
                "dark shorts"
            ],
            "carrying_items": [],
            "activity": "walking or standing",
            "interaction": "null",
            "location": "indoor room/doorway",
            "time_of_day": "null",
            "anomaly": "null",
            "summary": "A man is observed from behind, standing or walking in a doorway within an indoor room. He is wearing a striped t-shirt and dark shorts. The room contains two single beds, a small stool, a chair with a bag, and curtains over a window."
        },
        {
        "people_count": 1,
        "people_description": [
            "One adult male, partially visible behind a wall/doorframe"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "Striped t-shirt (blue and white)",
            "dark shorts",
            "flip-flops"
        ],
        "carrying_items": [],
        "activity": "Standing",
        "interaction": "null",
        "location": "Indoor room, possibly a dormitory or bedroom",
        "time_of_day": "null",
        "anomaly": "null",
        "summary": "A single adult male is partially visible in a sparsely furnished indoor room with two beds and a window covered by curtains. He is wearing a striped t-shirt and dark shorts."
        },
        {
        "people_count": 1,
        "people_description": [
            "male"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "striped t-shirt",
            "dark shorts",
            "flip-flops"
        ],
        "carrying_items": [
            "white object",
            "blue object"
        ],
        "activity": "standing and examining items",
        "interaction": "null",
        "location": "indoor room",
        "time_of_day": "null",
        "anomaly": "null",
        "summary": "A male individual is standing in an indoor room, wearing a striped t-shirt and dark shorts, looking at items he is holding in his hands."
        },
        {
        "people_count": 1,
        "people_description": [
            "male, dark hair, standing, looking down"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "striped t-shirt",
            "dark shorts",
            "flip-flops"
        ],
        "carrying_items": [
            "papers"
        ],
        "activity": "reading or reviewing papers",
        "interaction": "null",
        "location": "indoor room",
        "time_of_day": "null",
        "anomaly": "null",
        "summary": "A male is standing in an indoor room, holding and looking at papers. He is wearing a striped t-shirt, dark shorts, and flip-flops."
        },
        {
        "people_count": 1,
        "people_description": [
            "young adult male with dark hair and glasses"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "striped t-shirt",
            "dark shorts",
            "flip-flops"
        ],
        "carrying_items": [
            "white sheet of paper"
        ],
        "activity": "reading",
        "interaction": "null",
        "location": "indoor room",
        "time_of_day": "daytime",
        "anomaly": "null",
        "summary": "A young adult male is standing in a room, reading a white sheet of paper. He is wearing a striped t-shirt, dark shorts, and flip-flops. The room contains two single beds and a window with curtains."
        },
        {
        "people_count": 1,
        "people_description": [
            "Adult male, seen from the back, bending over a surface"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "Striped t-shirt",
            "dark shorts",
            "sandals"
        ],
        "carrying_items": [
            "blue object (possibly a book or container)"
        ],
        "activity": "Bending over, possibly arranging or inspecting items on a bed/table",
        "interaction": "null",
        "location": "Indoor room, likely a bedroom or living space",
        "time_of_day": "daytime",
        "anomaly": "null",
        "summary": "A single adult male is observed bending over a surface, possibly a bed or table, in an indoor room. He is wearing a striped t-shirt, dark shorts, and sandals, and appears to be handling a blue object. The room contains a bed, a chair, and a window with curtains."
        },
        {
        "people_count": 1,
        "people_description": [
            "One person is partially visible, walking through a doorway"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "striped t-shirt",
            "dark shorts",
            "slippers"
        ],
        "carrying_items": [],
        "activity": "walking",
        "interaction": "null",
        "location": "indoor room/bedroom",
        "time_of_day": "null",
        "anomaly": "null",
        "summary": "A person is partially visible walking through a doorway in an indoor room that appears to be sparsely furnished with two beds, a chair, and a window with curtains. The person is wearing a striped t-shirt and dark shorts."
        },
        {
        "people_count": 1,
        "people_description": [
            "male, seen from behind, dark hair"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "striped t-shirt",
            "dark shorts",
            "sandals"
        ],
        "carrying_items": [],
        "activity": "standing",
        "interaction": "null",
        "location": "indoor room, possibly a bedroom or living area",
        "time_of_day": "daytime",
        "anomaly": "null",
        "summary": "A single male is standing in an indoor room, seen from behind. He is wearing a striped t-shirt and dark shorts with sandals. The room contains a bed, a chair, and a small stool, with a window covered by curtains."
        },
        {
        "people_count": 1,
        "people_description": [
            "An adult male viewed from the back"
        ],
        "vehicle_count": 0,
        "vehicle_type": "null",
        "vehicle_color": "null",
        "clothing": [
            "striped t-shirt",
            "dark shorts"
        ],
        "carrying_items": [],
        "activity": "walking",
        "interaction": "null",
        "location": "indoor room",
        "time_of_day": "daytime",
        "anomaly": "null",
        "summary": "A single adult male is observed walking indoors, wearing a striped t-shirt and dark shorts, in a room furnished with beds and a window."
        }
    ]

    print("→ Ingesting VLM JSON into ChromaDB...")
    ingest_vlm_json(vlm_responses, collection)

    print("\n--- READY TO RECEIVE QUERIES ---")
    while True:
        user_query = input("\nEnter your query (or 'exit' to quit): ")
        if user_query.lower() == "exit":
            print("Exiting...")
            break

        retrieved_text = retrieve_documents(user_query, collection)

        print("\n--- RETRIEVED DOCUMENTS ---")
        print(retrieved_text)
        print("\nYou can now feed this text to an LLM (e.g., Mistral) to generate a response.\n")


if __name__ == "__main__":
    # main()
    pass