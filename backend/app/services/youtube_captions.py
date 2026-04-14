import logging

logger = logging.getLogger(__name__)

_MAX_CHARS = 2000


def fetch_transcript(youtube_id: str) -> str | None:
    """Fetch the first ~2000 chars of a YouTube video's captions.

    Uses the youtube-transcript-api library which scrapes the public
    captions endpoint — no API key required.  Returns None on any failure
    (disabled captions, network error, etc.).
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        logger.debug("youtube-transcript-api not installed — skipping transcripts")
        return None

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(youtube_id)
        parts: list[str] = []
        total = 0
        for entry in transcript:
            text = entry.text.strip()
            if not text:
                continue
            parts.append(text)
            total += len(text) + 1
            if total >= _MAX_CHARS:
                break
        if not parts:
            return None
        result = " ".join(parts)[:_MAX_CHARS]
        return result
    except Exception:
        logger.debug("Could not fetch transcript for %s", youtube_id)
        return None
