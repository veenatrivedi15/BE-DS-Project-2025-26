from explanation_engine import explanation_engine

def refine_explanation(
    clause_text,
    clause_type,
    severity,
    base_risks,
    base_recommendations
):
    """
    Non-GenAI explanation selector using TF-IDF similarity
    """
    return explanation_engine.get_best_explanation(
        clause_text,
        clause_type
    )
