import random

LOOT_TABLES: dict[str, list[tuple[str, float]]] = {
    "Goblin Guard": [
        ("Goblin's Short Sword", 0.9),
        ("Rusty Coin Pouch", 0.7),
        ("Stale Bread Crust", 0.5),
    ],
    "Skeletal Warrior": [
        ("Corroded Longsword", 0.85),
        ("Cracked Shield Fragment", 0.6),
        ("Ancient Coin", 0.8),
    ],
    "Wolf Pack": [
        ("Wolf Pelt", 0.8),
        ("Wolf Fang", 0.9),
    ],
    "Bandit Scout": [
        ("Bandit's Dagger", 0.75),
        ("Stolen Coin Purse", 0.6),
        ("Rough-spun Cloak", 0.4),
    ],
    "Giant Toad": [
        ("Toad Venom Sac", 0.7),
        ("Slick Hide", 0.5),
    ],
    "Stone Troll": [
        ("Troll Knucklebone", 0.9),
        ("Crude Iron Club", 0.6),
        ("Mountain Crystal", 0.3),
    ],
    "default": [
        ("Gold Coin", 0.8),
    ],
}


def roll_loot(enemy_name: str) -> list[str]:
    """Return a list of item names dropped by the enemy (probabilistic)."""
    table = LOOT_TABLES.get(enemy_name, LOOT_TABLES["default"])
    return [item for item, chance in table if random.random() < chance]
