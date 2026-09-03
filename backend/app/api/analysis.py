from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import AnalysisBootstrapCreate, AnalysisOut, ApiResponse
from app.services import business

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/bootstrap", response_model=ApiResponse)
def post_bootstrap_analysis(payload: AnalysisBootstrapCreate, db: Session = Depends(get_db)):
    """Phase 1 helper endpoint — replace with LangGraph flow in Phase 6."""
    analysis = business.bootstrap_analysis(db, payload)
    return ApiResponse(data=AnalysisOut.model_validate(analysis).model_dump())


@router.get("/{analysis_id}", response_model=ApiResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    from app.models import AgentAnalysis

    analysis = db.get(AgentAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="analysis not found")
    return ApiResponse(data=AnalysisOut.model_validate(analysis).model_dump())
