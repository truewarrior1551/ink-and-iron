# AI-Gamie Technical Stack

## 🧠 Brain (LLM)
- **Engine:** Ollama (self-hosted)
- **Primary Models:** `llama3.1:8b` (General DM), `mistral-nemo:12b` (Deep World-building).

## 📚 Story Engine (ML Layer)
- **Vector Database:** ChromaDB or Pinecone (Local preferred).
- **Data Source:** Scraped/Curated TTRPG modules, homebrew stories, and character sheets.
- **RAG Pipeline:** Retrieve story fragments based on player location/action to "seed" Ollama's creativity.

## 🗄️ Persistence Layer (The "Vault")
- **Journal:** Structured Markdown files (as discussed) for the active session.
- **Database:** SQLite for hard stats (HP, Level, Inventory, Gold) to ensure 100% accuracy (LLMs are bad at math, so we store the "Truth" in SQL).

## 🖥️ Frontend (The GUI)
- **Base:** Open WebUI (Derivative).
- **Customizations:** 
  - Integrated 3D Dice Roller (JS-based).
  - Character Sheet Sidebar (Live-synced with SQLite).
  - "Memory Map" visualization (showing the MD-journal structure).

## ⚙️ Middleware (The "Orchestrator")
- **Language:** Python (FastAPI).
- **Logic:** Handles the loop: `Player Input` -> `ML Retrieval` -> `SQL Update` -> `Ollama Prompt` -> `Update Journal`.
