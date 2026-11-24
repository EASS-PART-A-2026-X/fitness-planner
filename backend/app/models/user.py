from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "appuser"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=32)
    password_hash: str = Field(max_length=256)


class AuthSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="appuser.id", index=True)
    token_hash: str = Field(unique=True, index=True, max_length=64)
    expires_at: int = Field(index=True)


class UserPublic(SQLModel):
    id: int
    username: str


class AuthResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
