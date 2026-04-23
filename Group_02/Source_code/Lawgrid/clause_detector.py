def detect_clause_type(heading, content):
    h = heading.lower()
    t = content.lower()

    # Heading-based (highest accuracy)
    if "compensation" in h or "payment" in h:
        return "payment"

    if "term" in h or "termination" in h:
        return "termination"

    if "insurance" in h:
        return "insurance"

    if "audit" in h:
        return "audit"

    if "work product" in h or "intellectual property" in h:
        return "ip"

    if "dispute" in h or "governing law" in h:
        return "jurisdiction"

    if "equal employment" in h:
        return "employment"

    if "independent consultant" in h:
        return "independent_contractor"

    if "nonassignment" in h:
        return "nonassignment"

    if "complete agreement" in h or "entire agreement" in h:
        return "entire_agreement"

    # Fallback (content-based, low confidence)
    if "governed by" in t:
        return "jurisdiction"

    if "indemnify" in t:
        return "indemnity"

    return "general"
