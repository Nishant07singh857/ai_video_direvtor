from fastapi import APIRouter
from app.services.model_training import ModelTrainer

router = APIRouter()
trainer = ModelTrainer(dataset_path="data/datasets")

@router.post("/run_pipeline")
def run_pipeline():
    trainer.clean()
    trainer.label()
    trainer.split()
    trainer.train()
    trainer.validate()
    trainer.benchmark()
    trainer.shadow()
    return {"status": "Pipeline completed in shadow mode."}
