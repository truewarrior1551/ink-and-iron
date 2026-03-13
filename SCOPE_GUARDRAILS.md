# AI-Gamie: Scope & Guardrail Strategy

## 🛡️ Rule 1: "The Referee is Boss"
The LLM (Ollama) is the **Narrator**, but the Python Engine is the **Referee**.
- **No Self-Rolling:** The LLM is forbidden from "rolling" dice in its text. It must only *request* a roll from the Engine.
- **No Stat-Editing:** The LLM cannot change the player's HP or Gold. It can only "suggest" a change (e.g., "The player loses 5 HP"), which the Engine then validates and applies to the SQLite database.

## 🧱 Rule 2: "The World-Boundary" (Context Injection)
To prevent the AI from going "out of scope," we use **Zonal Loading**:
- **Current Zone:** The ML Layer provides high-detail "Lore Seeds" for the player's current 50ft radius.
- **Known Zones:** Low-detail summaries for previously visited areas.
- **Locked Zones:** Zero data is provided for areas the player hasn't unlocked yet. This prevents the AI from "spoiling" the end of the game or making up locations that don't exist.

## 🤖 Rule 3: "The Structured DM" (JSON Interface)
We will prompt the AI to output in a hybrid **Markdown + JSON** format.
- **Markdown:** Used for the beautiful narration the player reads on the "Scroll."
- **JSON (Hidden):** Used for the Engine to update stats, trigger dice rolls, and manage the world state.

## 🚫 Out-of-Scope Detection
If the player tries to do something "Non-Fantasy" (e.g., "I pull out a cell phone"), the **System Prompt** has a hard-coded rejection:
> *"As a DM for a Medieval Fantasy game, you must steer the player back to the setting. Use the tavern environment to distract them or have an NPC react with confusion."*
