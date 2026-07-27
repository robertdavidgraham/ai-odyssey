"""Build the book-only Odyssey PDF and remove PDF metadata from the result.

Requires Pandoc, XeLaTeX, and pypdf (install with: python -m pip install pypdf).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / "tmp" / "pdfs"
OUTPUT_PDF = ROOT / "output" / "odyssey.pdf"
COMBINED_MD = TMP_DIR / "odyssey.md"
HEADER_TEX = TMP_DIR / "odyssey-header.tex"


def source_documents() -> list[tuple[str, Path, str]]:
    documents = [("Preface", ROOT / "book" / "odyssey-book-00-preface.md", "preface")]
    documents.extend(
        (
            f"Book {book:02d}",
            ROOT / "book" / f"odyssey-book-{book:02d}.md",
            f"book-{book:02d}",
        )
        for book in range(1, 25)
    )
    return documents


def normalize_markdown(text: str) -> str:
    output: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^ {1,3}([-+*])(?=[ \t]+)", r"\1", line)
        is_list_item = bool(re.match(r"^[-+*][ \t]+", line))
        previous_is_list_item = bool(
            output and re.match(r"^[-+*][ \t]+", output[-1])
        )
        if is_list_item and output and output[-1].strip() and not previous_is_list_item:
            output.append("")
        output.append(line)
    return "\n".join(output)


def expose_unreferenced_footnotes(text: str) -> str:
    definition_pattern = re.compile(
        r"(?m)^\[\^([^\]]+)\]:[ \t]*(.*(?:\n(?: {4}|\t).*)*)"
    )
    unused: list[tuple[str, str]] = []

    def replace_definition(match: re.Match[str]) -> str:
        key = match.group(1)
        if len(re.findall(rf"\[\^{re.escape(key)}\]", text)) > 1:
            return match.group(0)
        note = re.sub(r"\n(?: {4}|\t)", "\n", match.group(2)).strip()
        unused.append((key, note))
        return ""

    text = definition_pattern.sub(replace_definition, text).rstrip()
    if unused:
        text += "\n\n### Unreferenced Footnote Definitions\n\n"
        text += (
            "These note definitions are present in the source Markdown even though "
            "no footnote marker links to them.\n\n"
        )
        text += "\n\n".join(f"**Note {key}.** {note}" for key, note in unused)
    return text


def namespace_footnotes(text: str, namespace: str) -> str:
    return re.sub(
        r"\[\^([^\]]+)\]",
        lambda match: f"[^{namespace}-{match.group(1)}]",
        text,
    )


def demote_headings(text: str) -> str:
    return re.sub(r"(?m)^(#{1,5})([ \t]+)", r"#\1\2", text)


def build_markdown(documents: list[tuple[str, Path, str]]) -> None:
    chunks: list[str] = []
    for index, (label, path, anchor) in enumerate(documents, start=1):
        text = path.read_text(encoding="utf-8").strip()
        text = normalize_markdown(text)
        text = expose_unreferenced_footnotes(text)
        text = namespace_footnotes(text, f"doc{index:02d}")
        text = demote_headings(text)
        chunks.extend(
            [
                r"\clearpage",
                "",
                r"\phantomsection",
                "",
                f"# {label} {{#{anchor}}}",
                "",
                text,
                "",
            ]
        )
    COMBINED_MD.write_text("\n".join(chunks), encoding="utf-8")


def build_header() -> None:
    header = r"""
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{titling}
\usepackage{tocloft}

\definecolor{OdysseyNavy}{HTML}{17324D}
\definecolor{OdysseyGold}{HTML}{A06C24}
\definecolor{OdysseyGray}{HTML}{5C6670}

\setlength{\parindent}{1.25em}
\setlength{\parskip}{0.22em}
\setlist{itemsep=0.2em,topsep=0.45em,leftmargin=1.7em}

\titleformat{\section}
  {\huge\sffamily\bfseries\color{OdysseyNavy}}
  {}{0pt}{}
  [\vspace{0.25em}\color{OdysseyGold}\titlerule]
\titlespacing*{\section}{0pt}{0pt}{1.1em}

\titleformat{\subsection}
  {\Large\sffamily\bfseries\color{OdysseyNavy}}
  {}{0pt}{}
\titlespacing*{\subsection}{0pt}{1.6em}{0.65em}

\titleformat{\subsubsection}
  {\large\sffamily\bfseries\color{OdysseyGray}}
  {}{0pt}{}
\titlespacing*{\subsubsection}{0pt}{1.25em}{0.45em}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\sffamily\color{OdysseyGray}\nouppercase{\leftmark}}
\fancyfoot[C]{\small\sffamily\color{OdysseyGray}\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\footrulewidth}{0pt}
\setlength{\headheight}{14pt}

\pretitle{\begin{center}\vspace*{1.1in}\Huge\sffamily\bfseries\color{OdysseyNavy}}
\posttitle{\par\vspace{0.3in}\color{OdysseyGold}\rule{0.72\textwidth}{1.2pt}\end{center}}
\preauthor{\begin{center}\large\sffamily\color{OdysseyGray}}
\postauthor{\par\end{center}}
\predate{\begin{center}\normalsize\sffamily\color{OdysseyGray}}
\postdate{\par\vfill\end{center}\clearpage}

\renewcommand{\contentsname}{Table of Contents}
\setlength{\cftbeforesecskip}{0.08em}
\renewcommand{\cftsecfont}{\small\sffamily}
\renewcommand{\cftsecpagefont}{\small\sffamily}
"""
    HEADER_TEX.write_text(header.strip() + "\n", encoding="utf-8")


def build_pdf() -> None:
    command = [
        "pandoc",
        str(COMBINED_MD),
        "--from=markdown+footnotes+smart",
        "--pdf-engine=xelatex",
        "--toc",
        "--toc-depth=1",
        "--standalone",
        "--include-in-header",
        str(HEADER_TEX),
        "--metadata",
        "title=The Odyssey",
        "--metadata",
        "subtitle=Retold in English, with Explanations",
        "--metadata",
        "author=",
        "--metadata",
        "date=",
        "--variable",
        "papersize=letter",
        "--variable",
        "fontsize=11pt",
        "--variable",
        "geometry:top=0.82in,bottom=0.82in,left=0.88in,right=0.88in",
        "--variable",
        "mainfont=TeX Gyre Pagella",
        "--variable",
        "sansfont=TeX Gyre Heros",
        "--variable",
        "monofont=TeX Gyre Cursor",
        "--variable",
        "linestretch=1.08",
        "--output",
        str(OUTPUT_PDF),
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def strip_pdf_metadata() -> None:
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject
    except ImportError as error:
        raise RuntimeError(
            "pypdf is required to remove PDF metadata. Install it with: "
            "python -m pip install pypdf"
        ) from error

    temporary_pdf = TMP_DIR / "odyssey-no-metadata.pdf"
    reader = PdfReader(OUTPUT_PDF)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.root_object.pop(NameObject("/Metadata"), None)
    writer._info = None
    with temporary_pdf.open("wb") as stream:
        writer.write(stream)
    temporary_pdf.replace(OUTPUT_PDF)


def main() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    documents = source_documents()
    missing = [str(path) for _, path, _ in documents if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing source documents: " + ", ".join(missing))
    build_markdown(documents)
    build_header()
    build_pdf()
    strip_pdf_metadata()
    print(OUTPUT_PDF)


if __name__ == "__main__":
    main()
