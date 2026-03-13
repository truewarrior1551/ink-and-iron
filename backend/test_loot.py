import json
import random
from pathlib import Path

def simulate_loot(tier_input):
    loot_path = Path("/home/jamie/projects/ai-gamie/backend/data/loot_tables.json")
    loot_data = json.loads(loot_path.read_text())
    
    t_str = str(tier_input)
    if t_str in loot_data["tiers"]:
        t_cfg = loot_data["tiers"][t_str]
        
        # Gold roll
        g_gain = random.randint(t_cfg["gold_range"][0], t_cfg["gold_range"][1])
        
        # Item roll (50% chance)
        item_found = None
        if random.random() > 0.5:
            item_found = random.choice(t_cfg["items"])
            
        return g_gain, item_found
    return 0, None

# Test Tier 2 Loot
print("--- Chrono-Jester Loot Test (Tier 2) ---")
for i in range(3):
    gold, item = simulate_loot(2)
    item_desc = f"and a {item['name']} ({item['description']})" if item else "(No item found)"
    print(f"Roll {i+1}: You found {gold} gold {item_desc}")
