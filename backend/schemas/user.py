from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    def validate_password_length(cls, v):
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be shorter than 72 characters")
        return v



class UserResponse(BaseModel):
    id: int
    username:str
    email: EmailStr

    class Config:
        orm_mode = True
