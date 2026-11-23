
import re


def to_seconds(timestamp):
    parts = timestamp.replace(",", ".").split(":")
    seconds = 0

    for part in parts:
        seconds = seconds * 60 + float(part)

    return seconds


def parse_vtt(content):
    segments = []

    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().splitlines()

        if not lines or lines[0].strip() == "WEBVTT":
            continue

        time_index = next(
            (i for i, line in enumerate(lines) if "-->" in line),
            None
        )

        if time_index is None:
            continue

        start, end = lines[time_index].split("-->", 1)

        start_time = to_seconds(start.strip())
        end_time = to_seconds(end.strip().split()[0])

        if end_time <= start_time:
            continue

        dialogue = " ".join(lines[time_index + 1:]).strip()

        if not dialogue:
            continue

        voice = re.match(r"<v\s+([^>]+)>(.*)", dialogue)

        if voice:
            speaker = voice.group(1).strip()
            text = voice.group(2)
        elif ":" in dialogue:
            speaker, text = dialogue.split(":", 1)
        else:
            speaker, text = "Unknown", dialogue

        text = re.sub(r"<[^>]+>", "", text).strip()

        segments.append({
            "speaker": speaker.strip(),
            "start_time": start_time,
            "end_time": end_time,
            "text": text,
            "segment_order": len(segments) + 1
        })

    return segments
