"""Standalone visual queue and complete outline atlas; no live-font geometry proxy."""
import base64
import gzip
import json
from pathlib import Path


def write_html(report, output, root):
    payload = base64.b64encode(gzip.compress(json.dumps(report, ensure_ascii=False,
                  separators=(',', ':'), allow_nan=False).encode(), mtime=0)).decode()
    faces = '\n'.join('@font-face{font-family:proof'+style+';src:url(data:font/woff2;base64,'+
        base64.b64encode((root/'webfonts'/f'VeryPeriSerif-{style}.woff2').read_bytes()).decode()+')}'
        for style in ('Regular', 'Italic'))
    source = Path(__file__).with_suffix('.html').read_text()
    output.write_text(source.replace('/* FONT_FACES */', faces).replace('/* AUDIT_DATA */', payload))
