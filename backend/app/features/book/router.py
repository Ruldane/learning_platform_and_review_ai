from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.book.schemas import BookFormat, BookOut
from app.features.book.service import editions
from app.features.book.service.runtime import BookRuntime

router = APIRouter(prefix="/programs/{program_id}/book", tags=["book"])
MIME: dict[BookFormat, str] = {"pdf": "application/pdf", "epub": "application/epub+zip"}
_FILE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            mime: {"schema": {"type": "string", "format": "binary"}} for mime in MIME.values()
        }
    }
}


def get_book_runtime(conn: HTTPConnection) -> BookRuntime:
    runtime: BookRuntime = conn.app.state.book
    return runtime


BookDep = Annotated[BookRuntime, Depends(get_book_runtime)]


@router.get("", response_model=BookOut)
async def get_book(program_id: str, current: CurrentUserDep, db: Db) -> BookOut:
    return await editions.read_edition(db, current.id, program_id)


@router.post("", response_model=BookOut, status_code=status.HTTP_202_ACCEPTED)
async def request_book(program_id: str, current: CurrentUserDep, db: Db) -> BookOut:
    return await editions.queue_edition(db, current.id, program_id)


@router.get("/{format}", response_class=Response, responses=_FILE_RESPONSE)
async def download_book(
    program_id: str, format: BookFormat, current: CurrentUserDep, runtime: BookDep
) -> Response:
    content = await editions.download(runtime, current.id, program_id, format)
    return Response(
        content,
        media_type=MIME[format],
        headers={
            "Content-Disposition": f'attachment; filename="ton-livre.{format}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
