import requests
import json
import time
from pathlib import Path
from typing import Dict, List
from bs4 import BeautifulSoup
from tqdm import tqdm


class SRDScraper:
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)        
        self.base_urls = {
            "spells": "https://www.dnd5eapi.co/api/spells",
            "monsters": "https://www.dnd5eapi.co/api/monsters",
            "classes": "https://www.dnd5eapi.co/api/classes",
            "rules": "https://www.dnd5eapi.co/api/rule-sections",
            "equipment": "https://www.dnd5eapi.co/api/equipment"
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SagesOracle/1.0 (Educational Project)'
        })
    
    def fetch_json(self, url: str, delay: float = 0.5) -> Dict:
        try:
            time.sleep(delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar {url}: {e}")
            return {}
    
    def scrape_category(self, category: str) -> List[Dict]:
        print(f"\n📚 Coletando dados de: {category.upper()}")

        index_url = self.base_urls.get(category)
        if not index_url:
            print(f"⚠️  Categoria {category} não encontrada")
            return []
        
        index_data = self.fetch_json(index_url)
        results = index_data.get('results', [])
        
        if not results:
            print(f"⚠️  Nenhum resultado encontrado para {category}")
            return []

        items = []
        for item in tqdm(results, desc=f"Processando {category}"):
            item_url = f"https://www.dnd5eapi.co{item['url']}"
            item_data = self.fetch_json(item_url)
            
            if item_data:
                items.append(item_data)

        output_file = self.output_dir / f"{category}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {len(items)} itens salvos em {output_file}")
        return items
    
    def scrape_all(self) -> Dict[str, List]:
        print("🚀 Iniciando coleta de dados do SRD 5e")
        print("=" * 50)
        
        all_data = {}
        for category in self.base_urls.keys():
            all_data[category] = self.scrape_category(category)
            time.sleep(1) 
        print("\n" + "=" * 50)
        print("🎉 Coleta finalizada!")
        print(f"📊 Total de itens coletados:")
        for category, items in all_data.items():
            print(f"   - {category}: {len(items)}")
        
        return all_data


def main():
    scraper = SRDScraper()
    scraper.scrape_all()


if __name__ == "__main__":
    main()