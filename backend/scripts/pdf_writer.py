"""Écriture d'un fichier PDF à partir des corps de ses objets (aucune dépendance) : partagé par
les CV fictifs (`sample_cv`) et les PDF piégés des tests de mise en page."""

_HEADER = b"%PDF-1.4\n"


def assemble_pdf(objects: list[bytes], *, trailer_extra: bytes = b"") -> bytes:
    """Fichier PDF à partir des corps d'objets (numérotés à partir de 1, le 1 étant le catalogue) :
    table `xref` calculée."""
    out = bytearray(_HEADER)
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R%b >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        trailer_extra,
        xref,
    )
    return bytes(out)
