"""
Streamlit Frontend
Interface de chat para o Sage's Oracle
"""

import streamlit as st
import requests
from typing import Dict, List
import json

# Configuração da página
st.set_page_config(
    page_title="Sage's Oracle - D&D 5e Assistant",
    page_icon="🧙‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL da API
API_URL = "http://localhost:8000"

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #8B0000;
        text-align: center;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .sub-header {
        text-align: center;
        color: #555;
        font-style: italic;
        margin-bottom: 2rem;
    }
    .source-card {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #8B0000;
        margin: 0.5rem 0;
    }
    .stChatMessage {
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🧙‍♂️ Sage\'s Oracle</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your AI Companion for D&D 5th Edition Rules</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://www.dndbeyond.com/avatars/thumbnails/6/359/420/618/636272680339895080.png", width=200)
    
    st.markdown("### ⚙️ Settings")
    
    # Configurações
    top_k = st.slider(
        "📚 Number of sources to use",
        min_value=1,
        max_value=10,
        value=5,
        help="How many documents to retrieve for context"
    )
    
    temperature = st.slider(
        "🌡️ Response creativity",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Lower = more focused, Higher = more creative"
    )
    
    st.markdown("---")
    
    # Status da API
    st.markdown("### 📊 API Status")
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=2)
        if health_response.status_code == 200:
            health_data = health_response.json()
            if health_data.get("status") == "ready":
                st.success("✅ API Online")
                st.metric("Chunks loaded", health_data.get("chunks_loaded", 0))
            else:
                st.warning("⚠️ API not ready")
                st.info(health_data.get("message", "Unknown status"))
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ API Offline")
        st.info("Make sure to run: `uvicorn backend.api.main:app --reload`")
    
    st.markdown("---")
    
    # Exemplos de perguntas
    st.markdown("### 💡 Example Questions")
    example_questions = [
        "What is the Fireball spell?",
        "How does the Grappled condition work?",
        "Tell me about the Tarrasque",
        "What is advantage on attack rolls?",
        "How do spell slots work?"
    ]
    
    for question in example_questions:
        if st.button(question, key=f"ex_{question}", use_container_width=True):
            st.session_state.example_question = question

# Inicializar histórico de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Greetings, adventurer! I am Sage, your guide to the rules of Dungeons & Dragons 5th Edition. Ask me anything about spells, monsters, rules, or game mechanics!"
        }
    ]

# Exibir histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Se for uma resposta do assistente com fontes, mostrar
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("📚 Sources used"):
                for source in message["sources"]:
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>{source['type'].upper()}</strong>: {source['name']}<br>
                        <small>Relevance: {source['relevance_score']:.2%}</small><br>
                        <a href="{source['url']}" target="_blank">View source →</a>
                    </div>
                    """, unsafe_allow_html=True)

# Input de pergunta
question = st.chat_input("Ask about D&D 5e rules, spells, or monsters...")

# Se clicou em exemplo, usar essa pergunta
if "example_question" in st.session_state:
    question = st.session_state.example_question
    del st.session_state.example_question

if question:
    # Adicionar pergunta ao histórico
    st.session_state.messages.append({"role": "user", "content": question})
    
    # Exibir pergunta
    with st.chat_message("user"):
        st.markdown(question)
    
    # Gerar resposta
    with st.chat_message("assistant"):
        with st.spinner("🔮 Consulting the ancient tomes..."):
            try:
                # Chamar API
                response = requests.post(
                    f"{API_URL}/ask",
                    json={
                        "question": question,
                        "top_k": top_k,
                        "temperature": temperature
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result["answer"]
                    sources = result["sources"]
                    
                    # Exibir resposta
                    st.markdown(answer)
                    
                    # Exibir fontes
                    with st.expander("📚 Sources used"):
                        for source in sources:
                            st.markdown(f"""
                            <div class="source-card">
                                <strong>{source['type'].upper()}</strong>: {source['name']}<br>
                                <small>Relevance: {source['relevance_score']:.2%}</small><br>
                                <a href="{source['url']}" target="_blank">View source →</a>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Salvar no histórico
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                
                elif response.status_code == 503:
                    error_msg = "⚠️ The knowledge base is not ready. Please run the ETL pipeline first:\n```bash\npython -m backend.etl.pipeline\n```"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                else:
                    error_msg = f"❌ Error: {response.status_code} - {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
            
            except requests.exceptions.ConnectionError:
                error_msg = "❌ Cannot connect to API. Make sure it's running:\n```bash\nuvicorn backend.api.main:app --reload\n```"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            
            except Exception as e:
                error_msg = f"❌ Unexpected error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>🎲 Powered by RAG (Retrieval-Augmented Generation) | Data from D&D 5e SRD</p>
    <p>Built with FastAPI, Sentence Transformers, and Streamlit</p>
</div>
""", unsafe_allow_html=True)