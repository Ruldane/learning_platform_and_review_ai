"""Streamed reading of a response body under a cap, decompression included.

The body is read raw (`aiter_raw`) and decompressed here, with bounded output (`max_length`): the
`httpx` decoder decompresses without limit per chunk, so a gzip, brotli or zstd bomb would inflate
in memory before any check. Only `gzip` and `deflate` (zlib envelope) are accepted; the
`Accept-Encoding` header advertises only those."""

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
            # `| 32`: gzip or zlib header detected automatically.
            self._zlib = zlib.decompressobj(zlib.MAX_WBITS | 32)
        else:
            raise UrlUnsupported()

    def feed(self, data: bytes, budget: int) -> bytes:
        """At most `budget + 1` bytes: one byte over is enough to refuse the body."""
        if self._zlib is None:
            return data
        return self._zlib.decompress(data, budget + 1)

    def finish(self) -> bytes:
        """Remaining decoded data; a truncated compressed stream, or one followed by data, is
        unreadable."""
        if self._zlib is None:
            return b""
        tail = self._zlib.flush()
        if not self._zlib.eof or self._zlib.unused_data:
            raise UrlUnreadable()
        return tail


async def read_capped(response: httpx.Response) -> bytes:
    """Decoded body; `UrlTooLarge` as soon as the bytes received or decoded exceed the cap."""
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
        tail = decoder.finish()
    except zlib.error:
        raise UrlUnreadable() from None
    if decoded + len(tail) > limit:
        raise UrlTooLarge()
    chunks.append(tail)
    return b"".join(chunks)
