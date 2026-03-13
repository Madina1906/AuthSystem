from sqlalchemy import Column, Integer, String, Enum
from app.database import Base
import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, nullable=True)  
    password = Column(String)
    google_id = Column(String, nullable=True)
    role = Column(Enum(Role), default=Role.ADMIN)


