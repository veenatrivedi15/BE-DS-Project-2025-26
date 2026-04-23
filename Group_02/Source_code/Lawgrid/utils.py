import pdfplumber
import re

def extract_text_from_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def split_into_clauses(text):
    pattern = r"\n\d+\.\s+[A-Z][A-Z\s]+\."
    sections = re.split(pattern, text)
    headings = re.findall(pattern, text)

    clauses = []
    for i in range(len(headings)):
        clauses.append({
            "heading": headings[i].strip(),
            "content": sections[i + 1].strip()
        })

    return clauses
