# สร้างโฟลเดอร์หลัก
New-Item -ItemType Directory -Force -Path "NamoNexus-Skills\docs"
New-Item -ItemType Directory -Force -Path "NamoNexus-Skills\config"
New-Item -ItemType Directory -Force -Path "NamoNexus-Skills\skills"
New-Item -ItemType Directory -Force -Path "NamoNexus-Skills\tests"

# KnowledgePack.pdf (placeholder)
Set-Content "NamoNexus-Skills\docs\KnowledgePack.pdf" "This is the Knowledge Pack PDF placeholder. รวมทุกเอกสาร Aesthetics, Dhamma, Code, Persona, System, Validation."

# Blueprint.yaml
Set-Content "NamoNexus-Skills\docs\Blueprint.yaml" @"
skills:
  - name: UX_Aesthetics_Designer
    sources: [Aesthetics_Design_Guide.txt, Aesthetics_Guide.md]
    purpose: ออกแบบ UI/UX Premium Dark Mode, Cyber-Zen
    validation: [UI ต้อง WOW, ห้ามใช้สีผิดมาตรฐาน]
  - name: Dhamma_Wisdom_Teacher
    sources: [Dhamma_Wisdom_Protocol.md, Dhamma_Wisdom_Protocol.txt]
    purpose: ตอบคำถามพระไตรปิฎกพร้อม Citation
    validation: [ห้าม Hallucinate, ต้องมี Citation]
"@

# skill_loader.json
Set-Content "NamoNexus-Skills\config\skill_loader.json" @"
{
  "skills": [
    {"name":"UX_Aesthetics_Designer","enabled":true,"sources":["docs/KnowledgePack.pdf"]},
    {"name":"Dhamma_Wisdom_Teacher","enabled":true,"sources":["docs/KnowledgePack.pdf"]}
  ],
  "settings": {
    "rag_engine":"FAISS",
    "vector_count":168000,
    "knowledge_pack":"docs/KnowledgePack.pdf",
    "blueprint":"docs/Blueprint.yaml"
  }
}
"@

# address.json
Set-Content "NamoNexus-Skills\config\address.json" @"
{
  "project_owner": "Kanin",
  "location": {
    "country": "Thailand",
    "province": "Phuket",
    "city": "Talat Yai",
    "timezone": "ICT"
  },
  "deployment": {
    "edge_device": "Lenovo Gaming 3",
    "cloud_provider": "GCP",
    "hybrid_stack": true
  }
}
"@

# README.md (พร้อม Workflow Diagram)
Set-Content "NamoNexus-Skills\docs\README.md" @"
# 📚 NamoNexus Knowledge Pack & Skill Loader

## 1. ภาพรวม
ชุดนี้ประกอบด้วย KnowledgePack.pdf, Blueprint.yaml, skill_loader.json, address.json

## 2. วิธีใช้งาน
1. โหลด KnowledgePack.pdf เข้า RAG Engine
2. โหลด Blueprint.yaml และ skill_loader.json เข้า Skill Loader
3. ใช้ address.json เป็น metadata
4. ตรวจสอบผลลัพธ์ด้วย Validation Gates

## 3. Workflow Diagram
```mermaid
flowchart TD
    A[KnowledgePack.pdf] --> B[RAG Engine (FAISS Index)]
    B --> C[Skill Loader (skill_loader.json)]
    C --> D[Blueprint.yaml]
    D --> E[AI Skill Modules]
    E --> F[Validation Gates]
    F --> G[Deploy to Classroom AI]

    subgraph AI Skill Modules
        UX[UX_Aesthetics_Designer]
        DW[Dhamma_Wisdom_Teacher]
        CA[Code_Architect]
        PM[Persona_Manager]
        SA[System_Architect]
        QG[Quality_Guardian]
    end
```
"@
Write-Host "✅ NamoNexus-Skills package created successfully!" -ForegroundColor Green
