"""PDF minimal valide, écrit à la main (aucune dépendance) : police Helvetica 12 pt, table `xref`
calculée ; Letter et une page par défaut, sinon taille de page et nombre de pages au choix (rendu
textuel des tests, preflight G14). Utilisé par les tests et par le contrôle de fin de phase."""

import math

_HEADER = b"%PDF-1.4\n"
LETTER = (612, 792)
_TOP_PT = 72  # première ligne de base à 72 pt du haut de la page
LEADING_PT = 14


def _escape(line: str) -> bytes:
    """Chaîne PDF littérale : `\\`, `(` et `)` échappés ; hors cp1252 → `?`."""
    escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped.encode("cp1252", errors="replace")


def _content(lines: list[str], height: int) -> bytes:
    ops = [b"BT", b"/F1 12 Tf", b"%d TL" % LEADING_PT, b"72 %d Td" % (height - _TOP_PT)]
    ops += [b"(" + _escape(line) + b") Tj T*" for line in lines]
    ops.append(b"ET")
    return b"\n".join(ops)


def _stream(lines: list[str], height: int) -> bytes:
    stream = _content(lines, height)
    return b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"


def _page(width: int, height: int, contents: int) -> bytes:
    return (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] " % (width, height)
        + b"/Resources << /Font << /F1 4 0 R >> >> /Contents %d 0 R >>" % contents
    )


def make_pdf(lines: list[str], *, size: tuple[int, int] = LETTER, pages: int = 1) -> bytes:
    """`lines` réparties dans l'ordre sur `pages` pages (autant de lignes par page, la dernière
    en a moins ; une page sans ligne reste blanche) de `size` points (largeur, hauteur)."""
    if pages < 1:
        raise ValueError("au moins une page")
    width, height = size
    per_page = max(1, math.ceil(len(lines) / pages))
    chunks = [lines[index * per_page : (index + 1) * per_page] for index in range(pages)]
    # Objets 1 à 5 : catalogue, pages, première page, police, contenu de la première page ;
    # chaque page suivante ajoute sa page et son contenu.
    kids = [3, *(6 + 2 * index for index in range(pages - 1))]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%b] /Count %d >>"
        % (b" ".join(b"%d 0 R" % kid for kid in kids), pages),
        _page(width, height, 5),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        _stream(chunks[0], height),
    ]
    for kid, chunk in zip(kids[1:], chunks[1:], strict=True):
        objects += [_page(width, height, kid + 1), _stream(chunk, height)]
    out = bytearray(_HEADER)
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


if __name__ == "__main__":
    import sys

    sys.stdout.buffer.write(make_pdf(sys.argv[1:] or ["Bonjour Tremplin"]))
