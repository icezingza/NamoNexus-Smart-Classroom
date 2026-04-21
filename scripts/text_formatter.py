"""
text_formatter.py - Shared text formatting utilities
"""

from __future__ import annotations


def format_diarization(diarization_result: list[dict]) -> str | None:
    """Formats a diarization result list into a speaker-tagged string.

    Args:
        diarization_result: A list of diarization items, each with 'speaker_tag' and 'word'.

    Returns:
        A formatted string with speaker tags, or None if the input is empty.
    """
    if not diarization_result:
        return None

    speaker_blocks = []
    current_speaker = None
    current_words = []
    for item in diarization_result:
        spk = item.get("speaker_tag")
        word = item.get("word", "")
        if spk != current_speaker:
            if current_speaker is not None:
                speaker_blocks.append(
                    f"[ผู้พูดที่ {current_speaker}]: {''.join(current_words).strip()}"
                )
            current_speaker = spk
            current_words = [word]
        else:
            current_words.append(word)
    if current_speaker is not None:
        speaker_blocks.append(
            f"[ผู้พูดที่ {current_speaker}]: {''.join(current_words).strip()}"
        )

    formatted_text = "\n".join(speaker_blocks)
    formatted_text += (
        "\n\n(System Note: วิเคราะห์บริบทแยกแยะครูกับนักเรียนจากบทสนทนานี้และให้คำตอบที่เหมาะสม)"
    )
    return formatted_text
