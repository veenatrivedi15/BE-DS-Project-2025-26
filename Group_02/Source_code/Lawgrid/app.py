from flask import Flask, render_template, request
import os
from pdf_highlighter import highlight_pdf

from utils import extract_text_from_pdf, split_into_clauses
from clause_detector import detect_clause_type
from risk_engine import generate_final_risk_report
from explanation_selector import refine_explanation
from flask import send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["contract"]
        path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(path)

        # 1️⃣ Extract text
        text = extract_text_from_pdf(path)

        # 2️⃣ Split into clauses
        clauses = split_into_clauses(text)

        analysis_results = []

        # 3️⃣ Analyze EACH clause
        for clause in clauses:
            clause_type = detect_clause_type(
                clause["heading"],
                clause["content"]
            )

            if clause_type == "general":
                continue

            # 4️⃣ Base risk report (KB-driven)
            report = generate_final_risk_report(clause_type)

            # 5️⃣ AI explanation (controlled LLM layer)
            explanation = refine_explanation(
                clause_text=clause["content"],
                clause_type=clause_type,
                severity=report["severity"],
                base_risks=report["key_risks"],
                base_recommendations=report["recommended_improvements"]
            )

            report["explanation"] = explanation

            analysis_results.append({
                "heading": clause["heading"],
                "content": clause["content"],  # 🔥 important
                "type": clause_type,
                "report": report
            })

        # Contract-level severity summary
        summary = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }
        highlight_data = []

        for item in analysis_results:
            highlight_data.append({
                "content": item["content"],
                "severity": item["report"]["severity"]
            })

        highlighted_filename = "highlighted_" + file.filename

        highlighted_pdf_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            highlighted_filename
        )


        highlight_pdf(
            input_pdf=path,
            clauses_with_severity=highlight_data,
            output_pdf=highlighted_pdf_path
        )


        for item in analysis_results:
            sev = item["report"]["severity"]
            summary[sev] += 1

        return render_template(
            "result.html",
            results=analysis_results,
            summary=summary,
            highlighted_pdf=highlighted_filename
        )




    return render_template("index.html")
@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )



if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)
