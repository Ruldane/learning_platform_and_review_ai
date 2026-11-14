"""Worker de mise en page d'un CV, lancé par `SubprocessPdfLayoutExtractor` (D119, sur le modèle
de D72) :

    python -m app.providers.pdf.layout_worker <max_pages> <max_memory_bytes> <dpi> <max_side_pt>

Pose lui-même `RLIMIT_AS` (POSIX), lit le PDF sur stdin et écrit la mise en page en JSON (ASCII,
images PNG en base64) sur stdout. Code 0 : mise en page ; 3 : PDF illisible ; 4 : trop de pages ;
5 : page tournée avec du texte ; tout autre code (mémoire épuisée, plantage d'une bibliothèque
native) est traité en illisible par le parent. N'importe ni FastAPI ni la base."""

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
