"""SQLAlchemy models for VoiceScreen."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    tg_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tariff: Mapped[str] = mapped_column(String(50), default="start")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vacancies: Mapped[list["Vacancy"]] = relationship(back_populates="client")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    title: Mapped[str] = mapped_column(String(255))
    scenario_name: Mapped[str] = mapped_column(String(100))
    pass_score: Mapped[float] = mapped_column(Float, default=6.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="vacancies")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="vacancy")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"))
    phone: Mapped[str] = mapped_column(String(20))
    fio: Mapped[str] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vacancy: Mapped["Vacancy"] = relationship(back_populates="candidates")
    calls: Mapped[list["Call"]] = relationship(back_populates="candidate")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    score_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    voximplant_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="calls")
    turns: Mapped[list["CallTurn"]] = relationship(back_populates="call")


class CallTurn(Base):
    __tablename__ = "call_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id"))
    speaker: Mapped[str] = mapped_column(String(20))  # "agent" or "candidate"
    text: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    call: Mapped["Call"] = relationship(back_populates="turns")
