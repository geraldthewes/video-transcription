import os
import logging
from faster_whisper import WhisperModel

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes the audio from a given path into raw text.

    Args:
        audio_path (str): The path to the audio file.

    Returns:
        str: The transcribed text.
    """
    if log_level == "DEBUG":
        logger.debug(f"DEBUG: Starting transcription for file: {audio_path}")
        logger.debug(f"DEBUG: File size: {os.path.getsize(audio_path)} bytes")
    
    model = WhisperModel("base")
    segments, _ = model.transcribe(audio_path)
    
    aggregated_segments = []
    current_segment = None

    for segment in segments:
        if current_segment is None:
            current_segment = {"start": segment.start, "end": segment.end, "text": segment.text}
        elif segment.text == current_segment["text"]:
            current_segment["end"] = segment.end
        else:
            aggregated_segments.append(current_segment)
            current_segment = {"start": segment.start, "end": segment.end, "text": segment.text}

    if current_segment is not None:
        aggregated_segments.append(current_segment)

    result = "\n".join([f"{s['start']:.2f}-{s['end']:.2f}: {s['text']}" for s in aggregated_segments])
    
    if log_level == "DEBUG":
        logger.debug(f"DEBUG: Transcription completed. Result length: {len(result)} characters")
    
    return result
