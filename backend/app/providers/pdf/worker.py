"""Worker d'extraction PDF, lancé par `SubprocessPdfExtractor` (D72) :

    python -m app.providers.pdf.worker <max_pages> <max_chars> <max_memory_bytes>

Pose lui-même `RLIMIT_AS` (POSIX ; ignoré ailleurs), lit le PDF sur stdin et écrit le texte en
UTF-8 sur stdout. Code 0 : texte ; 3 : PDF illisible ; tout autre code (mémoire épuisée, plantage
d'une bibliothèque native) est aussi traité en illisible par le parent. N'importe ni FastAPI ni la
base : seulement `pdfplumber`, au travers d'`extract`."""

import sys

from app.providers.pdf.extract import extract_pdf_text

EXIT_OK = 0
EXIT_UNREADABLE = 3


def limit_memory(max_bytes: int) -> None:
    """Plafond de l'espace d'adressage du processus (une allocation au-delà lève `MemoryError`).
    Sans effet hors POSIX : `resource` n'existe pas sous Windows (développement seulement)."""
    if sys.platform != "win32":
        import resource

        _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        limit = max_bytes if hard == resource.RLIM_INFINITY else min(max_bytes, hard)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def main(argv: list[str]) -> int:
    max_pages, max_chars, max_memory = (int(arg) for arg in argv)
    limit_memory(max_memory)
    data = sys.stdin.buffer.read()
    try:
        text = extract_pdf_text(data, max_pages, max_chars)
    except Exception:
        return EXIT_UNREADABLE
    # `replace` : un caractère isolé hors Unicode valide (surrogate) ne fait pas échouer la page.
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
