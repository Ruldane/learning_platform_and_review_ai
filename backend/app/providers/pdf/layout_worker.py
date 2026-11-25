"""CV layout worker, launched by `SubprocessPdfLayoutExtractor` (D119, modelled on D72):

    python -m app.providers.pdf.layout_worker <max_pages> <max_memory_bytes> <dpi> <max_side_pt>

It sets `RLIMIT_AS` itself (POSIX), reads the PDF from stdin and writes the layout as JSON (ASCII,
PNG images in base64) to stdout. Exit code 0: layout; 3: unreadable PDF; 4: too many pages;
5: rotated page with text; any other code (memory exhausted, crash of a native library) is treated
as unreadable by the parent. It imports neither FastAPI nor the database."""

import json
import sys

from app.providers.pdf.layout_extract import RotatedPage, TooManyPages, extract_layout_payload
from app.providers.pdf.worker import limit_memory

EXIT_OK = 0
EXIT_UNREADABLE = 3
EXIT_TOO_MANY_PAGES = 4
EXIT_ROTATED_PAGE = 5


def main(argv: list[str]) -> int:
    max_pages, max_memory, dpi, max_side = (int(arg) for arg in argv)
    limit_memory(max_memory)
    data = sys.stdin.buffer.read()
    try:
        payload = extract_layout_payload(data, max_pages, dpi, max_side)
    except TooManyPages:
        return EXIT_TOO_MANY_PAGES
    except RotatedPage:
        return EXIT_ROTATED_PAGE
    except Exception:
        return EXIT_UNREADABLE
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=True).encode("ascii"))
    sys.stdout.buffer.flush()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
