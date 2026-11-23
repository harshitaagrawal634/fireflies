
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")


def generate_meeting_summary(transcript: str) -> str:
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is missing")

    client = genai.Client(api_key=API_KEY)

    prompt = f"""
You are an assistant that summarizes meeting transcripts.

Generate a clear, concise summary of the meeting.

Include:
1. Main discussion points
2. Important decisions
3. Action items and responsible people, if mentioned

Do not invent information.

Meeting transcript:
{transcript}
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            break

        except ServerError as e:
            if e.code != 503 or attempt == 2:
                raise

            print(f"Gemini busy. Retrying {attempt + 2}/3...")
            time.sleep(2 ** attempt)

    if not response.text:
        raise ValueError("AI returned an empty summary")

    return response.text
