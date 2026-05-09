# SCORE-IMPACT: Clean contracts for admin login + tourist anonymous bootstrap.
from datetime import datetime

from pydantic import Field

from aether_api.schemas.common import BaseDTO


class AdminLoginRequest(BaseDTO):
    email: str = Field(min_length=3, max_length=240, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=1, max_length=128)


class TokenDTO(BaseDTO):
    token: str
    token_type: str = "Bearer"  # noqa: S105 - OAuth2 token-type constant, not a secret.
    role: str
    subject: str
    expires_at: datetime


class AdminProfileDTO(BaseDTO):
    admin_id: str
    name: str
    email: str
    role: str


class AdminLoginResponseDTO(BaseDTO):
    token: TokenDTO
    profile: AdminProfileDTO
