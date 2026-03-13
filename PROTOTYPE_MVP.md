# AI-Gamie: Prototype MVP (Day 1 Focus)

## 🎯 Goal: A Single-Player "Playable Loop"
By the end of the prototype phase, a player should be able to:
1. **Pick an Archetype** (Warrior, Mage, or Rogue).
2. **Enter the Tavern** (The starting location).
3. **Take 5-10 Actions** with the DM (Ollama) responding to dice rolls.
4. **See the "Chronicle Scroll" Update** after every turn.

## 🛠 Step 1: The "Stateless" Orchestrator (Python/FastAPI)
- **Task:** Create a single endpoint `/turn` that accepts player input.
- **Logic:** 
  - Read `Journal.md`.
  - Assemble the "DM System Prompt" (including stats + story history).
  - Call Ollama.
  - Parse the response (extract Narration vs. Roll Requests).
  - Wipe Ollama context for the next turn.

## 🎲 Step 2: The "Referee" (Roll Logic)
- **Task:** A simple function `roll_d20(modifier)` that the Orchestrator calls whenever the AI says "[ROLL: Stealth]".
- **Output:** Returns a result string that is fed back into the next AI prompt.

## 📜 Step 3: The "Tavern HUD" (Frontend)
- **Task:** A basic React/Vue page (or Open WebUI modification).
- **Required Elements:**
  - **Chat Field:** For player input.
  - **The Scroll:** A simple sidebar displaying the contents of `Journal.md`.
  - **Status Bar:** A red HP bar that reads from a local variable.

## 🗃 Step 4: Initial Data Seed (The World)
- **Task:** Create a `World_Data.json` with:
  - **Location:** "The Whispering Tankard Tavern."
  - **NPC:** "Barnaby the Barkeep" (Friendly, knows a secret about a map).
  - **Initial Prompt:** The "Hook" that starts the game.

## 🚫 What to SKIP (For Now):
- No Multiplayer.
- No PDF Export.
- No Advanced Vector DB (Just use a hardcoded JSON for the first 3 rooms).
- No Save/Load logic (Just a single "New Game" state).
