from typing import List, Dict, Any
import tiktoken

class TextChunker:    
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:        
        return len(self.encoding.encode(text))
    
    def chunk_spell(self, spell_data: Dict) -> Dict[str, Any]:
        desc_parts = []
        
        desc_parts.append(f"# {spell_data.get('name', 'Unknown Spell')}")
        desc_parts.append(f"**Level:** {spell_data.get('level', 0)}")
        desc_parts.append(f"**School:** {spell_data.get('school', {}).get('name', 'Unknown')}")
        desc_parts.append(f"**Casting Time:** {spell_data.get('casting_time', 'Unknown')}")
        desc_parts.append(f"**Range:** {spell_data.get('range', 'Unknown')}")
        desc_parts.append(f"**Duration:** {spell_data.get('duration', 'Unknown')}")
                
        components = []
        if spell_data.get('components', []):
            for comp in spell_data['components']:
                components.append(comp)
        desc_parts.append(f"**Components:** {', '.join(components)}")
                
        if spell_data.get('desc'):
            desc_parts.append("\n**Description:**")
            for desc_line in spell_data['desc']:
                desc_parts.append(desc_line)
                
        if spell_data.get('higher_level'):
            desc_parts.append("\n**At Higher Levels:**")
            for hl_line in spell_data['higher_level']:
                desc_parts.append(hl_line)
        
        full_text = "\n".join(desc_parts)
        
        return {
            "text": full_text,
            "metadata": {
                "type": "spell",
                "name": spell_data.get('name'),
                "level": spell_data.get('level'),
                "school": spell_data.get('school', {}).get('name'),
                "source": "SRD 5e",
                "url": f"https://www.dnd5eapi.co{spell_data.get('url', '')}"
            },
            "token_count": self.count_tokens(full_text)
        }
    
    def chunk_monster(self, monster_data: Dict) -> Dict[str, Any]:        
        desc_parts = []
        
        desc_parts.append(f"# {monster_data.get('name', 'Unknown Monster')}")
        desc_parts.append(f"*{monster_data.get('size', '')} {monster_data.get('type', '')}, {monster_data.get('alignment', '')}*")

        desc_parts.append(f"\n**Armor Class:** {monster_data.get('armor_class', [{}])[0].get('value', 'N/A')}")
        desc_parts.append(f"**Hit Points:** {monster_data.get('hit_points', 'N/A')}")
        desc_parts.append(f"**Speed:** {monster_data.get('speed', {})}")
        desc_parts.append(f"**Challenge Rating:** {monster_data.get('challenge_rating', 'N/A')}")
        desc_parts.append("\n**Ability Scores:**")
        for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            score = monster_data.get(ability, 10)
            modifier = (score - 10) // 2
            desc_parts.append(f"- {ability.upper()}: {score} ({modifier:+d})")

        if monster_data.get('special_abilities'):
            desc_parts.append("\n**Special Abilities:**")
            for ability in monster_data['special_abilities']:
                desc_parts.append(f"- **{ability.get('name')}:** {ability.get('desc')}")

        if monster_data.get('actions'):
            desc_parts.append("\n**Actions:**")
            for action in monster_data['actions']:
                desc_parts.append(f"- **{action.get('name')}:** {action.get('desc')}")
        
        full_text = "\n".join(desc_parts)
        
        return {
            "text": full_text,
            "metadata": {
                "type": "monster",
                "name": monster_data.get('name'),
                "cr": monster_data.get('challenge_rating'),
                "monster_type": monster_data.get('type'),
                "size": monster_data.get('size'),
                "source": "SRD 5e",
                "url": f"https://www.dnd5eapi.co{monster_data.get('url', '')}"
            },
            "token_count": self.count_tokens(full_text)
        }
    
    def chunk_rule_section(self, rule_data: Dict, max_tokens: int = 512, overlap: int = 50) -> List[Dict[str, Any]]:
        chunks = []
        
        title = rule_data.get('name', 'Unknown Rule')
        desc = rule_data.get('desc', '')
        full_text = f"# {title}\n\n{desc}"
        token_count = self.count_tokens(full_text)
        
        if token_count <= max_tokens:
            return [{
                "text": full_text,
                "metadata": {
                    "type": "rule",
                    "section": title,
                    "source": "SRD 5e",
                    "url": f"https://www.dnd5eapi.co{rule_data.get('url', '')}"
                },
                "token_count": token_count
            }]
        
        tokens = self.encoding.encode(full_text)
        
        for i in range(0, len(tokens), max_tokens - overlap):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "type": "rule",
                    "section": title,
                    "chunk_index": len(chunks),
                    "source": "SRD 5e",
                    "url": f"https://www.dnd5eapi.co{rule_data.get('url', '')}"
                },
                "token_count": len(chunk_tokens)
            })
        
        return chunks


def main():
    chunker = TextChunker()
    test_spell = {
        "name": "Fireball",
        "level": 3,
        "school": {"name": "Evocation"},
        "casting_time": "1 action",
        "range": "150 feet",
        "duration": "Instantaneous",
        "components": ["V", "S", "M"],
        "desc": ["A bright streak flashes from your pointing finger to a point you choose within range..."],
        "url": "/api/spells/fireball"
    }
    
    chunk = chunker.chunk_spell(test_spell)
    print(f"✅ Chunk criado: {chunk['token_count']} tokens")
    print(chunk['text'][:200])


if __name__ == "__main__":
    main()