# AI-Gamie: Save, Load & The Legend Export

## ⏳ The "Chrono-Jester" (Anti-Save-Scumming)
The engine will track the "Timeline Health." If it detects a reload that reverts a "Character Death" or a "Natural 1," the UI triggers a playful interaction before loading.

### 🎭 Playful "Call-Outs":
- **The Tavern Keeper:** *"Back so soon? I could have sworn I saw you falling into that pit... must be the ale playing tricks on my eyes."*
- **The Bard:** *"A curious ripple in the song of your life... almost as if the strings were plucked backwards. Shall we try that verse again?"*
- **The Oracle:** *"The Fates have a sense of humor today, it seems. Averting destiny, are we? Fine, let's pretend that never happened."*

## 💾 Save System (The "Campfire")
- **Manual Save:** Triggered by the "Campfire" icon. Creates a timestamped folder with `Journal.md` and `GameData.sqlite`.
- **Auto-Save:** Every time the player enters a new major location (Transition Point).
- **Hard-Core Mode (Optional):** "Iron-Soul" mode where only one save exists and it deletes itself on character death (No save-scumming allowed!).

## 📜 The "Legend" Export (PDF)
At any point (or upon finishing a quest), the player can click the "Seal of Legend" to generate a PDF.

### 🏛️ PDF Layout:
- **Cover Page:** AI-generated "Hero Portrait" and "The Tale of [Character Name]."
- **The Chronicle:** A beautifully formatted version of the `Journal.md` story, styled with parchment backgrounds.
- **The Hall of Stats:** A final snapshot of the Character Sheet, Inventory, and Total Gold.
- **The Bestiary:** A list of every unique monster the player defeated during that run.

## ⚙️ Logic (How it works):
1. **Detection:** The Engine compares the `Last_Action_Result` in the current session with the `Last_Action_Result` in the file being loaded.
2. **Flagging:** If the current session result was "Death" or "Fail" and the loaded one is "Success" or "Before Action," the `Save_Scum_Flag` is set to `True`.
3. **The Joke:** The UI displays a random "Chrono-Jester" quote before the `Load` operation completes.
