#!/usr/bin/env python3
"""Просмотр опорных точек глифа: контур, угловые точки (синие квадраты), гладкие (зелёные круги), управляющие (оранжевые кружки) с ручками,
направляющие 0, 510, 516, −9, границы ширины. Запуск: python3 -I tools/node_view.py data/en/n4.glif out.png [x-height 510]
Рисует через Chromium (Playwright, /opt/pw-browsers/chromium-*/chrome-linux/chrome), SVG из GLIF рядом не нужен."""
import glob, re, subprocess, sys, tempfile, os
glif, out = sys.argv[1], sys.argv[2]
g = open(glif).read()
adv = float(re.search(r'<advance width="([\d.]+)"', g).group(1))
pts = [(float(x), float(y), t) for x, y, t in re.findall(r'<point x="([-\d.]+)" y="([-\d.]+)"(?: type="(\w+)")?', g)]
n = len(pts)
# контур из GLIF: сегменты считаем по точкам (qcurve с внеконтурными точками перед ним)
contours = re.findall(r'<contour>(.*?)</contour>', g, re.S)
d = []
for c in contours:
    P = [(float(x), float(y), t) for x, y, t in re.findall(r'<point x="([-\d.]+)" y="([-\d.]+)"(?: type="(\w+)")?', c)]
    m = len(P); start = next(i for i, p in enumerate(P) if p[2])
    P = P[start:] + P[:start]; d.append(f"M{P[0][0]} {P[0][1]}")
    i = 1; pend = []
    P = P + [P[0]]
    for x, y, t in P[1:]:
        if not t: pend.append((x, y))
        elif t == 'line': d.append(f"L{x} {y}"); pend = []
        else:
            if not pend: d.append(f"L{x} {y}")
            else:
                prev = None
                for k, (cx, cy) in enumerate(pend):
                    if k < len(pend) - 1:
                        nx, ny = pend[k + 1]; d.append(f"Q{cx} {cy} {(cx + nx) / 2} {(cy + ny) / 2}")
                    else: d.append(f"Q{cx} {cy} {x} {y}")
            pend = []
    d.append("Z")
S = [f"<svg xmlns='http://www.w3.org/2000/svg' width='1000' height='1180' viewBox='-30 -560 {adv + 60} 640' style='background:#fff;font-family:DejaVu Sans,sans-serif'><g transform='scale(1,-1)'>"]
for y, c in ((0, '#d55'), (510, '#59f'), (516, '#9bd'), (-9, '#e99')):
    S.append(f"<line x1='-30' x2='{adv + 30}' y1='{y}' y2='{y}' stroke='{c}' stroke-width='0.8' stroke-dasharray='4 3'/>")
S.append(f"<line x1='0' x2='0' y1='-40' y2='540' stroke='#999' stroke-width='0.8'/><line x1='{adv}' x2='{adv}' y1='-40' y2='540' stroke='#999' stroke-width='0.8'/>")
S.append(f"<path d='{' '.join(d)}' fill='#ddd' stroke='#222' stroke-width='1.2'/>")
for i, (x, y, t) in enumerate(pts):
    if not t:
        for j in (i - 1, (i + 1) % n):
            q = pts[j]
            if q[2] == 'qcurve': S.append(f"<line x1='{x}' y1='{y}' x2='{q[0]}' y2='{q[1]}' stroke='#e70' stroke-width='0.6'/>")
for x, y, t in pts:
    if t == 'line': S.append(f"<rect x='{x - 2.6}' y='{y - 2.6}' width='5.2' height='5.2' fill='#06c'/>")
    elif t == 'qcurve': S.append(f"<circle cx='{x}' cy='{y}' r='3' fill='#080'/>")
    else: S.append(f"<circle cx='{x}' cy='{y}' r='2.2' fill='#fff' stroke='#e70' stroke-width='1'/>")
S.append("</g></svg>")
html = os.path.join(tempfile.mkdtemp(), "nodes.html"); open(html, "w").write("<html><body style='margin:0'>" + "".join(S) + "</body></html>")
chrome = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")[0]
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--screenshot={os.path.abspath(out)}", "--window-size=1000,1180", f"file://{html}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"{n} точек: угловых {sum(1 for p in pts if p[2]=='line')}, гладких {sum(1 for p in pts if p[2]=='qcurve')}, управляющих {sum(1 for p in pts if not p[2])}")
