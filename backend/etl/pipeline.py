import json
from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from backend.etl.scrapers.srd_scraper import SRDScraper
from backend.utils.chunking import TextChunker

class ETLPipeline:    
    
    def __init__(
        self,
        raw_data_dir: str = "data/raw",
        processed_data_dir: str = "data/processed",
        embeddings_dir: str = "data/embeddings"
    ):
        self.raw_data_dir = Path(raw_data_dir)
        self.processed_data_dir = Path(processed_data_dir)
        self.embeddings_dir = Path(embeddings_dir)
                
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
                
        self.scraper = SRDScraper(output_dir=str(self.raw_data_dir))
        self.chunker = TextChunker()
        self.embedding_model = None
    
    def load_embedding_model(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Carrega modelo de embeddings"""
        print(f"📥 Carregando modelo de embeddings: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        print(f"✅ Modelo carregado! Dimensão: {self.embedding_model.get_sentence_embedding_dimension()}")
    
    def step_1_scrape_data(self):
        """Etapa 1: Coleta de dados"""
        print("\n" + "="*60)
        print("ETAPA 1: COLETA DE DADOS")
        print("="*60)
        
        self.scraper.scrape_all()
    
    def step_2_process_and_chunk(self):
        """Etapa 2: Processamento e chunking"""
        print("\n" + "="*60)
        print("ETAPA 2: PROCESSAMENTO E CHUNKING")
        print("="*60)
        
        all_chunks = []
                
        spells_file = self.raw_data_dir / "spells.json"
        if spells_file.exists():
            print("\n🔮 Processando magias...")
            with open(spells_file, 'r', encoding='utf-8') as f:
                spells = json.load(f)
            
            for spell in tqdm(spells, desc="Chunking spells"):
                chunk = self.chunker.chunk_spell(spell)
                all_chunks.append(chunk)
            
            print(f"✅ {len(spells)} magias processadas")
                
        monsters_file = self.raw_data_dir / "monsters.json"
        if monsters_file.exists():
            print("\n👹 Processando monstros...")
            with open(monsters_file, 'r', encoding='utf-8') as f:
                monsters = json.load(f)
            
            for monster in tqdm(monsters, desc="Chunking monsters"):
                chunk = self.chunker.chunk_monster(monster)
                all_chunks.append(chunk)
            
            print(f"✅ {len(monsters)} monstros processados")
                
        rules_file = self.raw_data_dir / "rules.json"
        if rules_file.exists():
            print("\n📜 Processando regras...")
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            
            for rule in tqdm(rules, desc="Chunking rules"):
                rule_chunks = self.chunker.chunk_rule_section(rule)
                all_chunks.extend(rule_chunks)
            
            print(f"✅ {len(rules)} seções de regras processadas")
                
        chunks_file = self.processed_data_dir / "all_chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Total de chunks criados: {len(all_chunks)}")
        print(f"💾 Salvos em: {chunks_file}")
        
        return all_chunks
    
    def step_3_generate_embeddings(self, chunks: List[Dict]):
        """Etapa 3: Geração de embeddings"""
        print("\n" + "="*60)
        print("ETAPA 3: GERAÇÃO DE EMBEDDINGS")
        print("="*60)
        
        if self.embedding_model is None:
            self.load_embedding_model()
                
        texts = [chunk['text'] for chunk in chunks]
        
        print(f"\n🧮 Gerando embeddings para {len(texts)} chunks...")
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )
                
        embeddings_file = self.embeddings_dir / "embeddings.npy"
        metadata_file = self.embeddings_dir / "metadata.json"
        
        np.save(embeddings_file, embeddings)
                
        metadata = [
            {
                'id': i,
                'metadata': chunk['metadata'],
                'token_count': chunk['token_count']
            }
            for i, chunk in enumerate(chunks)
        ]
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Embeddings salvos: {embeddings_file}")
        print(f"✅ Metadata salva: {metadata_file}")
        print(f"📊 Shape dos embeddings: {embeddings.shape}")
    
    def run_full_pipeline(self):        
        print("\n" + "🎲"*30)
        print("SAGE'S ORACLE - ETL PIPELINE")
        print("🎲"*30)
                
        self.step_1_scrape_data()
                
        chunks = self.step_2_process_and_chunk()
                
        self.step_3_generate_embeddings(chunks)
        
        print("\n" + "="*60)
        print("🎉 PIPELINE CONCLUÍDO COM SUCESSO!")
        print("="*60)
        print("\n📊 Arquivos gerados:")
        print(f"   📁 {self.raw_data_dir}/")
        print(f"   📁 {self.processed_data_dir}/")
        print(f"   📁 {self.embeddings_dir}/")


def main():    
    pipeline = ETLPipeline()
    pipeline.run_full_pipeline()

if __name__ == "__main__":
    main()