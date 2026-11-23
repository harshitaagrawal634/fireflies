
from app.services.ai_summary import generate_meeting_summary

transcript = """
Alice: We need to finalize the E-Cell event plan.
Bob: I will complete the registration form by Friday.
Alice: We also need to confirm the venue.
Charlie: I will coordinate with the administration.
"""

summary = generate_meeting_summary(transcript)

print("\nGENERATED SUMMARY:\n")
print(summary)
