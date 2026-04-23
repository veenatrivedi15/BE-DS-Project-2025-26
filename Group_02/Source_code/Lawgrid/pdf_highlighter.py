import fitz  # PyMuPDF

SEVERITY_COLORS = {
    "HIGH": (1, 0, 0),      # Red
    "MEDIUM": (1, 0.65, 0), # Orange
    "LOW": (0, 0.8, 0)      # Green
}

def highlight_pdf(input_pdf, clauses_with_severity, output_pdf):
    doc = fitz.open(input_pdf)

    for page in doc:
        page_text = page.get_text().lower()

        for clause in clauses_with_severity:
            text = clause["content"].lower()
            severity = clause["severity"]

            if text[:40] in page_text:
                areas = page.search_for(text[:40])

                for rect in areas:
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=SEVERITY_COLORS[severity])
                    highlight.update()

    doc.save(output_pdf)
