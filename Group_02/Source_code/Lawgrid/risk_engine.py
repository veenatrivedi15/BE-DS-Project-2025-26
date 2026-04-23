LEGAL_RISK_KB = {

    "payment": {
        "risk": [
            "Unclear payment timelines may cause cash flow issues",
            "No penalty for delayed payments",
            "Ambiguous expense reimbursement terms"
        ],
        "solution": [
            "Specify clear payment deadlines",
            "Add late payment penalties",
            "Clearly define reimbursable expenses"
        ]
    },

    "termination": {
        "risk": [
            "One-sided termination rights may unfairly disadvantage one party",
            "Lack of notice period can cause operational disruption",
            "No compensation for early termination losses"
        ],
        "solution": [
            "Introduce mutual termination rights",
            "Add a reasonable notice period",
            "Provide compensation for early termination"
        ]
    },

    "insurance": {
        "risk": [
            "High insurance thresholds may be costly for smaller parties",
            "Failure to maintain coverage may trigger contract breach",
            "Coverage scope may not match actual risks"
        ],
        "solution": [
            "Align insurance limits with industry standards",
            "Clearly define required coverage types",
            "Allow alternative risk mitigation measures"
        ]
    },

    "audit": {
        "risk": [
            "Broad audit rights may disrupt normal operations",
            "Unlimited audit frequency increases compliance burden",
            "Confidential information may be exposed during audits"
        ],
        "solution": [
            "Limit audit frequency",
            "Require reasonable advance notice",
            "Protect confidential information during audits"
        ]
    },

    "ip": {
        "risk": [
            "Loss of ownership over created work",
            "Restrictions on reuse of background intellectual property",
            "Unclear ownership of derivative works"
        ],
        "solution": [
            "Retain background IP rights",
            "Clearly define ownership of new work",
            "Allow limited reuse of work product"
        ]
    },

    "jurisdiction": {
        "risk": [
            "May disadvantage the non-local party",
            "Increases litigation cost",
            "Limits flexibility in dispute resolution"
        ],
        "solution": [
            "Allow mutual agreement on governing law",
            "Add arbitration or mediation mechanisms",
            "Define a neutral jurisdiction"
        ]
    },

    "employment": {
        "risk": [
            "Non-compliance with employment and anti-discrimination laws",
            "Exposure to regulatory penalties",
            "Reputational risk from unlawful employment practices"
        ],
        "solution": [
            "Ensure policies comply with applicable employment laws",
            "Conduct periodic compliance reviews",
            "Provide training on equal employment obligations"
        ]
    },

    "independent_contractor": {
        "risk": [
            "Risk of worker misclassification",
            "Exposure to back taxes and statutory penalties",
            "Potential employment law claims"
        ],
        "solution": [
            "Ensure factual practices align with independent contractor status",
            "Avoid employer-like supervision or control",
            "Periodically review classification compliance"
        ]
    },

    "nonassignment": {
        "risk": [
            "Limits flexibility in corporate restructuring or transactions",
            "May prevent assignment during mergers or acquisitions"
        ],
        "solution": [
            "Allow assignment with reasonable consent",
            "Include exceptions for corporate restructuring"
        ]
    },

    "entire_agreement": {
        "risk": [
            "Excludes reliance on prior representations",
            "Limits ability to claim based on oral agreements"
        ],
        "solution": [
            "Ensure all material terms are captured in writing",
            "Allow amendments only through written agreement"
        ]
    }
}

def generate_final_risk_report(clause_type):
    kb = LEGAL_RISK_KB.get(clause_type)

    severity = get_severity(clause_type)

    if not kb:
        return {
            "risk_summary": "This clause requires manual legal review.",
            "severity": severity,
            "key_risks": ["No predefined risk patterns available"],
            "recommended_improvements": ["Consult a legal professional"]
        }

    return {
        "risk_summary": f"This clause introduces {clause_type.replace('_', ' ')}-related legal risk.",
        "severity": severity,
        "key_risks": kb["risk"],
        "recommended_improvements": kb["solution"]
    }



SEVERITY_RULES = {
    "termination": "HIGH",
    "independent_contractor": "HIGH",
    "ip": "HIGH",
    "indemnity": "HIGH",

    "payment": "MEDIUM",
    "audit": "MEDIUM",
    "jurisdiction": "MEDIUM",
    "employment": "MEDIUM",
    "nonassignment": "MEDIUM",

    "insurance": "LOW",
    "entire_agreement": "LOW"
}

def get_severity(clause_type):
    return SEVERITY_RULES.get(clause_type, "LOW")

