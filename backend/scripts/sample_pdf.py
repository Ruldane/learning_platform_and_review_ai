"""PDF minimal valide, écrit à la main (aucune dépendance) : une page, police Helvetica, table
`xref` calculée. Utilisé par les tests et par le contrôle de fin de phase."""

_HEADER = b"%PDF-1.4\n"


def _escape(line: str) -> bytes:
    """Chaîne PDF littérale : `\\`, `(` et `)` échappés ; hors cp1252 → `?`."""
    escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped.encode("cp1252", errors="replace")


def _content(lines: list[str]) -> bytes:
    ops = [b"BT", b"/F1 12 Tf", b"14 TL", b"72 720 Td"]
    ops += [b"(" + _escape(line) + b") Tj T*" for line in lines]
    ops.append(b"ET")
    return b"\n".join(ops)


def make_pdf(lines: list[str]) -> bytes:
    stream = _content(lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
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
