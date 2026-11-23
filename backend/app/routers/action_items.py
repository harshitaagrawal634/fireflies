from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.transcript import TranscriptSegment
from app.services.ai_action_items import extract_action_items

from app.database import get_db
from app.models.action_item import ActionItem
from app.models.meeting import Meeting
from app.schemas.action_item import (
    ActionItemCreate,
    ActionItemResponse,
    ActionItemUpdate,
)

router = APIRouter(tags=["Action Items"])


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
    "/api/meetings/{meeting_id}/action-items",
    response_model=list[ActionItemResponse]
)
def get_action_items(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    get_meeting_or_404(meeting_id, db)

    return (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id == meeting_id)
        .order_by(ActionItem.id.asc())
        .all()
    )


@router.post(
    "/api/meetings/{meeting_id}/action-items",
    response_model=ActionItemResponse,
    status_code=201
)
def create_action_item(
    meeting_id: int,
    data: ActionItemCreate,
    db: Session = Depends(get_db)
):
    get_meeting_or_404(meeting_id, db)

    item = ActionItem(
        meeting_id=meeting_id,
        description=data.description,
        assignee=data.assignee
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.patch(
    "/api/action-items/{item_id}",
    response_model=ActionItemResponse
)
def update_action_item(
    item_id: int,
    data: ActionItemUpdate,
    db: Session = Depends(get_db)
):
    item = (
        db.query(ActionItem)
        .filter(ActionItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Action item not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return item


@router.delete(
    "/api/action-items/{item_id}",
    status_code=204
)
def delete_action_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    item = (
        db.query(ActionItem)
        .filter(ActionItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Action item not found"
        )

    db.delete(item)
    db.commit()


@router.post(
    "/api/meetings/{meeting_id}/action-items/extract",
    response_model=list[ActionItemResponse]
)
def generate_action_items(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    # 1. Verify the meeting exists
    get_meeting_or_404(meeting_id, db)

    # 2. Fetch its transcript
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

    # 3. Prepare transcript for Gemini
    transcript = "\n".join(
        f"{segment.speaker}: {segment.text}"
        for segment in segments
    )

    # 4. Extract structured action items
    extracted_items = extract_action_items(transcript)

    # 5. Fetch existing tasks to prevent duplicates
    existing_items = (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id == meeting_id)
        .all()
    )

    existing_keys = {
        (
            item.description.strip().casefold(),
            (item.assignee or "").strip().casefold()
        )
        for item in existing_items
    }

    # 6. Save only new tasks
    created = []

    for data in extracted_items:
        key = (
            data.description.strip().casefold(),
            (data.assignee or "").strip().casefold()
        )

        if key in existing_keys:
            continue

        item = ActionItem(
            meeting_id=meeting_id,
            description=data.description.strip(),
            assignee=data.assignee,
            completed=False
        )

        db.add(item)
        created.append(item)
        existing_keys.add(key)

    db.commit()

    for item in created:
        db.refresh(item)

    return created
