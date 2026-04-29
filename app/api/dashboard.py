"""Dashboard aggregations for HR-кабинета.

Все запросы скоупируются по client_id через JOIN на Vacancy.client_id.
Запросы оптимизированы для пилотных объёмов (десятки вакансий, сотни
кандидатов, тысячи звонков). Для больших баз можно будет добавить
materialized view или предсчитанные счётчики.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._time import iso_utc
from app.api.deps import get_current_principal
from app.db.models import Call, Candidate, Client, Vacancy
from app.db.session import get_session

router = APIRouter()


@router.get("")
async def get_dashboard(
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Сводка по клиенту: KPI, разбивка решений, активность за 7 дней,
    последние звонки."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today_start - timedelta(days=6)  # 7 дней включая сегодня

    candidates_q = (
        select(Candidate.id)
        .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
        .where(Vacancy.client_id == client.id)
    )
    candidates_total = (
        await session.execute(select(func.count()).select_from(candidates_q.subquery()))
    ).scalar_one()

    calls_total_q = (
        select(Call.id)
        .join(Candidate, Call.candidate_id == Candidate.id)
        .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
        .where(Vacancy.client_id == client.id)
    )
    calls_total = (
        await session.execute(select(func.count()).select_from(calls_total_q.subquery()))
    ).scalar_one()

    today_calls = (
        await session.execute(
            select(func.count())
            .select_from(
                calls_total_q.where(Call.started_at >= today_start).subquery()
            )
        )
    ).scalar_one()

    avg_score_raw = (
        await session.execute(
            select(func.avg(Call.score))
            .join(Candidate, Call.candidate_id == Candidate.id)
            .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
            .where(Vacancy.client_id == client.id, Call.score.is_not(None))
        )
    ).scalar_one()
    avg_score = round(float(avg_score_raw), 2) if avg_score_raw is not None else None

    # Разбивка по статусам кандидатов (pending / in_progress / done / exhausted).
    status_rows = (
        await session.execute(
            select(Candidate.status, func.count())
            .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
            .where(Vacancy.client_id == client.id, Candidate.active.is_(True))
            .group_by(Candidate.status)
        )
    ).all()
    by_status = {status: count for status, count in status_rows}

    # Разбивка по решениям звонков.
    decision_rows = (
        await session.execute(
            select(Call.decision, func.count())
            .join(Candidate, Call.candidate_id == Candidate.id)
            .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
            .where(Vacancy.client_id == client.id, Call.decision.is_not(None))
            .group_by(Call.decision)
        )
    ).all()
    by_decision = {decision: count for decision, count in decision_rows}

    # Звонков по дням за 7 дней (для столбчатого графика).
    # Используем func.date() — Postgres вернёт DATE, SQLAlchemy сериализует в str.
    day_rows = (
        await session.execute(
            select(func.date(Call.started_at).label("day"), func.count())
            .join(Candidate, Call.candidate_id == Candidate.id)
            .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
            .where(
                Vacancy.client_id == client.id,
                Call.started_at >= week_ago,
            )
            .group_by("day")
            .order_by("day")
        )
    ).all()
    by_day_raw = {str(day): count for day, count in day_rows}
    # Заполняем «пустые» дни нулями, чтобы график не «рваный».
    calls_by_day: list[dict] = []
    for i in range(7):
        day = (week_ago + timedelta(days=i)).date()
        calls_by_day.append({"date": day.isoformat(), "count": by_day_raw.get(str(day), 0)})

    # Последние 10 звонков с ФИО и решением.
    recent_rows = (
        await session.execute(
            select(Call, Candidate.fio)
            .join(Candidate, Call.candidate_id == Candidate.id)
            .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
            .where(Vacancy.client_id == client.id)
            .order_by(desc(Call.id))
            .limit(10)
        )
    ).all()
    recent_calls = [
        {
            "id": call.id,
            "candidate_id": call.candidate_id,
            "candidate_fio": fio,
            "started_at": iso_utc(call.started_at),
            "decision": call.decision,
            "score": call.score,
        }
        for call, fio in recent_rows
    ]

    # Сколько активных вакансий — для KPI «Активных вакансий».
    active_vacancies = (
        await session.execute(
            select(func.count())
            .select_from(Vacancy)
            .where(Vacancy.client_id == client.id, Vacancy.active.is_(True))
        )
    ).scalar_one()

    return {
        "candidates_total": candidates_total,
        "calls_total": calls_total,
        "calls_today": today_calls,
        "active_vacancies": active_vacancies,
        "avg_score": avg_score,
        "by_status": by_status,
        "by_decision": by_decision,
        "calls_by_day": calls_by_day,
        "recent_calls": recent_calls,
    }
