# AI-Gamie: Context Orchestrator

## 🔄 The "Round-Clear" Cycle
1. **Player Action:** "I try to talk my way past the guard."
2. **Engine Pre-Process:** 
   - **Roll Dice:** (D20 + CHA).
   - **Retrieve Lore:** (Search Vector DB for "Guard Dialog" and "Location: Keep").
3. **The "Stateless" Prompt:**
   - **SYSTEM:** You are the DM. The player is at [Location]. Current Goal is [Goal].
   - **CHARACTER:** [Stats/HP/Inventory].
   - **CHRONICLE:** [Last 3 Events Summary].
   - **ACTION:** The player rolled a 19 on Persuasion.
   - **INSPIRATION:** (From Lore DB) "The guard is tired and misses his family."
4. **Ollama Response:** DM narrates the success.
5. **Post-Process (The "Clear"):**
   - **Update MD Journal:** Log the 19 roll and the DM's response.
   - **Update SQLite:** If HP/Gold changed.
   - **Wipe Ollama Context:** Explicitly clear the session history (`/api/generate` with empty context or clear the conversation in the UI).
6. **Next Turn:** Start from Step 1 with a *new* stateless prompt using the updated data.

## 💾 The "Chronicle" (Long-Term Memory)
To keep the AI from forgetting older events, the **Chronicle** in the MD Journal uses a "Summary Pyramid":
- **Current Chapter:** (Full detail, last 5-10 turns).
- **Previous Chapter:** (3-5 sentence summary).
- **Previous Sessions:** (1-2 sentence summaries).
This ensures the AI knows *everything* that happened but only uses a few hundred tokens instead of thousands.
