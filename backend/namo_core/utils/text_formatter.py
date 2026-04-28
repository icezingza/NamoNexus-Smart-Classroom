"""Text formatting utilities for transcript and diarization processing."""

def format_diarization(diarization_data: list) -> str:
    """
    Format diarization results into a structured string for LLM.
    Each item in diarization_data is expected to have 'speaker' and 'text'.
    """
    if not diarization_data:
        return ""
    
    formatted_parts = []
    for item in diarization_data:
        # Some diarization outputs might be tuples or dicts
        if isinstance(item, dict):
            speaker = item.get("speaker", "Unknown")
            text = item.get("text", "").strip()
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            speaker = item[0]
            text = str(item[1]).strip()
        else:
            continue
            
        if text:
            formatted_parts.append(f"{speaker}: {text}")
            
    return "\n".join(formatted_parts)
