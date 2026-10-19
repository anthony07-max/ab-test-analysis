"""
Download the Cookie Cats A/B test data (90,189 players).

The data was released by Tactile Entertainment through a DataCamp project and is mirrored on
Kaggle (https://www.kaggle.com/datasets/yufengsui/mobile-games-ab-testing). Kaggle needs a login,
so this script uses a public GitHub mirror of the same file and checks its MD5 checksum.
No explicit licence is published for the data, so it is not committed to this repository.

Usage:  python src/download_data.py
"""
import hashlib
from pathlib import Path

import requests

URL = ("https://raw.githubusercontent.com/ryanschaub/Mobile-Games-A-B-Testing-with-Cookie-Cats/"
       "master/cookie_cats.csv")
MD5 = "99b48ea3d4a552fa6b27aac60a8cfddf"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "cookie_cats.csv"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    digest = hashlib.md5(r.content).hexdigest()
    if digest != MD5:
        raise SystemExit(f"Checksum mismatch: got {digest}, expected {MD5}")
    OUT.write_bytes(r.content)
    print(f"Saved {OUT} ({len(r.content)/1e6:.1f} MB, checksum OK)")


if __name__ == "__main__":
    main()
