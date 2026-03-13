from pydantic import BaseModel


class SignupSchema(BaseModel):

    first_name: str
    last_name: str
    phone: str
    password: str


class LoginSchema(BaseModel):

    phone: str
    password: str


class CompleteProfileSchema(BaseModel):
    phone: str