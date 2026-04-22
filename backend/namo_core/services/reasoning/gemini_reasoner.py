import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, Content, FinishReason
    import vertexai.preview.generative_models as generative_models
except ImportError:
    # จะทำการติดตั้งใน turn ถัดไปถ้าหายไป
    pass

logger = logging.getLogger(__name__)

class GeminiReasoner:
    """
    GeminiReasoner - Phase 12 Cloud-Enhanced Brain
    ============================================
    Connects NamoNexus to Google Cloud Vertex AI (Gemini 1.5 Pro).
    Uses the "Dhamma Prompt" designed by Namo 2.
    """
    
    def __init__(self, project_id: str, location: str = "asia-southeast1"):
        self.project_id = project_id
        self.location = location
        self.model_name = "gemini-1.5-pro-002"
        self._initialized = False
        self.model = None

    def _initialize(self):
        if not self._initialized:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                self.model = GenerativeModel(self.model_name)
                self._initialized = True
                logger.info(f"🚀 [Gemini] Connected to {self.model_name} at {self.location}")
            except Exception as e:
                logger.error(f"❌ [Gemini] Connection failed: {e}")
                raise

    def generate_dhamma_answer(self, query: str, contexts: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        สร้างคำตอบธรรมะโดยอิงจาก Context และ System Prompt
        """
        # สร้าง Model ใหม่พร้อม System Instruction เสมอเพื่อให้ Prompt อัปเดตตามที่ส่งมา
        vertexai.init(project=self.project_id, location=self.location)
        model = GenerativeModel(
            self.model_name,
            system_instruction=[system_prompt]
        )
        
        # เตรียม Context String
        context_text = "\n\n".join([
            f"--- แหล่งที่มา: เล่ม {c.get('book')} ข้อ {c.get('item_id')} ---\n{c.get('content', c.get('text', ''))}"
            for c in contexts
        ])
        
        full_prompt = f"""
CONTEXT จากพระไตรปิฎก:
{context_text}

คำถามจากเด็กๆ:
{query}
        """

        generation_config = {
            "max_output_tokens": 2048,
            "temperature": 0.2, 
            "top_p": 0.95,
        }

        safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        try:
            responses = model.generate_content(
                [full_prompt],
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )
            return responses.text
        except Exception as e:
            logger.error(f"🔥 [Gemini] Generation error: {e}")
            return "ขออภัยครับน้องๆ ตอนนี้พี่นะโมกำลังเข้าฌาน (ประมวลผล) ลึกเกินไปหน่อย รบกวนถามใหม่อีกครั้งนะ"

if __name__ == "__main__":
    # ทดสอบเบื้องต้น (ถ้ามีคีย์)
    pass
