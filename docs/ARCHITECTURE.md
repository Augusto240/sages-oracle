# 🏗️ Arquitetura Técnica - Sage's Oracle

## Visão Geral

Sage's Oracle é um assistente de IA para D&D 5e que utiliza a arquitetura **RAG (Retrieval-Augmented Generation)** para fornecer respostas precisas e fundamentadas sobre regras, magias e monstros.

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                  │
│  - Interface de chat                                     │
│  - Exibição de fontes                                   │
│  - Configurações (top_k, temperature)                   │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP/REST
                 ▼
┌─────────────────────────────────────────────────────────┐
│              API BACKEND (FastAPI)                       │
│  Endpoints:                                              │
│  - POST /ask         → Faz pergunta                     │
│  - GET  /health      → Status da API                    │
│  - GET  /sources/:type → Lista fontes                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                  RAG ENGINE (Core)                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Query Embedding                               │  │
│  │     - Transforma pergunta em vetor                │  │
│  │                                                   │  │
│  │  2. Retrieval (Busca Semântica)                   │  │
│  │     - Similaridade coseno                         │  │
│  │     - Top-K chunks mais relevantes                │  │
│  │                                                   │  │
│  │  3. Context Building                              │  │
│  │     - Monta prompt com documentos recuperados     │  │
│  │                                                   │  │
│  │  4. LLM Generation                                │  │
│  │     - Chama Ollama (Phi-3 Mini)                   │  │
│  │     - Prompt engineering com guardrails           │  │
│  │                                                   │  │
│  │  5. Response + Source Citation                    │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
┌─────────────┐      ┌──────────────┐
│  Embeddings │      │    Chunks    │
│   (.npy)    │      │    (.json)   │
│             │      │              │
│ - 384 dims  │      │ - Text       │
│ - NumPy     │      │ - Metadata   │
│             │      │ - Tokens     │
└─────────────┘      └──────────────┘
      ▲                     ▲
      │                     │
      └─────────────────────┘
              │
              ▼
    ┌──────────────────┐
    │   ETL Pipeline   │
    │                  │
    │ 1. Scraper       │
    │ 2. Chunker       │
    │ 3. Embedder      │
    └──────────────────┘
              ▲
              │
    ┌──────────────────┐
    │  Data Sources    │
    │                  │
    │ - D&D 5e API     │
    │ - SRD Content    │
    └──────────────────┘
```

## Stack Tecnológica

### Backend
- **FastAPI**: Framework web moderno, async, com validação automática
- **Pydantic**: Validação de dados e modelos
- **Uvicorn**: ASGI server

### IA & ML
- **Sentence Transformers**: Geração de embeddings semânticos
  - Modelo: `all-MiniLM-L6-v2` (384 dimensões, 80MB)
- **Ollama**: Servidor local de LLMs
  - Modelo: `phi3:mini` (3.8B parâmetros, ~2.3GB)
- **NumPy**: Operações vetoriais e similaridade coseno

### ETL
- **Requests**: HTTP client para scraping de APIs
- **tqdm**: Progress bars
- **tiktoken**: Tokenização para contagem

### Frontend
- **Streamlit**: Framework para apps de dados/ML

## Decisões Arquiteturais

### 1. Por que Embeddings Locais?

**Decisão**: Usar `all-MiniLM-L6-v2` localmente ao invés de APIs externas (OpenAI, Cohere).

**Motivo**:
- ✅ Sem custo de API
- ✅ Sem latência de rede
- ✅ Privacidade total
- ✅ Funciona offline
- ⚠️ Trade-off: Qualidade um pouco menor que modelos gigantes

### 2. Por que Phi-3 Mini?

**Decisão**: Usar Phi-3 Mini (3.8B) via Ollama ao invés de GPT-4 ou modelos maiores.

**Motivo**:
- ✅ Roda em hardware modesto (RTX 3050, 8GB VRAM)
- ✅ Rápido para inferência
- ✅ Qualidade excelente para o tamanho
- ✅ Sem custos de API
- ⚠️ Trade-off: Menos "criativo" que modelos de 70B+, mas perfeito para Q&A factual

### 3. Estratégia de Chunking

**Decisão**: Chunking diferenciado por tipo de conteúdo.

| Tipo | Estratégia | Max Tokens | Overlap | Motivo |
|------|-----------|-----------|---------|--------|
| **Spells** | Entity-based | 300 | 0 | Magias são auto-contidas |
| **Monsters** | Entity-based | 400 | 0 | Stat blocks completos |
| **Rules** | Section-based | 512 | 50 | Regras precisam de contexto |

**Por quê?**
- Chunks muito pequenos perdem contexto
- Chunks muito grandes prejudicam a precisão do retrieval
- Overlap em regras evita cortar conceitos ao meio

### 4. Busca Puramente Vetorial (vs. Híbrida)

**Decisão Atual**: Busca vetorial com similaridade coseno.

**Possível Melhoria Futura**: Implementar busca híbrida (vetorial + BM25).

**Trade-off**:
- ✅ Simples de implementar
- ✅ Funciona bem para perguntas semânticas
- ⚠️ Pode falhar em buscas por nome exato (ex: "Fireball" vs "Fire Ball")

### 5. Prompt Engineering

**Decisão**: Prompt com guardrails explícitos.

```python
Guardrails implementados:
1. "Use ONLY the provided documents"
2. "If not in documents, say you don't know"
3. "Cite document numbers"
4. "Be concise but complete"
```

**Por quê?**
- Previne alucinações
- Força rastreabilidade (citações)
- Mantém respostas fundamentadas

## Métricas de Performance

### Tamanho dos Dados

| Componente | Tamanho | Quantidade |
|-----------|---------|-----------|
| Raw JSON | ~5MB | 5 arquivos |
| Processed Chunks | ~3MB | 600-800 chunks |
| Embeddings | ~2MB | 600-800 × 384 dims |
| **Total** | **~10MB** | - |

### Tempo de Processamento (ETL)

| Etapa | Tempo (estimado) |
|-------|-----------------|
| Scraping | ~2-3 minutos |
| Chunking | ~10 segundos |
| Embeddings | ~30 segundos |
| **Total** | **~3-4 minutos** |

### Latência (Query)

| Etapa | Tempo |
|-------|-------|
| Embedding da query | ~50ms |
| Retrieval (top-5) | ~20ms |
| LLM Generation | ~2-5s (dependendo do comprimento) |
| **Total** | **~2-5s** |

## Escalabilidade

### Limitações Atuais

- **Busca Linear**: O(n) para busca em ~800 chunks (aceitável para essa escala)
- **Single-threaded**: Sem paralelização
- **In-memory**: Tudo em RAM

### Como Escalar (Futuro)

1. **Para 10K+ chunks**:
   - Migrar para FAISS com índice IVF
   - Ou usar Milvus/Qdrant

2. **Para múltiplos usuários**:
   - Adicionar Redis para cache
   - Load balancer para múltiplas instâncias da API

3. **Para LLMs maiores**:
   - Usar GPU remota (RunPod, Together.ai)
   - Ou quantização INT8/INT4

## Segurança

### Implementado

- ✅ CORS configurado
- ✅ Guardrails no prompt (anti-alucinação)
- ✅ Timeout nas requisições

### A Implementar (Produção)

- [ ] Rate limiting
- [ ] API Keys
- [ ] Input sanitization
- [ ] Logging de queries

## Testes

### Casos de Teste Recomendados

1. **Retrieval Accuracy**
   - Query: "Fireball"
   - Esperado: Chunk da magia Fireball no top-1

2. **Out-of-scope**
   - Query: "How to cook pasta?"
   - Esperado: "I don't have that information..."

3. **Multi-hop**
   - Query: "What spells can a 5th level wizard cast?"
   - Esperado: Combinar info de wizard + spell slots

## Referências

- [D&D 5e API](https://www.dnd5eapi.co/)
- [Sentence Transformers](https://www.sbert.net/)
- [Ollama](https://ollama.ai/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)

