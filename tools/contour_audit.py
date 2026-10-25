#!/usr/bin/env python3
"""Scan all six published fonts and produce a hash-bound absolute review queue.

This command inventories and nominates; it does not declare visual acceptance.
Use --require-reviewed to fail on unresolved/confirmed defects as well as errors.
"""
import argparse
from collections import Counter
import hashlib
import gzip
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import fontTools
import shapely
from fontTools.ttLib import TTFont
from contour_geometry import (RULES, Segment, cluster, digest, inspect_outline,
                              normalized, read_outline, serialize)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def published_version(root=Path('fonts')):
    path = root/'ttf/VeryPeriSerif-Regular.ttf'
    with TTFont(path) as font:
        match = re.match(r'Version (\d+\.\d+)\b', font['name'].getDebugName(5))
    if not match: raise ValueError('Cannot identify the published family version')
    return match[1]


def detector_hash():
    return digest({'rules': RULES, 'sources': {p: sha(Path('tools')/p) for p in
                   ('contour_geometry.py', 'contour_audit.py', 'contour_audit_report.py',
                    'contour_audit_report.html')}})


def priority(evidence):
    base = {'empty_contour': 95, 'open_contour': 95, 'zero_segment': 90,
            'undefined_tangent': 90, 'disconnected': 95, 'interior_stationary': 90,
            'self_intersection': 80, 'singular_endpoint': 60,
            'curvature_wave': 65, 'curvature_jump': 45,
            'short_segment': 45, 'near_straight_bend': 30, 'tangent_break': 25, 'transverse_step': 80}
    kinds = {e['kind'] for e in evidence}
    return min(100, max(base[e['kind']] for e in evidence)+6*(len(kinds)-1))


def apply_decisions(report, ledger):
    decisions = ledger.get('decisions', {})
    valid = {'intentional', 'defect', 'fixed_pending_recheck'}
    seen = set()
    for case in report['cases']:
        r = decisions.get(case['id'])
        if r is None: continue
        if (r.get('geometry_sha256') != case['geometry_sha256'] or
            r.get('detector_sha256') != report['detector_sha256']):
            continue
        if r.get('status') not in valid or not r.get('reason', '').strip():
            raise ValueError('Decision needs a supported status and a written reason: '+case['id'])
        case['status'] = r['status']; case['reason'] = r['reason']; seen.add(case['id'])
    report['stale_decisions'] = sorted(set(decisions)-seen)
    report['forms'] = []
    form_decisions = ledger.get('forms', {}); seen_forms = set()
    for shape_id, shape in report['shapes'].items():
        if not any(shape['contours']): continue
        for style in ('Regular', 'Italic'):
            if not any(report['fonts'][key]['style'] == style for key, _ in shape['uses']): continue
            form_id = digest([style, shape_id, report['detector_sha256'], 'whole-form'])[:24]
            row = {'id': form_id, 'style': style, 'geometry_sha256': shape_id, 'status': 'unreviewed'}
            r = form_decisions.get(form_id)
            if r and r.get('geometry_sha256') == shape_id and r.get('detector_sha256') == report['detector_sha256']:
                if r.get('status') != 'reviewed' or not r.get('reason', '').strip():
                    raise ValueError('Whole-form review needs a written reason: '+form_id)
                row.update(status='reviewed', reason=r['reason']); seen_forms.add(form_id)
            report['forms'].append(row)
    report['stale_form_decisions'] = sorted(set(form_decisions)-seen_forms)


def run(root, cache_path=None):
    report = {'schema': 1, 'release': published_version(root), 'detector_sha256': detector_hash(), 'rules': RULES,
              'coordinates': '1000 UPM; per-shape control-point bounding-box origin',
              'candidates_are_not_confirmed_defects': True,
              'fonts': {}, 'shapes': {}, 'cases': [], 'errors': []}
    engine = digest({'source': sha(Path('tools/contour_geometry.py')), 'rules': RULES,
                     'numpy': np.__version__, 'fonttools': fontTools.__version__, 'shapely': shapely.__version__})
    report['geometry_engine_sha256'] = engine
    persisted = {}
    if cache_path and cache_path.exists():
        saved = json.loads(gzip.decompress(cache_path.read_bytes()))
        if saved.get('engine') == engine: persisted = saved['shapes']
    cache = {}; case_ids = set(); hits = 0
    for style in ('Regular', 'Italic'):
        reference = None
        for fmt, folder in (('TTF', 'ttf'), ('OTF', 'otf'), ('WOFF2', 'webfonts')):
            path = root/folder/f'VeryPeriSerif-{style}.{fmt.lower()}'
            if not path.exists(): raise FileNotFoundError(path)
            font = TTFont(path); key = style+'/'+fmt
            cm = font.getBestCmap(); reverse = {}
            for cp, name in cm.items(): reverse.setdefault(name, []).append(chr(cp))
            rows = {}; data = {'file': str(path), 'sha256': sha(path), 'style': style,
                              'format': fmt, 'version': font['name'].getDebugName(5),
                              'glyphs': rows, 'glyph_count': len(font.getGlyphOrder())}
            report['fonts'][key] = data
            if fmt == 'TTF': reference = font
            if fmt == 'WOFF2':
                different = [t for t in reference.keys() if t not in ('GlyphOrder', 'head') and
                             (t not in font or reference.getTableData(t) != font.getTableData(t))]
                data['ttf_table_differences_except_head'] = different
                extra = set(font.keys())-set(reference.keys())
                if different or extra:
                    report['errors'].append({'font': key, 'error': 'WOFF2/TTF table mismatch',
                                             'tables': different, 'extra': sorted(extra)})
            for name in font.getGlyphOrder():
                try:
                    contours, closed = read_outline(font, name)
                    origin, shape_id = normalized(contours)
                    shape_id = digest([shape_id, closed])
                    rows[name] = {'shape': shape_id, 'origin': origin.tolist(),
                                  'characters': reverse.get(name, []), 'contours': len(contours)}
                    if shape_id not in cache:
                        local = [[Segment(s.points-origin) for s in c] for c in contours]
                        if shape_id in persisted:
                            cached = persisted[shape_id]; findings = cached['findings']
                            samples = [{'length': v} for v in cached['lengths']]; hits += 1
                        else:
                            findings, samples = inspect_outline(local, closed)
                            persisted[shape_id] = {'findings': findings, 'lengths': [s['length'] for s in samples]}
                        cache[shape_id] = (findings, samples)
                        points = [s.points for c in local for s in c]
                        bbox = np.vstack(points) if points else np.zeros((1, 2))
                        report['shapes'][shape_id] = {'contours': serialize(local), 'closed': closed,
                            'bounds': [*bbox.min(axis=0).tolist(), *bbox.max(axis=0).tolist()],
                            'lengths': [round(s['length'], 5) for s in samples], 'uses': []}
                    report['shapes'][shape_id]['uses'].append([key, name])
                    findings, samples = cache[shape_id]
                    for group in cluster(findings, samples):
                        anchor = max(group, key=lambda e: priority([e]))
                        case_id = digest([style, shape_id, report['detector_sha256'],
                                          anchor['contour'], anchor['s'], sorted({e['kind'] for e in group})])[:24]
                        if case_id in case_ids: continue
                        case_ids.add(case_id)
                        report['cases'].append({'id': case_id, 'style': style, 'geometry_sha256': shape_id,
                            'contour': anchor['contour'], 's': anchor['s'], 'xy': anchor['xy'],
                            'kinds': sorted({e['kind'] for e in group}), 'priority': priority(group),
                            'status': 'unreviewed', 'evidence': group})
                except Exception as exc:
                    rows[name] = {'characters': reverse.get(name, []), 'error': str(exc)}
                    report['errors'].append({'font': key, 'glyph': name, 'error': str(exc)})
            data['read_glyphs'] = sum('error' not in r for r in rows.values())
            data['read_contours'] = sum(r.get('contours', 0) for r in rows.values())
            data['unique_shapes'] = len({r['shape'] for r in rows.values() if 'shape' in r})
            print(key, data['read_glyphs'], '/', data['glyph_count'], 'glyphs;',
                  data['read_contours'], 'contours;', data['unique_shapes'], 'unique shapes', flush=True)
    report['cases'].sort(key=lambda c: (-c['priority'], c['style'], c['geometry_sha256'], c['s']))
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(gzip.compress(json.dumps({'engine': engine, 'shapes': persisted},
                               separators=(',', ':'), allow_nan=False).encode(), mtime=0))
    print('Cached geometry reused:', hits, flush=True)
    return report


def summarize(report):
    by_style = {}
    for style in ('Regular', 'Italic'):
        cases = [c for c in report['cases'] if c['style'] == style]
        by_style[style] = {'sites': len(cases), 'detector_evidence': dict(Counter(
            e['kind'] for c in cases for e in c['evidence'])),
            'statuses': dict(Counter(c['status'] for c in cases))}
    report['summary'] = {'sites': len(report['cases']), 'errors': len(report['errors']),
        'unresolved': sum(c['status'] != 'intentional' for c in report['cases']),
        'unreviewed_whole_forms': sum(f['status'] != 'reviewed' for f in report['forms']),
        'by_style': by_style, 'visual_acceptance': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path('fonts'))
    ap.add_argument('--output', type=Path)
    ap.add_argument('--html', type=Path)
    ap.add_argument('--decisions', type=Path, default=Path('data/contour-review.json'))
    ap.add_argument('--cache', type=Path, default=Path('build/contour-audit/geometry-cache.json.gz'))
    ap.add_argument('--require-reviewed', action='store_true')
    args = ap.parse_args(); report = run(args.root, args.cache)
    if args.output is None: args.output = Path(f'docs/qa/contour-audit-{report["release"]}.json')
    if args.html is None: args.html = Path(f'docs/specimen/contour-audit-{report["release"]}.html')
    ledger = json.loads(args.decisions.read_text()) if args.decisions.exists() else {'decisions': {}}
    apply_decisions(report, ledger); summarize(report)
    report['resolved_batches'] = ledger.get('resolved_batches', {})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.html.parent.mkdir(parents=True, exist_ok=True)
    # Machine-readable queue stays separate from the geometry-heavy visual report.
    machine = {k: v for k, v in report.items() if k != 'shapes'}
    machine['shapes'] = {key: {k: v for k, v in d.items() if k not in ('contours',)}
                         for key, d in report['shapes'].items()}
    queue_path = args.output.with_suffix('.json.gz')
    queue_path.write_bytes(gzip.compress(json.dumps(machine, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode(), mtime=0))
    brief = {k: v for k, v in machine.items() if k not in ('cases', 'shapes', 'forms', 'fonts')}
    brief['fonts'] = {key: {k: v for k, v in row.items() if k != 'glyphs'} for key, row in report['fonts'].items()}
    brief['queue_file'] = str(queue_path); brief['queue_sha256'] = sha(queue_path)
    args.output.write_text(json.dumps(brief, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    from contour_audit_report import write_html
    write_html(report, args.html, args.root)
    print(json.dumps(report['summary'], ensure_ascii=False))
    print(args.html)
    if report['errors'] or (args.require_reviewed and (report['summary']['unresolved'] or report['summary']['unreviewed_whole_forms'])):
        raise SystemExit(1)


if __name__ == '__main__': main()
