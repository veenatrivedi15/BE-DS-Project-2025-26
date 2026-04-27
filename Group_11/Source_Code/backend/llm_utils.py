import ollama
from chromadb_utils import retrieve_documents
def get_llm_summary(user_query: str):

    context = """A person is standing in a doorway of an indoor room. The room contains two beds, a chair with a backpack, and a small stool. The person is wearing a striped t-shirt and dark shorts.. Activity: standing in a doorway. Clothing: striped t-shirt, dark shorts.\n\nA single male is standing in an indoor room, seen from behind. He is wearing a striped t-shirt and dark shorts with sandals. The room contains a bed, a chair, and a small stool, with a window covered by curtains.. Activity: standing. Clothing: striped t-shirt, dark shorts, sandals.\n\nA single adult male is partially visible in a sparsely furnished indoor room with two beds and a window covered by curtains. He is wearing a striped t-shirt and dark shorts.. Activity: Standing. Clothing: Striped t-shirt (blue and white), dark shorts, flip-flops."""

    context = retrieve_documents(query=user_query)

    print(f"\n\n{context}\n\n")

    prompt = f"""
    You are analyzing multiple observations of the room.

    These observations may be repetitive or from slightly different viewpoints.

    ---------------------
    OBSERVATIONS:
    {context}
    ---------------------

    QUESTION:
    {user_query}

    INSTRUCTIONS:
    - Do NOT repeat the same description multiple times
    - Combine all observations into a single coherent understanding
    - Ignore repeated details unless they add new information
    - Be concise and factual
    - Only report the information explicitly present in the observations.
    - Do NOT make assumptions, inferences, or conclusions.
    - Be concise and factual.
    - Do NOT describe feelings, intentions, or possibilities.
    - Keep the output in 1-3 sentences maximum.
    - If unsure, say: "Not enough information"
    -If date is given, mention it.

    ANSWER:
    """

    response = ollama.chat(
        model="phi3:mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response['message']['content']

def main():
    llm_summary = get_llm_summary()
    print(f"\n{llm_summary}\n")


if __name__ == "__main__":
    # main()
    pass