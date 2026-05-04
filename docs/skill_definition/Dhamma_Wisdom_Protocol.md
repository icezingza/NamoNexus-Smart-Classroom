# NamoNexus Dhamma Wisdom Protocol

This document defines how the system should handle, process, and present sacred Dhamma data from the Tripitaka.

## 1. Respect for Source Data
- **Sanctity**: Treat the Tripitaka data with the highest respect. Never use it for trivial or inappropriate generation.
- **Accuracy**: prioritize exact quotes where possible. If summarizing, ensure the essence of the Dhamma is preserved without distortion.

## 2. Citation Standards
All output generated from the knowledge base must include source citations in the following formats:
- **Primary**: `[พระไตรปิฎก เล่มที่ X ข้อที่ Y]`
- **Secondary**: `(จาก: ชื่อคัมภีร์/อรรถกถา)`
- **Digital Reference**: Link to `84000.org` or `learntripitaka.com` if available in metadata.

## 3. "Saturate Wisdom" Pipeline Goal
The goal is to transform 168,861 vectors of raw wisdom into:
1. **Teaching Briefs**: Summaries for teachers to prepare lessons.
2. **Student FAQ**: Answering complex questions with scriptural backing.
3. **Audio Scripts**: Converting Dhamma dialogues into engaging classroom scripts.
4. **Flashcards**: Key concepts (e.g., Five Precepts, Four Noble Truths) for student review.

## 4. Context Injection Rules
- Always prepend the `teaching_hint` (from the EmpathyEngine) to the RAG context.
- Ensure the AI understands the "Student State" (e.g., bored, engaged, confused) to adapt the tone of the Dhamma explanation.

## 5. Source Hierarchy
1. **Pali Canon (Tipitaka)**: Highest authority.
2. **Commentaries (Atthakatha)**: Explanatory context.
3. **Sub-commentaries (Tika)**: Technical details.
4. **Dhamma Talks**: Modern applications.
