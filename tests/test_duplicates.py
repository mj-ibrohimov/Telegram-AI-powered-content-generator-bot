from app.content.duplicate_detector import DuplicateDetector, normalize


def test_normalize_strips_html_and_punctuation():
    text = "<b>Hallo!</b> Wie geht's?"
    assert normalize(text) == "hallo wie geht s"


def test_exact_duplicate_detected():
    detector = DuplicateDetector()
    existing = ["Hallo, wie geht es dir heute?"]
    assert detector.is_exact_duplicate("Hallo, wie geht es dir heute?", existing)


def test_exact_duplicate_case_insensitive():
    detector = DuplicateDetector()
    existing = ["Hallo Welt"]
    assert detector.is_exact_duplicate("hallo welt", existing)


def test_similar_duplicate_detected_above_threshold():
    detector = DuplicateDetector(similarity_threshold=0.5)
    existing = ["Ich lerne jeden Tag Deutsch und es macht mir viel Spass beim Deutschlernen"]
    new_content = "Ich lerne jeden Tag Deutsch und es macht mir viel Spass beim Deutschlernen heute"
    assert detector.is_similar_duplicate(new_content, existing)


def test_dissimilar_content_not_duplicate():
    detector = DuplicateDetector(similarity_threshold=0.8)
    existing = ["Die Katze sitzt auf dem Tisch und schlaeft"]
    new_content = "Berlin ist die Hauptstadt von Deutschland und hat viele Museen"
    assert not detector.is_similar_duplicate(new_content, existing)


def test_no_existing_content_never_duplicate():
    detector = DuplicateDetector()
    assert not detector.is_duplicate("Some new content", [])
