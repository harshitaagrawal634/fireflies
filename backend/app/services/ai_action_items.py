
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()


class ExtractedActionItem(BaseModel):
    description: str = Field(min_length=1)
    assignee: str | None = None


class ExtractedActionItems(BaseModel):
    items: list[ExtractedActionItem]


def extract_action_items(transcript: str) -> list[ExtractedActionItem]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing")

    client = genai.Client(api_key=api_key)

    prompt = f"""
Extract action items from the meeting transcript.

Rules:
1. Extract only actual tasks or commitments.
2. Include the responsible person's name if mentioned.
3. If no assignee is mentioned, use null.
4. Include any stated deadline in the description.
5. Do not invent tasks or people.
6. If no action items exist, return an empty items list.

Transcript:
{transcript}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedActionItems
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    result = ExtractedActionItems.model_validate_json(response.text)

    return result.items
