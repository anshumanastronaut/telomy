#!/usr/bin/env python3
"""Render the DPR markdown to a styled PDF (pure-Python: markdown -> HTML -> xhtml2pdf)."""
import sys, re
import markdown
from xhtml2pdf import pisa

SRC = sys.argv[1] if len(sys.argv) > 1 else "DPR.md"
OUT = sys.argv[2] if len(sys.argv) > 2 else "DPR.pdf"

md = open(SRC).read()
# map glyphs the built-in PDF fonts can't draw (box-drawing, arrows, sub/superscripts, math) to ASCII
GLYPHS = {"—": "-", "–": "-", "−": "-", "→": "->", "←": "<-", "·": "*", "×": "x", "≈": "~",
          "≥": ">=", "±": "+/-", "∧": "AND", "µ": "u", "²": "2", "³": "3", "₂": "2", "§": "Sec.",
          "Σ": "sum", "─": "-", "│": "|", "┌": "+", "┐": "+", "└": "+", "┘": "+", "├": "+",
          "┤": "+", "┬": "+", "┴": "+", "┼": "+"}
for k, v in GLYPHS.items():
    md = md.replace(k, v)
# xhtml2pdf has no GitHub-style strikethrough/emoji; keep the status glyphs as text
body = markdown.markdown(md, extensions=["tables", "fenced_code", "toc", "sane_lists"])

CSS = """
@page { size: A4; margin: 1.6cm 1.5cm 1.8cm 1.5cm; @frame footer { -pdf-frame-content: footer;
        bottom: 0.8cm; margin-left: 1.5cm; margin-right: 1.5cm; height: 1cm; } }
body { font-family: Helvetica; font-size: 9.2pt; color: #1b2a33; line-height: 1.38; }
h1 { font-size: 20pt; color: #0e7c7b; margin: 0 0 2pt 0; }
h2 { font-size: 13.5pt; color: #0e7c7b; border-bottom: 1.2pt solid #0e7c7b; padding-bottom: 2pt;
     margin: 14pt 0 6pt 0; -pdf-keep-with-next: true; }
h3 { font-size: 11pt; color: #14505a; margin: 10pt 0 3pt 0; -pdf-keep-with-next: true; }
p { margin: 3pt 0; }
strong { color: #0b3b45; }
code { font-family: Courier; font-size: 8pt; background: #eef4f4; }
pre { font-family: Courier; font-size: 7.4pt; background: #f3f7f7; border: 0.5pt solid #d6e3e3;
      padding: 5pt; color: #223; }
table { -pdf-keep-in-frame-mode: shrink; width: 100%; border-collapse: collapse; margin: 5pt 0;
        font-size: 8.2pt; }
th { background: #0e7c7b; color: #ffffff; padding: 3pt 5pt; text-align: left; }
td { border-bottom: 0.5pt solid #cfdede; padding: 3pt 5pt; vertical-align: top; }
ul, ol { margin: 3pt 0 3pt 6pt; }
li { margin: 1.5pt 0; }
hr { border: none; border-top: 0.5pt solid #cfdede; margin: 8pt 0; }
a { color: #0e7c7b; }
.footer { font-size: 7pt; color: #8aa; text-align: center; }
"""

html = f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
{body}
<div id="footer" class="footer">Telomy — Detailed Project Report (confidential) · page <pdf:pagenumber> of <pdf:pagecount></div>
</body></html>"""

with open(OUT, "wb") as f:
    res = pisa.CreatePDF(html, dest=f, encoding="utf-8")
print("PDF errors:" , res.err, "->", OUT)
