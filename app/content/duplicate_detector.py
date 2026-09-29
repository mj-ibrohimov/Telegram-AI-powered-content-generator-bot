import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class DuplicateDetector:
    def __init__(self, similarity_threshold: float = 0.80):
        self.similarity_threshold = similarity_threshold

    def is_exact_duplicate(self, content: str, existing_contents: list[str]) -> bool:
        normalized = normalize(content)
        return any(normalized == normalize(existing) for existing in existing_contents)

    def is_similar_duplicate(self, content: str, existing_contents: list[str]) -> bool:
        if not existing_contents:
            return False

        normalized_new = normalize(content)
        normalized_existing = [normalize(c) for c in existing_contents if c.strip()]
        if not normalized_new or not normalized_existing:
            return False

        corpus = normalized_existing + [normalized_new]
        try:
            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            return False

        new_vector = matrix[-1]
        existing_vectors = matrix[:-1]
        similarities = cosine_similarity(new_vector, existing_vectors)[0]
        return bool(similarities.max() >= self.similarity_threshold) if len(similarities) else False

    def is_duplicate(self, content: str, existing_contents: list[str]) -> bool:
        return self.is_exact_duplicate(content, existing_contents) or self.is_similar_duplicate(
            content, existing_contents
        )
