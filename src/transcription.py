from faster_whisper import WhisperModel

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes the audio from a given path into raw text.

    Args:
        audio_path (str): The path to the audio file.

    Returns:
        str: The transcribed text.
    """
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

    return "\n".join([f"{s['start']:.2f}-{s['end']:.2f}: {s['text']}" for s in aggregated_segments])
