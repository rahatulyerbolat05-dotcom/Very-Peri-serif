"""Explicit later outline revisions allowed by earlier shape-specific regressions.

The latest batch has its own strict whole-font baseline check. This declaration
keeps old ya/ghe regressions usable without treating every later edit as a bug.
"""
import json
from pathlib import Path


def later_outline_changes(version, style, include_representation=True):
    revisions = json.loads(Path('data/curve-finish/manifest.json').read_text()).get('outline_revisions', {})
    key = lambda s: tuple(int(x) for x in s.split('.'))
    return {name for release, record in revisions.items() if key(release) > key(version)
            and (include_representation or not record.get('geometry_preserving'))
            for name in record['glyphs'].get(style, [])}
