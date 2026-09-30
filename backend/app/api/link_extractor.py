from fastapi import APIRouter
from pydantic import BaseModel
from video_engine.ingestion.link_extractor import YouTubeStyleExtractor

router = APIRouter()
extractor = YouTubeStyleExtractor()

class LinkRequest(BaseModel):
    url: str

@router.post("/extract")
def extract_link(req: LinkRequest):
    data = extractor.extract_data_from_link(req.url)
    return data
