"""The Unicode ranges and category rules from the supplied count.py."""
from collections import Counter

RANGES = [
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0x3000, 0x303F),
    (0xFF00, 0xFFEF),
    (0x31F0, 0x31FF),
    (0x1B000, 0x1B0FF),
]


def is_japanese_char(ch):
    code = ord(ch)
    return any(start <= code <= end for start, end in RANGES)


def analyze_text(text):
    jp_chars = [ch for ch in text if is_japanese_char(ch)]
    counts = Counter(jp_chars)
    return {
        "chars": len(jp_chars),
        "total_chars": len(text),
        "hiragana": sum(0x3040 <= ord(ch) <= 0x309F for ch in jp_chars),
        "katakana": sum(0x30A0 <= ord(ch) <= 0x30FF or 0x31F0 <= ord(ch) <= 0x31FF for ch in jp_chars),
        "kanji": sum(0x4E00 <= ord(ch) <= 0x9FFF or 0x3400 <= ord(ch) <= 0x4DBF for ch in jp_chars),
        "punctuation": sum(0x3000 <= ord(ch) <= 0x303F or 0xFF00 <= ord(ch) <= 0xFFEF for ch in jp_chars),
        "top_characters": [{"character": ch, "count": count} for ch, count in counts.most_common(10)],
    }


def analyze_file(filepath):
    with open(filepath, "r", encoding="utf-8") as stream:
        result = analyze_text(stream.read())
    print(f"File: {filepath}")
    print(f"Total characters in file: {result['total_chars']}")
    print(f"Total Japanese characters (incl. punctuation): {result['chars']}")
    print(f"  Hiragana:    {result['hiragana']}")
    print(f"  Katakana:    {result['katakana']}")
    print(f"  Kanji:       {result['kanji']}")
    print(f"  Punctuation: {result['punctuation']}")
    print()
    print("Top 10 most common Japanese characters:")
    for row in result["top_characters"]:
        print(f"  {row['character']!r}: {row['count']}")
