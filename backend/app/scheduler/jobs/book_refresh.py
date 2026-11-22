from app.features.book.service.refresh import refresh_books
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    if ctx.book is not None:
        await refresh_books(ctx.book)
