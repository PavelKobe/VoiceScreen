from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.post("/upload-csv")
async def upload_candidates_csv(
    vacancy_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Upload a CSV file with candidates for a vacancy."""
    # TODO: parse CSV, create Candidate records, enqueue calls
    return {"status": "accepted", "vacancy_id": vacancy_id, "filename": file.filename}


@router.get("/{candidate_id}")
async def get_candidate(
    candidate_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get candidate details with call results."""
    # TODO: query candidate + related calls
    return {"candidate_id": candidate_id}
