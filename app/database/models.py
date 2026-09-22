from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, String, Text
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    group_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    university: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    time: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    week: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    lesson_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    teacher: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    groups: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    subgroup: Mapped[str | None] = mapped_column(String(20), nullable=True)

    room: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )




class Institute(Base):
    __tablename__ = "institutes"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(255)
    )

    url: Mapped[str] = mapped_column(
        String(500),
        unique=True
    )

class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str]

    url: Mapped[str]

    institute_id: Mapped[int]

class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    group_id: Mapped[int]

    date: Mapped[date]

    time: Mapped[str]

    subject: Mapped[str]

    teacher: Mapped[str | None]

    room: Mapped[str | None]

    lesson_type: Mapped[str | None]


