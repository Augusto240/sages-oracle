from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from pathlib import Path

from backend.core.rag_engine import RAGEngine

class QuestionRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    temperature: Optional[float] = 0.3


class Source(BaseModel):
    doc_id: int
    type: str
    name: str
    source: str
    url: str
    relevance_score: float


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Source]
    context_used: int


app = FastAPI(
    title="Sage's Oracle API",
    description="D&D 5e Rules Assistant powered by RAG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine: Optional[RAGEngine] = None


@app.on_event("startup")
async def startup_event():
    """Inicializa o RAG Engine no startup"""
    global rag_engine
        
    chunks_file = Path("data/processed/all_chunks.json")
    if not chunks_file.exists():
        print("⚠️  WARNING: ETL pipeline não foi executado!")
        print("   Execute: python -m backend.etl.pipeline")
        return
    
    print("🚀 Inicializando RAG Engine...")
    rag_engine = RAGEngine()
    print("✅ API pronta!")


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "Sage's Oracle API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Status detalhado"""
    if rag_engine is None:
        return {
            "status": "not_ready",
            "message": "RAG Engine not initialized. Run ETL pipeline first."
        }
    
    return {
        "status": "ready",
        "chunks_loaded": len(rag_engine.chunks),
        "embedding_model": "all-MiniLM-L6-v2",
        "llm_model": rag_engine.llm_model
    }


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Faz uma pergunta ao assistente
    
    - **question**: A pergunta sobre D&D 5e
    - **top_k**: Número de documentos para usar como contexto (padrão: 5)
    - **temperature**: Temperatura do LLM (0-1, padrão: 0.3)
    """
    if rag_engine is None:
        raise HTTPException(
            status_code=503,
            detail="RAG Engine not initialized. Run ETL pipeline first."
        )
    
    try:        
        retrieved_chunks = rag_engine.retrieve(request.question, request.top_k)
                
        result = rag_engine.generate_answer(
            request.question,
            retrieved_chunks,
            request.temperature
        )
        
        return QuestionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sources/{doc_type}")
async def list_sources(doc_type: str):
    """
    Lista todas as fontes de um tipo específico
    
    - **doc_type**: Tipo de documento (spell, monster, rule)
    """
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    
    filtered = [
        chunk['metadata']
        for chunk in rag_engine.chunks
        if chunk['metadata']['type'] == doc_type
    ]
    
    return {
        "type": doc_type,
        "count": len(filtered),
        "sources": filtered
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)