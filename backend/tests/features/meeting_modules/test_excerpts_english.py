"""English transcripts: the labels and decision sentences of the excerpts are recognised."""

from app.features.meeting_modules.excerpts import extract


def test_english_labels_and_sentences() -> None:
    excerpts = extract(
        "Decision: keep the buffer stock.\n"
        "We decided to move the review to Friday.\n"
        "To study: compare the two reorder thresholds.\n"
        "Plain remark."
    )
    assert [(item.kind, item.text) for item in excerpts] == [
        ("decision", "keep the buffer stock."),
        ("decision", "We decided to move the review to Friday."),
        ("topic", "compare the two reorder thresholds."),
        ("topic", "Plain remark."),
    ]
