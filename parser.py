# parser.py — 10-K / 10-Q Section Extractor
# Extracts MD&A and Risk Disclosure sections from SEC filing HTML.
# Uses BeautifulSoup + regex; handles varied formatting across filers.

import re
from bs4 import BeautifulSoup, Tag

# ─── Item targets ──────────────────────────────────────────────────
# 10-K sections
ITEMS_10K = {
    "risk_factors":   ("1A", "RISK FACTORS"),
    "mda":            ("7",  "MANAGEMENT"),
    "market_risk":    ("7A", "QUANTITATIVE AND QUALITATIVE"),
}
# 10-Q sections
ITEMS_10Q = {
    "mda":         ("2",  "MANAGEMENT"),
    "market_risk": ("3",  "QUANTITATIVE AND QUALITATIVE"),
    "risk_factors": ("1A", "RISK FACTORS"),
}

_ITEM_RE = re.compile(
    r"item\s+(\d+[a-c]?)\s*[.\-–—:]?\s*(.{0,80})",
    re.IGNORECASE,
)

_CLEAN_RE = re.compile(r"\s{2,}")


def _clean(text: str) -> str:
    """Collapse whitespace and strip boilerplate page markers."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _CLEAN_RE.sub(" ", text)
    return text.strip()


def _find_item_anchors(soup: BeautifulSoup) -> list[tuple[str, Tag]]:
    """
    Return a list of (item_number_str, tag) from navigation anchors,
    covering both <a name="item7"> and <div id="item7"> patterns.
    """
    anchors: list[tuple[str, Tag]] = []

    # Named anchors
    for tag in soup.find_all("a", attrs={"name": True}):
        name = tag.get("name", "")
        m = re.match(r"(?:item|i)(\d+[a-c]?)", name, re.IGNORECASE)
        if m:
            anchors.append((m.group(1).lower(), tag))

    # Headings with item text
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "b", "strong", "p"]):
        text = tag.get_text(" ", strip=True)
        m = _ITEM_RE.match(text)
        if m:
            anchors.append((m.group(1).lower(), tag))

    return anchors


def _extract_between(start_tag: Tag, end_tag: Tag | None, max_chars: int = 80_000) -> str:
    """Collect text from all siblings between start_tag and end_tag."""
    texts: list[str] = []
    length = 0
    node = start_tag.next_sibling

    while node is not None and (end_tag is None or node != end_tag):
        if hasattr(node, "get_text"):
            chunk = node.get_text(" ", strip=True)
        else:
            chunk = str(node).strip()
        if chunk:
            texts.append(chunk)
            length += len(chunk)
            if length > max_chars:
                break
        node = node.next_sibling

    return _clean(" ".join(texts))


def _fallback_section(text: str, item_num: str, next_item_num: str | None) -> str:
    """Plain-text fallback: look for ITEM X ... ITEM Y."""
    pattern = rf"ITEM\s+{re.escape(item_num)}\b.{{0,120}}"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ""

    start = match.start()
    end = len(text)
    if next_item_num:
        next_pat = rf"ITEM\s+{re.escape(next_item_num)}\b"
        m2 = re.search(next_pat, text[start + 50:], re.IGNORECASE)
        if m2:
            end = start + 50 + m2.start()

    return _clean(text[start:end][:80_000])


def extract_sections(html: str, form_type: str = "10-K") -> dict[str, str]:
    """
    Parse an SEC filing HTML string and return a dict with keys:
        'mda', 'risk_factors', 'market_risk'
    Each value is the extracted plain-text (up to ~80 000 chars).
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove script/style noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    items_map = ITEMS_10K if form_type == "10-K" else ITEMS_10Q
    anchors = _find_item_anchors(soup)

    # Build a lookup: item_num → first matching tag
    anchor_dict: dict[str, Tag] = {}
    for num, tag in anchors:
        if num not in anchor_dict:
            anchor_dict[num] = tag

    sections: dict[str, str] = {}
    plain_text = soup.get_text("\n")

    for section_key, (item_num, _keyword) in items_map.items():
        start_tag = anchor_dict.get(item_num.lower())

        # Find the tag immediately after this item
        next_tag: Tag | None = None
        for other_num, other_tag in anchors:
            if other_num.lower() != item_num.lower() and start_tag is not None:
                # Pick the next distinct item anchor that comes after start_tag
                if start_tag.find_next(other_tag.name) == other_tag:
                    next_tag = other_tag
                    break

        if start_tag is not None:
            extracted = _extract_between(start_tag, next_tag)
            # If extraction yielded too little, fall back to plain-text
            if len(extracted) < 200:
                # Determine next item number for fallback
                nums_in_order = [n for n, _ in anchors]
                try:
                    idx = nums_in_order.index(item_num.lower())
                    next_num = nums_in_order[idx + 1] if idx + 1 < len(nums_in_order) else None
                except ValueError:
                    next_num = None
                extracted = _fallback_section(plain_text, item_num, next_num)
        else:
            # Pure plain-text extraction as last resort
            nums_in_order = list(anchor_dict.keys())
            try:
                idx = nums_in_order.index(item_num.lower())
                next_num = nums_in_order[idx + 1] if idx + 1 < len(nums_in_order) else None
            except ValueError:
                next_num = None
            extracted = _fallback_section(plain_text, item_num, next_num)

        sections[section_key] = extracted or "(Section not found in this filing.)"

    return sections


def section_word_count(text: str) -> int:
    """Count words in a section text."""
    return len(text.split())


def get_section_stats(sections: dict[str, str]) -> dict[str, dict]:
    """Return basic stats (word_count, char_count) for each section."""
    return {
        key: {
            "word_count": section_word_count(text),
            "char_count": len(text),
            "found": not text.startswith("(Section not"),
        }
        for key, text in sections.items()
    }
