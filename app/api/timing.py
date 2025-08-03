# app/api/timing.py
from fastapi import APIRouter, UploadFile, File
from app.detection.multi_detector import process_video_with_timing
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/timing")
async def run_timing_test(file: UploadFile = File(...)):
    contents = await file.read()
    result = process_video_with_timing(contents)
    return JSONResponse(content=result)
