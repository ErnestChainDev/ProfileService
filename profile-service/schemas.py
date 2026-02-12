from typing import Optional
from pydantic import BaseModel, Field

class ProfileUpsertIn(BaseModel):
    full_name: Optional[str] = None
    year_level: Optional[str] = None

    bio: Optional[str] = Field(
        default=None,
        description="Short personal bio / self-introduction",
        max_length=300,
    )

    interests: Optional[str] = Field(default=None)
    career_goals: Optional[str] = Field(default=None)

    preferred_program: Optional[str] = Field(
        default=None,
        description="Optional target program: BSCS/BSIT/BSIS/BTVTED",
        pattern=r"^(|BSCS|BSIT|BSIS|BTVTED)$",
    )

    skills: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class UserOut(BaseModel):
    id: int
    email: str

class ProfileOut(BaseModel):
    user_id: int
    full_name: str
    year_level: str
    bio: str
    interests: str
    career_goals: str
    preferred_program: str
    skills: str
    notes: str
