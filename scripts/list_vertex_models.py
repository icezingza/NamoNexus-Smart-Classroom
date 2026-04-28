import os
import vertexai
from vertexai.generative_models import GenerativeModel

def list_my_models():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "namo-classroom-58e4be305633.json"
    project_id = "namo-classroom"
    location = "us-central1"
    
    vertexai.init(project=project_id, location=location)
    
    print(f"--- Models available in {project_id} ({location}) ---")
    # ใน SDK ใหม่ เราสามารถลองเรียกใช้รุ่นพื้นฐานเพื่อเช็คผล
    try:
        model = GenerativeModel("gemini-1.5-flash-001")
        response = model.generate_content("Hi")
        print("✅ gemini-1.5-flash-001: OK")
    except Exception as e:
        print(f"❌ gemini-1.5-flash-001: {e}")

    try:
        model = GenerativeModel("gemini-1.0-pro-002")
        response = model.generate_content("Hi")
        print("✅ gemini-1.0-pro-002: OK")
    except Exception as e:
        print(f"❌ gemini-1.0-pro-002: {e}")

if __name__ == "__main__":
    list_my_models()
