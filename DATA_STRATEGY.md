# AI-Gamie Data & Lore Strategy

## 📂 Source Material (Open-Data)
To give the AI high-quality "Dungeon Master" behavior, we will ingest:
1. **The 5e SRD Bestiary & Spells:** For core mechanical data (monsters, items).
2. **Project Gutenberg (Public Domain):** For descriptive language (Gothic horror from Poe, Adventure from Lovecraft/Dumas).
3. **Open-Source Modules (Dungeon Masters Guild Free Tier):** To learn "Quest Structures" (The Hook, The Conflict, The Resolution).

## 🧠 The ML "Oracle" (RAG Pipeline)
- **Vector DB:** We will chunk these sources and store them in **ChromaDB**.
- **The Retrieval Hook:** When the player enters a "Forest," the engine queries the DB for "Forest Descriptions" and "Forest Encounters" and injects the top 3 results into the DM's "Inspiration" prompt.

## 📈 Story Guidelines (The "Heat Map")
The engine will enforce a "Story Arc" by tracking the phase of the game:
- **Phase: Introduction** (High detail on surroundings).
- **Phase: Inciting Incident** (Introduction of a threat/goal).
- **Phase: Rising Action** (Increasing Difficulty Class for rolls).
- **Phase: Climax** (Boss mechanics, high stakes).
- **Phase: Resolution** (Loot, XP, and setup for the next session).
