# NamoNexus Gold Standard Code Library

Use these snippets as the reference standard for all code generation and refactoring in the NamoNexus project.

## 1. Backend: Async FastAPI Endpoint
```python
from fastapi import APIRouter, Depends, HTTPException
from namo_core.core.orchestrator import NamoOrchestrator
from namo_core.config.deps import get_orchestrator
from pydantic import BaseModel

router = APIRouter(prefix="/notebook", tags=["notebook"])

class NotebookRequest(BaseModel):
    query: str
    top_k: int = 3

@router.post("/generate")
async def generate_wisdom(
    req: NotebookRequest,
    orchestrator: NamoOrchestrator = Depends(get_orchestrator)
):
    """Sovereign standard: 100% Async, explicit dependency injection."""
    try:
        # Avoid blocking the event loop
        result = await orchestrator.reasoner.generate_async(
            query=req.query,
            context=await orchestrator.knowledge.search_async(req.query, req.top_k)
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 2. Frontend: Premium React Component
```tsx
import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils'; // standard utility for classes

interface PremiumCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export const PremiumCard: React.FC<PremiumCardProps> = ({ title, children, className }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "glass p-6 rounded-[2.5rem] border border-white/10 glow-indigo transition-all hover:border-indigo-500/30",
        className
      )}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 bg-indigo-500/10 rounded-xl">
          <Sparkles className="w-4 h-4 text-indigo-400" />
        </div>
        <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500">
          {title}
        </h4>
      </div>
      <div className="text-slate-200 leading-relaxed">
        {children}
      </div>
    </motion.div>
  );
};
```

## 3. Real-time: useNamoSocket Usage
```tsx
const { data, status, connect } = useNamoSocket(wsUrl);

useEffect(() => {
  if (status === 'idle') connect();
}, [status, connect]);

// Event handling
useEffect(() => {
  if (data?.transcript?.speaker === 'namo') {
    console.log("Namo is speaking:", data.transcript.text);
  }
}, [data]);
```
