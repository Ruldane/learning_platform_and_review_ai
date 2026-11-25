from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from app.features.study.service.runtime import StudyRuntime


def get_study_runtime(conn: HTTPConnection) -> StudyRuntime:
    """The study opened by the lifespan (`app.state.study`)."""
    runtime: StudyRuntime = conn.app.state.study
    return runtime


StudyDep = Annotated[StudyRuntime, Depends(get_study_runtime)]
