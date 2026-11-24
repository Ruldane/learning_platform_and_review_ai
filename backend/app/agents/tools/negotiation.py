"""The figures of a salary survey and the separate outcome of the salary role-play."""

from typing import Literal

from pydantic import BaseModel, Field

SalaryReason = Literal["ceiling_reached", "budget_held", "fixed_amount"]


class SalarySample(BaseModel):
    run_id: str
    role: str
    zone: str
    minimum_eur: int = Field(gt=0)
    maximum_eur: int = Field(gt=0)
    observations: int = Field(gt=0)


class SalaryOutcome(BaseModel):
    offer_eur: int
    remaining_eur: int
    reason: SalaryReason


def salary_outcome(sample: SalarySample, raised: bool) -> SalaryOutcome:
    offered = sample.maximum_eur if raised else sample.minimum_eur
    reason: SalaryReason = "ceiling_reached" if raised else "budget_held"
    if sample.minimum_eur == sample.maximum_eur:
        reason = "fixed_amount"
    return SalaryOutcome(
        offer_eur=offered, remaining_eur=sample.maximum_eur - offered, reason=reason
    )
