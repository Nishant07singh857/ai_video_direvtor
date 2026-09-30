from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.dataset_builder import DatasetBuilder

router = APIRouter()
dataset_builder = DatasetBuilder(db_session=None)

class ExportRequest(BaseModel):
    filename: str = "dataset.jsonl"

@router.post("/extract")
def extract_decisions():
    try:
        data = dataset_builder.extract_timeline_decisions()
        return {"decisions": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
def export_dataset(request: ExportRequest):
    try:
        data = dataset_builder.extract_timeline_decisions()
        filepath = dataset_builder.export_to_jsonl(data, request.filename)
        return {"status": "success", "filepath": filepath}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
