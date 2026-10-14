"""Fetch and verify the pinned official Regular sources used by the studies."""
from pathlib import Path
import argparse
import hashlib
import urllib.request
import tempfile
import os

COMMIT = '65c0ef225f386a3c7e87570a4aa9cc0262c2fd81'
ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'sources/Instrument_Serif.glyphs': 'e7dd989a8d17b7cdc13130b79597d44bdd4b9dd043c801639468ef38d58a706f',
    'fonts/ttf/InstrumentSerif-Regular.ttf': '498efd461f6ddfcb7a111bf9a565709d2085d48201d501ead960d93e84ffbb88',
    'OFL.txt': '129ed7618959716959f2941fdd5b49e0ad6e6c1d78726761786a00253d865521',
    'AUTHORS.txt': 'dc1a3464426e3b099999023df8d2666e1dc0278b2bd309c59cdf63402a12c469',
    'CONTRIBUTORS.txt': '3801890cc1eb7c032518ac922bd3c7f9f277f714162365deb7aed0af383a7ce6',
}

def verify_reference(directory):
    directory = directory.resolve()
    for relative, digest in FILES.items():
        path = directory/relative
        if not path.is_file():
            raise SystemExit(f'Missing {path}; run python tools/prepare_reference.py first.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Unexpected original-source hash: {path}. File left unchanged.')
    return directory

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT/'reference/instrument-serif')
    args = parser.parse_args()
    directory = args.directory.resolve()
    # Refuse a mismatched existing reference before fetching any missing files.
    for relative, digest in FILES.items():
        path = directory/relative
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Unexpected existing source: {path}; no file was replaced.')
    for relative, digest in FILES.items():
        path = directory/relative
        if path.exists():
            continue
        url = f'https://raw.githubusercontent.com/Instrument/instrument-serif/{COMMIT}/{relative}'
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit(f'Unexpected download hash: {relative}')
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary.write(data)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path,path)
    verify_reference(directory)
    print(f'Official Regular sources verified: {COMMIT}')

if __name__ == '__main__':
    main()
