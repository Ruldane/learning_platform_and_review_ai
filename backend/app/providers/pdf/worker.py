"""PDF extraction worker, launched by `SubprocessPdfExtractor` (D72):

    python -m app.providers.pdf.worker <max_pages> <max_chars> <max_memory_bytes>

It sets `RLIMIT_AS` itself (POSIX; ignored elsewhere), reads the PDF from stdin and writes the text
in UTF-8 to stdout. Exit code 0: text; 3: unreadable PDF; any other code (memory exhausted, crash
of a native library) is also treated as unreadable by the parent. It imports neither FastAPI nor
the database: only `pdfplumber`, through `extract`."""

import sys

from app.providers.pdf.extract import extract_pdf_text

EXIT_OK = 0
EXIT_UNREADABLE = 3


def limit_memory(max_bytes: int) -> None:
    """Process address-space cap (an allocation beyond it raises `MemoryError`). No effect outside
    POSIX:
    `resource` does not exist on Windows (development only)."""
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
    # `replace`: a lone character outside valid Unicode (surrogate) does not make the page fail.
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
