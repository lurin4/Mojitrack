"""Run manually once to vendor the pinned browser libraries. No Node required."""
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    "chart.umd.js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.js",
    "chart.LICENSE.md": "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/LICENSE.md",
    "lucide.js": "https://cdn.jsdelivr.net/npm/lucide@0.468.0/dist/umd/lucide.js",
    "lucide.LICENSE": "https://cdn.jsdelivr.net/npm/lucide@0.468.0/LICENSE",
}


def main():
    folder = ROOT / "static" / "vendor"
    folder.mkdir(parents=True, exist_ok=True)
    for name, url in ASSETS.items():
        request = Request(url, headers={"User-Agent": "reading-site-setup/0.1"})
        with urlopen(request, timeout=60) as response:
            body = response.read()
        if not body or body.lstrip().lower().startswith((b"<!doctype html", b"<html")):
            raise RuntimeError(f"Unexpected asset response: {name}")
        destination = folder / name
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(body)
        temporary.replace(destination)
        print(f"Downloaded {name}")


if __name__ == "__main__":
    main()
