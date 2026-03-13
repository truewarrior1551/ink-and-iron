# Ink & Iron: Dark Fantasy Chronicles

**Ink & Iron** is a feature-rich, interactive Single-Player RPG engine that combines classic D&D 5e mechanics with modern AI-driven narration and dynamic world generation.

## 🚀 Version 0.8.0: The Triple Crown Update

### 🗝️ Core Features

#### 1. Advanced D&D 5e Character System
*   **The Big 6 Stats:** Full tracking for Strength, Dexterity, Constitution, Intelligence, Wisdom, and Charisma using the "Standard Array" distribution.
*   **Racial Bloodlines:** Choose from **Human, Elf, Dwarf, or Halfling**, each with unique stat bonuses and passive traits (e.g., Fey Ancestry, Darkvision, Dwarven Resilience).
*   **Interactive Leveling:** Earn XP through discovery and combat. Gain Max HP, Attribute Points (ASI), and new Proficiencies as you level up.

#### 2. Dynamic World Engine
*   **Perlin Noise Generation:** A massive **30x30 map** generated using layered noise algorithms for natural terrain flow (Mountain ridges, Woodland edges, Coastal lines).
*   **Fog of War:** Explore a shrouded world where tiles only reveal themselves as you step on them or use discovery magic.
*   **Landmark Discovery:** Uncover Points of Interest (POIs) that are automatically recorded in your permanent **Lore-Book**.

#### 3. Deep Gameplay Mechanics
*   **Interactive Dice UI:** Experience true player agency with a manual Dice Tray for all skill checks and saving throws.
*   **The Arsenal & Forge:** Gather materials (Iron Ore, Ancient Scraps) from the world to **Repair** and **Upgrade** your weapons.
*   **Bestiary:** Track your triumphs over 20+ unique D&D monsters that **automatically scale** to your level to keep the challenge alive.
*   **The Chrono-Jester:** A unique anti-save-scumming system that reacts narratively when you attempt to alter the timeline via the Undo (⌛) feature.

### 🔮 Magic & Spells
Full support for a growing Spellbook, including utility magic like:
*   **Far Sight:** Burn away the Fog of War in a massive radius.
*   **Feather Fall:** Survive dangerous descents and reach hidden heights.

## 🛠️ Technical Stack
*   **Backend:** FastAPI (Python 3.12)
*   **Database:** SQLite (State persistence & snapshots)
*   **Frontend:** Vanilla CSS & JS (Hardware accelerated layers)
*   **AI Engine:** Ollama (Llama 3.1:8b)
*   **Containerization:** Docker & Docker Compose

## 📦 Getting Started

### Prerequisites
*   Docker & Docker Compose
*   Ollama (with `llama3.1:8b` pulled)

### Installation
1.  Clone the repository:
    ```bash
    git clone https://github.com/truewarrior1551/ink-and-iron.git
    cd ink-and-iron
    ```
2.  Start the services:
    ```bash
    docker-compose up -d --build
    ```
3.  Open your browser at `http://localhost:8080`.

## 📜 Credits & License
*   **Lead Architect:** Gemini CLI
*   **Implementation:** Claude Code & Jamie
*   **Ruleset:** Open-D20 (D&D 5e SRD 5.1 compliant)
*   **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)

---
*Welcome to the realm of infinite story... What will your legend be?*
