from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from explanation_kb import EXPLANATION_KB

class ExplanationEngine:
    def __init__(self):
        self.vectorizers = {}
        self.explanation_vectors = {}

        for clause_type, explanations in EXPLANATION_KB.items():
            vectorizer = TfidfVectorizer(stop_words="english")
            vectors = vectorizer.fit_transform(explanations)

            self.vectorizers[clause_type] = vectorizer
            self.explanation_vectors[clause_type] = vectors

    def get_best_explanation(self, clause_text, clause_type):
        if clause_type not in self.vectorizers:
            return "No explanation available for this clause type."

        vectorizer = self.vectorizers[clause_type]
        explanation_vectors = self.explanation_vectors[clause_type]

        clause_vector = vectorizer.transform([clause_text])

        similarities = cosine_similarity(clause_vector, explanation_vectors)
        best_index = similarities.argmax()

        return EXPLANATION_KB[clause_type][best_index]


# Singleton instance (loaded once)
explanation_engine = ExplanationEngine()
