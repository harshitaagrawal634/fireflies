from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.services.ai_summary import generate_meeting_summary

from app.database import get_db
from app.models.meeting import Meeting
from app.models.transcript import TranscriptSegment
from app.schemas.transcript import (
    TranscriptSegmentCreate,
    TranscriptSegmentResponse,
)
from app.services.vtt_parser import parse_vtt

router = APIRouter(
    prefix="/api/meetings",
    tags=["Transcripts"]
)


def get_meeting_or_404(meeting_id: int, db: Session):
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id)
        .first()
    )

    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="Meeting not found"
        )

    return meeting


@router.get(
    "/{meeting_id}/transcript",
    response_model=list[TranscriptSegmentResponse]
)
def get_transcript(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    get_meeting_or_404(meeting_id, db)

    return (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.segment_order.asc())
        .all()
    )


@router.post(
    "/{meeting_id}/transcript",
    response_model=list[TranscriptSegmentResponse],
    status_code=201
)
def add_transcript(
    meeting_id: int,
    segments: list[TranscriptSegmentCreate],
    db: Session = Depends(get_db)
):
    get_meeting_or_404(meeting_id, db)

    created = []

    for data in segments:
        segment = TranscriptSegment(
            meeting_id=meeting_id,
            speaker=data.speaker,
            start_time=data.start_time,
            end_time=data.end_time,
            text=data.text,
            segment_order=data.segment_order
        )

        db.add(segment)
        created.append(segment)

    db.commit()

    for segment in created:
        db.refresh(segment)

    return created


@router.get(
    "/{meeting_id}/transcript/search",
    response_model=list[TranscriptSegmentResponse]
)
def search_transcript(
    meeting_id: int,
    q: str = Query(min_length=1),
    db: Session = Depends(get_db)
):
    get_meeting_or_404(meeting_id, db)

    return (
        db.query(TranscriptSegment)
        .filter(
            TranscriptSegment.meeting_id == meeting_id,
            TranscriptSegment.text.ilike(f"%{q}%")
        )
        .order_by(TranscriptSegment.segment_order.asc())
        .all()
    )


@router.post(
    "/{meeting_id}/transcript/upload",
    response_model=list[TranscriptSegmentResponse],
    status_code=201
)
async def upload_vtt(
    meeting_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    get_meeting_or_404(meeting_id, db)

    if not file.filename or not file.filename.lower().endswith(".vtt"):
        raise HTTPException(400, "Please upload a .vtt file")

    content = await file.read(2_000_001)

    if len(content) > 2_000_000:
        raise HTTPException(413, "File exceeds 2 MB")

    try:
        segments = parse_vtt(content.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise HTTPException(400, "Invalid VTT content")

    if not segments:
        raise HTTPException(400, "No transcript segments found")

    created = []

    for data in segments:
        segment = TranscriptSegment(
            meeting_id=meeting_id,
            **data
        )
        db.add(segment)
        created.append(segment)

    db.commit()

    for segment in created:
        db.refresh(segment)

    return created


@router.post("/{meeting_id}/generate-summary")
def generate_summary(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    # Step 1: Check whether the meeting exists
    meeting = get_meeting_or_404(meeting_id, db)

    # Step 2: Fetch transcript segments
    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.segment_order.asc())
        .all()
    )

    if not segments:
        raise HTTPException(
            status_code=400,
            detail="No transcript found for this meeting"
        )

    # Step 3: Combine segments into a single transcript
    transcript = "\n".join(
        f"{segment.speaker}: {segment.text}"
        for segment in segments
    )

    # Step 4: Generate summary using Gemini
    summary = generate_meeting_summary(transcript)

    # Step 5: Save the summary in the database
    meeting.summary = summary
    db.commit()
    db.refresh(meeting)

    # Step 6: Return the generated summary
    return {
        "meeting_id": meeting.id,
        "summary": meeting.summary
    }
