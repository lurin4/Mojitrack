"""Standalone file counter using the same rules as the website."""
import sys

from app.counting import analyze_file

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python count.py <path_to_txt_file>")
    analyze_file(sys.argv[1])
