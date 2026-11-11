from pydantic import BaseModel


class MeOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    auth_mode: str
