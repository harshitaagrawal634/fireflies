
from app.services.vtt_parser import parse_vtt

sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
<v Alice>We need to finish the project.

00:00:05.000 --> 00:00:08.000
<v Bob>I will complete the backend.
"""

segments = parse_vtt(sample_vtt)

for segment in segments:
    print(segment)
