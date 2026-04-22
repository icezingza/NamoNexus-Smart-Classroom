import os
import logging
from google import genai
from google.genai import types
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GeminiModernReasoner:
    """
    GeminiModernReasoner - 2025 Edition
    ===================================
    Connects NamoNexus to the latest Gemini 2.0 Models using the brand-new google-genai SDK.
    """
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-flash-lite-latest"
        
    def generate_dhamma_answer(self, query: str, contexts: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        สร้างคำตอบธรรมะโดยอิงจาก Context และ System Prompt (Modern SDK)
        """
        # เตรียม Context String
        context_text = "\n\n".join([
            f"--- แหล่งที่มา: เล่ม {c.get('book')} ข้อ {c.get('item_id')} ---\n{c.get('content', c.get('text', ''))}"
            for c in contexts
        ])
        
        full_prompt = f"SYSTEM INSTRUCTION: {system_prompt}\n\nCONTEXT พระไตรปิฎก:\n{context_text}\n\nคำถาม: {query}"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"🔥 [Modern] Generation error: {e}")
            return f"ขออภัยครับน้องๆ พี่นะโม (เวอร์ชัน 2.0) ติดขัดนิดหน่อย: {e}"

if __name__ == "__main__":
    pass
