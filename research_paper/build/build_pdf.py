"""
Builds PrivAgent_Research_Paper.pdf from PrivAgent_Research_Paper.md.

  1. Markdown -> HTML with mistune (tables plugin).
  2. $$...$$ display math and $...$ inline math are rendered to PNG with
     matplotlib mathtext and embedded as data URIs.
  3. Figures become <figure> blocks with numbered captions.
  4. The HTML (two-column, IEEE-like CSS) is printed to PDF with headless
     Microsoft Edge (or Chrome).

Run from the repository root:
    python research_paper/build/build_pdf.py
"""
import base64
import io
import os
import re
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mistune  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAPER = os.path.join(ROOT, "research_paper")
MD = os.path.join(PAPER, "PrivAgent_Research_Paper.md")
HTML = os.path.join(PAPER, "build", "PrivAgent_Research_Paper.html")
PDF = os.path.join(PAPER, "PrivAgent_Research_Paper.pdf")
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]


DPI = 300


def math_png(tex, size):
    """Returns (base64 png, width_in, height_in) at true typeset size."""
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size, color="#111111")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight", pad_inches=0.01, transparent=True)
    plt.close(fig)
    from PIL import Image
    w, h = Image.open(io.BytesIO(buf.getvalue())).size
    return base64.b64encode(buf.getvalue()).decode(), w / DPI, h / DPI


def render_math(text):
    def display(m):
        tex = m.group(1).strip().replace(r"\big(", "(").replace(r"\big)", ")")
        data, w, h = math_png(tex, 9.5)
        return (f'\n<div class="eq"><img alt="" style="width:{w:.3f}in" '
                f'src="data:image/png;base64,{data}"></div>\n')

    def inline(m):
        data, w, h = math_png(m.group(1), 9.5)
        return (f'<img class="im" alt="" style="width:{w:.3f}in;height:{h:.3f}in" '
                f'src="data:image/png;base64,{data}">')
    text = re.sub(r"\$\$(.+?)\$\$", display, text, flags=re.S)
    text = re.sub(r"(?<![\\$])\$([^$\n]+?)\$", inline, text)
    return text


def embed_figures(html):
    count = [0]

    def repl(m):
        src, alt = m.group(1), m.group(2)
        count[0] += 1
        path = os.path.join(PAPER, src.replace("/", os.sep))
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        cls = "fig wide" if any(k in src for k in ("fig01", "fig02", "fig03", "fig04", "fig06", "fig07",
                                                  "fig09")) else "fig"
        return (f'<figure class="{cls}"><img src="data:image/png;base64,{data}" alt="">'
                f'<figcaption>{alt}</figcaption></figure>')
    return re.sub(r'<p><img src="([^"]+)" alt="([^"]*)" ?/?></p>', repl, html)


CSS = """
@page { size: Letter; margin: 0.7in 0.6in 0.75in 0.6in; }
body { font-family: 'Times New Roman', Times, serif; font-size: 9.6pt; line-height: 1.28; color: #111; }
.title { text-align: center; font-size: 19pt; font-weight: bold; margin: 0 0 4pt 0; line-height: 1.15; }
.subtitle { text-align: center; font-size: 12pt; font-style: italic; margin: 0 0 8pt 0; }
.authors { text-align: center; font-size: 10pt; margin-bottom: 10pt; column-span: all; }
.front { column-span: all; }
.cols { column-count: 2; column-gap: 0.28in; text-align: justify; hyphens: auto; }
h2 { font-size: 10.5pt; text-transform: uppercase; letter-spacing: 0.04em; text-align: center;
     margin: 12pt 0 5pt 0; break-after: avoid; }
h3 { font-size: 9.8pt; font-style: italic; font-weight: normal; margin: 8pt 0 3pt 0; break-after: avoid; }
p { margin: 0 0 5pt 0; }
ul, ol { margin: 0 0 5pt 0; padding-left: 14pt; }
li { margin-bottom: 2pt; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 8.2pt; }
table { border-collapse: collapse; width: 100%; font-size: 7.6pt; margin: 4pt 0 8pt 0; break-inside: avoid;
        text-align: left; }
th { border-top: 1.2px solid #000; border-bottom: 0.8px solid #000; padding: 2pt 3pt; font-weight: bold; }
td { padding: 1.6pt 3pt; border-bottom: 0.3px solid #ccc; vertical-align: top; }
td code, th code { font-size: 7pt; }
tr:last-child td { border-bottom: 1.2px solid #000; }
.tablewrap { column-span: all; break-inside: avoid; margin: 4pt 0; }
figure { margin: 6pt 0 8pt 0; break-inside: avoid; text-align: center; }
figure.wide { column-span: all; }
figure img { max-width: 100%; }
figure.wide img { max-width: 92%; }
figcaption { font-size: 8pt; text-align: left; margin-top: 3pt; }
.eq { text-align: center; margin: 4pt 0 6pt 0; break-inside: avoid; }
.eq img { max-width: 100%; height: auto; }
img.im { vertical-align: -0.28em; }
hr { display: none; }
.abstract { column-span: all; font-size: 9.2pt; margin: 0 0.15in 6pt 0.15in; text-align: justify; }
.refs p { font-size: 8pt; margin-bottom: 3pt; text-align: left; }
.draftnote { column-span: all; text-align: center; font-size: 8pt; color: #a33; margin-bottom: 6pt; }
"""


def build():
    with open(MD, encoding="utf-8") as f:
        md = f.read()
    md = re.sub(r"^---\n.*?\n---\n", "", md, count=1, flags=re.S).lstrip("\n")   # YAML front matter
    lines = md.split("\n")
    title = lines[0].lstrip("# ").strip()
    subtitle = lines[2].lstrip("# ").strip()
    body = "\n".join(lines[4:])
    body = render_math(body)
    render = mistune.create_markdown(plugins=["table"], escape=False)
    html = render(body)
    html = embed_figures(html)
    html = re.sub(r"(<table>.*?</table>)", r'<div class="tablewrap">\1</div>', html, flags=re.S)
    # Abstract (from the first <p><strong>Abstract to the Index Terms paragraph) spans both columns
    html = re.sub(r"(<p><em>\[Author.*?</p>)", r'<div class="authors">\1</div>', html, count=1, flags=re.S)
    html = re.sub(r"(<p><strong>Abstract\.</strong>.*?<p><strong>Index Terms.*?</p>)",
                  r'<div class="abstract">\1</div>', html, count=1, flags=re.S)
    html = re.sub(r"(<h2>References</h2>)(.*?)(<h3>Appendix)", r'\1<div class="refs">\2</div>\3', html,
                  count=1, flags=re.S)
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head><body>
<div class="front"><div class="title">{title}</div><div class="subtitle">{subtitle}</div></div>
<div class="draftnote">Working research draft. Results are on synthetic data; see Sections 7.7 and 8.</div>
<div class="cols">{html}</div></body></html>"""
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if browser is None:
        sys.exit("No Edge/Chrome found; HTML written to " + HTML)
    if os.path.exists(PDF):
        os.remove(PDF)
    # A separate profile directory is needed when the browser is already open.
    profile = os.path.join(os.environ.get("TEMP", PAPER), "privagent_pdf_profile")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={profile}", f"--print-to-pdf={PDF}",
                    "file:///" + HTML.replace(os.sep, "/")],
                   check=True, timeout=180, capture_output=True)
    # The launcher can return before the headless instance finishes writing.
    import time
    for _ in range(120):
        if os.path.exists(PDF) and os.path.getsize(PDF) > 0:
            time.sleep(2)
            break
        time.sleep(1)
    if not os.path.exists(PDF):
        sys.exit("PDF was not produced; HTML is at " + HTML)
    print("PDF:", PDF, os.path.getsize(PDF), "bytes")


if __name__ == "__main__":
    build()
