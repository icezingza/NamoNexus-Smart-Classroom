# 📚 NamoNexus Knowledge Pack & Skill Loader

## 1. ภาพรวม
ชุดนี้ประกอบด้วย KnowledgePack.pdf, Blueprint.yaml, skill_loader.json, address.json

## 2. วิธีใช้งาน
1. โหลด KnowledgePack.pdf เข้า RAG Engine
2. โหลด Blueprint.yaml และ skill_loader.json เข้า Skill Loader
3. ใช้ address.json เป็น metadata
4. ตรวจสอบผลลัพธ์ด้วย Validation Gates

## 3. Workflow Diagram
`mermaid
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
`
