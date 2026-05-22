from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.services.model_training_service import retrain_model_from_all_sources

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/retrain-model")
def retrain_model_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    try:
        return retrain_model_from_all_sources(db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al reentrenar el modelo: {str(e)}",
        )