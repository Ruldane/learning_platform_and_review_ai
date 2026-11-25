"""Teaching criteria used alongside fact-checking."""

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose

MIN_GRADE = 75
CRITERIA = {
    "definitions": "Definitions and prerequisites",
    "depth": "Depth of explanation",
    "example": "Worked example",
    "exercise": "Exercise and solution",
    "continuity": "Chapter progression",
}


class Grade(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: Prose = Field(min_length=1, max_length=300)


class LessonGrades(BaseModel):
    definitions: Grade
    depth: Grade
    example: Grade
    exercise: Grade
    continuity: Grade

    def _by_name(self) -> dict[str, Grade]:
        return {
            "definitions": self.definitions,
            "depth": self.depth,
            "example": self.example,
            "exercise": self.exercise,
            "continuity": self.continuity,
        }

    def scores(self) -> dict[str, int]:
        return {name: grade.score for name, grade in self._by_name().items()}

    def problems(self) -> list[str]:
        return [
            f"{CRITERIA[name]} ({grade.score}/100, minimum {MIN_GRADE}) — {grade.reason}"
            for name, grade in self._by_name().items()
            if grade.score < MIN_GRADE
        ]
