import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import requests


class RAGEngine:
    """Engine principal do RAG"""
    
    def __init__(
        self,
        chunks_file: str = "data/processed/all_chunks.json",
        embeddings_file: str = "data/embeddings/embeddings.npy",
        metadata_file: str = "data/embeddings/metadata.json",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_url: str = "http://localhost:11434/api/generate",
        llm_model: str = "phi3:mini"
    ):
        self.chunks_file = Path(chunks_file)
        self.embeddings_file = Path(embeddings_file)
        self.metadata_file = Path(metadata_file)
        
        self.llm_url = llm_url
        self.llm_model = llm_model
                
        print("📚 Carregando base de conhecimento...")
        self.chunks = self._load_chunks()
        self.embeddings = self._load_embeddings()
        self.metadata = self._load_metadata()
                
        print(f"🤖 Carregando modelo de embeddings...")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        print(f"✅ RAG Engine inicializada!")
        print(f"   📊 {len(self.chunks)} chunks carregados")
        print(f"   🧮 Embeddings shape: {self.embeddings.shape}")
    
    def _load_chunks(self) -> List[Dict]:
        """Carrega chunks processados"""
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_embeddings(self) -> np.ndarray:
        """Carrega embeddings"""
        return np.load(self.embeddings_file)
    
    def _load_metadata(self) -> List[Dict]:
        """Carrega metadata"""
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Busca semântica: encontra os chunks mais relevantes
        
        Args:
            query: Pergunta do usuário
            top_k: Número de chunks para retornar
            
        Returns:
            Lista de (chunk, score de similaridade)
        """        
        query_embedding = self.embedding_model.encode([query])[0]
                
        similarities = np.dot(self.embeddings, query_embedding)
                
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            score = float(similarities[idx])
            results.append((chunk, score))
        
        return results
    
    def generate_answer(
        self,
        query: str,
        context_chunks: List[Tuple[Dict, float]],
        temperature: float = 0.3
    ) -> Dict:
        """
        Gera resposta usando LLM com contexto recuperado
        
        Args:
            query: Pergunta do usuário
            context_chunks: Chunks recuperados com scores
            temperature: Temperatura do LLM (0-1, menor = mais determinístico)
        """        
        context_parts = []
        sources = []
        
        for i, (chunk, score) in enumerate(context_chunks, 1):
            context_parts.append(f"[Documento {i}]")
            context_parts.append(chunk['text'])
            context_parts.append("")
                        
            metadata = chunk['metadata']
            source = {
                'doc_id': i,
                'type': metadata['type'],
                'name': metadata.get('name', 'Unknown'),
                'source': metadata['source'],
                'url': metadata.get('url', ''),
                'relevance_score': round(score, 3)
            }
            sources.append(source)
        
        context = "\n".join(context_parts)
                
        prompt = self._build_prompt(query, context)
            
        answer = self._call_llm(prompt, temperature)
        
        return {
            'answer': answer,
            'sources': sources,
            'context_used': len(context_chunks)
        }
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Constrói o prompt para o LLM"""
        return f"""You are Sage, a knowledgeable assistant for Dungeons & Dragons 5th Edition rules.

Your role is to answer questions about D&D rules, spells, and monsters using ONLY the information provided in the documents below.

IMPORTANT RULES:
1. Base your answer STRICTLY on the provided documents
2. If the answer is not in the documents, say "I don't have that information in my current knowledge base"
3. Cite document numbers when making specific claims (e.g., "According to Document 1...")
4. Be concise but complete
5. Use clear, accessible language

DOCUMENTS:
{context}

QUESTION: {query}

ANSWER:"""
    
    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """
        Chama o LLM (Ollama) para gerar resposta
        
        Args:
            prompt: Prompt completo
            temperature: Temperatura (0-1)
        """
        try:
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 500
                }
            }
            
            response = requests.post(self.llm_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
        
        except requests.exceptions.RequestException as e:
            return f"Error calling LLM: {str(e)}"
    
    def ask(self, query: str, top_k: int = 5) -> Dict:
        """
        Método principal: faz pergunta e retorna resposta completa
        
        Args:
            query: Pergunta do usuário
            top_k: Número de documentos para usar como contexto
        """
        print(f"\n❓ Pergunta: {query}")
                
        print(f"🔍 Buscando {top_k} documentos relevantes...")
        retrieved_chunks = self.retrieve(query, top_k)
            
        print(f"🤖 Gerando resposta com {self.llm_model}...")
        result = self.generate_answer(query, retrieved_chunks)
        
        print(f"✅ Resposta gerada!")
        return result


def main():
    """Teste do RAG Engine"""    
    rag = RAGEngine()
    
    query = "What is the spell Fireball?"
    result = rag.ask(query)
    
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(f"\n📝 Resposta:\n{result['answer']}")
    print(f"\n📚 Fontes usadas:")
    for source in result['sources']:
        print(f"   - {source['name']} (relevância: {source['relevance_score']})")


if __name__ == "__main__":
    main()