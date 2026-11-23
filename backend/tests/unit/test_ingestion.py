from app.ingestion.chunkers import SectionChunker
from app.ingestion.cleaners import clean_text
from app.ingestion.metadata import DocumentManifestItem
from app.ingestion.parsers.interface import SectionContent
from app.ingestion.quarantine import evaluate_quarantine_rules


def test_clean_text():
    dirty = "Hello World!\x00\x0c\n\nPage 1 of 5\n\nSome text here\n\n\n\nMore text."
    cleaned = clean_text(dirty)
    assert "\x00" not in cleaned
    assert "Page 1 of 5" not in cleaned
    assert "Hello World!" in cleaned
    assert "Some text here" in cleaned


def test_section_chunker():
    chunker = SectionChunker(target_tokens=50, max_tokens=100, overlap_tokens=10)
    sections = [
        SectionContent(
            text="This is a test section with some basic sentence text for checking chunking.",
            heading="Introduction",
            page_number=1,
        )
    ]
    chunks = chunker.chunk_sections(sections)
    assert len(chunks) >= 1
    assert chunks[0].section == "Introduction"
    assert chunks[0].page_start == 1


def test_quarantine_evaluation():
    # Valid item
    valid_item = DocumentManifestItem(
        file="hr/policy.pdf",
        title="Policy",
        department="HR",
        visibility="company",
        min_role="member",
        owner="HR Dept",
    )
    is_q, reason = evaluate_quarantine_rules(valid_item)
    assert is_q is False
    assert reason is None

    # Missing owner
    missing_owner = DocumentManifestItem(
        file="hr/policy.pdf",
        title="Policy",
        department="HR",
        visibility="company",
        min_role="member",
        owner=None,
    )
    is_q, reason = evaluate_quarantine_rules(missing_owner)
    assert is_q is True
    assert "owner" in reason.lower()

    # Conflicting duplicate
    is_q, reason = evaluate_quarantine_rules(valid_item, duplicate_active=True)
    assert is_q is True
    assert "duplicate" in reason.lower()
