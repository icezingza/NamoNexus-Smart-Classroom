import os
import logging
import google.generativeai as genai
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GeminiStudioReasoner:
    """
    GeminiStudioReasoner - AI Studio Edition (Phase 12+)
    ==================================================
    Connects NamoNexus to Google AI Studio (Gemini 1.5 Pro) using API Key.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model_name = "gemini-1.5-flash"
        
    def generate_dhamma_answer(self, query: str, contexts: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        สร้างคำตอบธรรมะโดยอิงจาก Context และ System Prompt (AI Studio API)
        """
        # เตรียม Context String
        context_text = "\n\n".join([
            f"--- แหล่งที่มา: เล่ม {c.get('book')} ข้อ {c.get('item_id')} ---\n{c.get('content', c.get('text', ''))}"
            for c in contexts
        ])
        
        # ตั้งค่าโมเดลพร้อม System Instruction
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt
        )

        full_prompt = f"CONTEXT พระไตรปิฎก:\n{context_text}\n\nคำถาม: {query}"

        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 4096,
        }

        try:
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"🔥 [Studio] Generation error: {e}")
            return f"ขออภัยครับน้องๆ พี่นะโมติดขัดนิดหน่อย: {e}"

if __name__ == "__main__":
    pass
