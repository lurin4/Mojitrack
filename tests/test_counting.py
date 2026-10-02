import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from app.counting import RANGES, analyze_file, analyze_text, is_japanese_char


class CounterTests(unittest.TestCase):
    def test_original_ranges(self):
        self.assertEqual(RANGES, [(0x3040, 0x309F), (0x30A0, 0x30FF), (0x4E00, 0x9FFF),
                                 (0x3400, 0x4DBF), (0x3000, 0x303F), (0xFF00, 0xFFEF),
                                 (0x31F0, 0x31FF), (0x1B000, 0x1B0FF)])
        for low, high in RANGES:
            self.assertTrue(is_japanese_char(chr(low)))
            self.assertTrue(is_japanese_char(chr(high)))

    def test_categories_match_original_counter(self):
        text = "\u3042\u30a2\u31f0\u6f22\u3400\u3002\uff21\uff11\uff76\U0001b000A1 \u2026"
        result = analyze_text(text)
        self.assertEqual(result["total_chars"], 14)
        self.assertEqual(result["chars"], 10)
        self.assertEqual(result["hiragana"], 1)
        self.assertEqual(result["katakana"], 2)
        self.assertEqual(result["kanji"], 2)
        self.assertEqual(result["punctuation"], 4)

    def test_original_exclusions_and_frequencies(self):
        for char in "ABC123 \n\u2026\uf900\U00020000":
            self.assertFalse(is_japanese_char(char))
        result = analyze_text("\u732b\u732b\u3042")
        self.assertEqual(result["top_characters"], [{"character": "\u732b", "count": 2},
                                                   {"character": "\u3042", "count": 1}])
        self.assertEqual(analyze_text("")["chars"], 0)

    def test_file_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("\u732b\u304c\u597d\u304d\u3002", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                analyze_file(path)
            self.assertIn("Total Japanese characters (incl. punctuation): 5", output.getvalue())
            self.assertIn("  Punctuation: 1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
