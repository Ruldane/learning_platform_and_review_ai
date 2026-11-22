import io
import zipfile
from html import escape

from app.features.portfolio.schemas import Candidate, CandidateKind

CSP = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
STYLE = (
    "body{margin:0;background:#f5f4ef;color:#24241f;font:1.05rem/1.6 system-ui,sans-serif}"
    "main{width:min(88%,52rem);margin:4rem auto}"
    "h1{font-size:clamp(2.3rem,7vw,4rem);line-height:1.1}"
    "section{margin-top:2.5rem}article{background:#fff;border:1px solid #cac7bd;"
    "padding:1rem 1.4rem;margin:.75rem 0;border-radius:.5rem}a{color:#1b5541}"
    "p{white-space:pre-wrap;overflow-wrap:anywhere}"
)
SECTIONS: tuple[tuple[CandidateKind, str], ...] = (
    ("profile", "Présentation"),
    ("linkedin", "Parcours professionnel"),
    ("skill", "Compétences"),
    ("project", "Projets"),
    ("github", "Preuves GitHub"),
)


def _fact(item: Candidate) -> str:
    title = f"<h3>{escape(item.label)}</h3>" if item.label != item.text else ""
    link = ""
    if item.url:
        address = escape(item.url, quote=True)
        link = f'<a href="{address}" rel="noreferrer">Consulter la source</a>'
    return f"<article>{title}<p>{escape(item.text)}</p>{link}</article>"


def html(selected: list[Candidate]) -> bytes:
    name = next((escape(item.text) for item in selected if item.id == "name"), "Portfolio")
    parts = [
        "<!doctype html>",
        '<html lang="fr"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta http-equiv="Content-Security-Policy" content="{escape(CSP, quote=True)}">',
        f"<title>{name}</title><style>{STYLE}</style></head><body><main><h1>{name}</h1>",
    ]
    for kind, heading in SECTIONS:
        items = [_fact(item) for item in selected if item.kind == kind and item.id != "name"]
        if items:
            parts.append(f"<section><h2>{heading}</h2>{''.join(items)}</section>")
    parts.append("</main></body></html>")
    return "\n".join(parts).encode()


def archive(document: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
        entry = zipfile.ZipInfo("index.html", (1980, 1, 1, 0, 0, 0))
        entry.external_attr = 0o100644 << 16
        zipped.writestr(entry, document, zipfile.ZIP_DEFLATED)
    return buffer.getvalue()
