"""Lecture en flux d'un corps de réponse sous plafond, décompression comprise.

Le corps est lu brut (`aiter_raw`) et décompressé ici, sortie bornée (`max_length`) : le
décodeur de `httpx` décompresse sans limite par morceau, donc une bombe gzip, brotli ou zstd
y gonflerait en mémoire avant tout contrôle. Seuls `gzip` et `deflate` (enveloppe zlib) sont
acceptés ; `Accept-Encoding` n'annonce qu'eux."""

import zlib

import httpx

from app.providers.web import base
from app.providers.web.base import UrlTooLarge, UrlUnreadable, UrlUnsupported

ACCEPT_ENCODING = "gzip, deflate"
_IDENTITY = ("", "identity")
_COMPRESSED = ("gzip", "x-gzip", "deflate")


def declared_too_large(response: httpx.Response, limit: int) -> bool:
    length = response.headers.get("content-length", "").strip()
    return length.isdigit() and int(length) > limit


class _Decoder:
    def __init__(self, encoding: str) -> None:
        if encoding in _IDENTITY:
            self._zlib = None
        elif encoding in _COMPRESSED:
            # `| 32` : en-tête gzip ou zlib détecté automatiquement.
            self._zlib = zlib.decompressobj(zlib.MAX_WBITS | 32)
        else:
            raise UrlUnsupported()

    def feed(self, data: bytes, budget: int) -> bytes:
        """Au plus `budget + 1` octets : un dépassement suffit à refuser le corps."""
        if self._zlib is None:
            return data
        return self._zlib.decompress(data, budget + 1)

    def flush(self) -> bytes:
        return b"" if self._zlib is None else self._zlib.flush()


async def read_capped(response: httpx.Response) -> bytes:
    """Corps décodé ; `UrlTooLarge` dès que les octets reçus ou décodés dépassent le plafond."""
    limit = base.FETCH_MAX_BYTES
    decoder = _Decoder(response.headers.get("content-encoding", "").strip().lower())
    chunks: list[bytes] = []
    received = decoded = 0
    try:
        async for raw in response.aiter_raw():
            received += len(raw)
            if received > limit:
                raise UrlTooLarge()
            data = decoder.feed(raw, limit - decoded)
            decoded += len(data)
            if decoded > limit:
                raise UrlTooLarge()
            chunks.append(data)
        tail = decoder.flush()
    except zlib.error:
        raise UrlUnreadable() from None
    if decoded + len(tail) > limit:
        raise UrlTooLarge()
    chunks.append(tail)
    return b"".join(chunks)
