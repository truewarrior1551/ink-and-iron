# AI-Gamie: Open-D20 Ruleset (CC-BY-4.0)

## ⚖️ Legal Foundation
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0).
- **Core Source:** Systems Reference Document 5.1 (SRD 5.1).
- **Attribution:** This engine utilizes the core mechanics of the 5e SRD as permitted under the CC-BY-4.0 license.

## 🎲 Visual Dice UI (Interactive)
The UI will feature a prominent, interactive 3D/2D dice tray.
- **Player Agency:** When the AI triggers a "Check," the UI prompts the player: *"Roll for Stealth!"*.
- **Visual Feedback:** The player clicks/taps to roll. The result is calculated by the engine (not the AI) and then sent to Ollama as: `[SYSTEM: Player rolled a 17 (14+3) for Stealth]`.
- **Transparency:** All modifiers (Proficiency, Ability) are visible in a breakdown tooltip.

## 🏗️ Mechanics Map
### 1. The D20 Resolution
- **Success/Failure:** d20 + Modifiers vs. Difficulty Class (DC).
- **Criticals:** Natural 20 (Critical Success), Natural 1 (Critical Failure).

### 2. Character Attributes
- **The Big Six:** Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma.
- **Progression:** Leveling system based on XP milestones.

### 3. Combat Economy
- **Turn-Based:** Movement, Action, Bonus Action, and Reaction.
- **Tactical Logic:** The engine tracks HP and AC in SQLite to prevent "LLM hallucination" of damage.
