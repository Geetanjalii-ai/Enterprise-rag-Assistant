import re


def clean_text(text: str) -> str:
    """Clean extracted document text: repeated headers/footers, broken characters, excess whitespace."""
    if not text:
        return ""

    # Replace null and non-printable control characters (keep newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize carriage returns and line feeds
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize non-breaking spaces
    text = text.replace("\xa0", " ")

    # Clean up page numbers / footer lines like 'Page 1 of 5' or '--- Page 2 ---'
    text = re.sub(r"(?i)\bpage\s+\d+\s+of\s+\d+\b", "", text)
    text = re.sub(r"(?i)-{2,}\s*page\s+\d+\s*-{2,}", "", text)

    # Clean multiple consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
