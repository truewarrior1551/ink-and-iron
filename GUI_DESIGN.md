# AI-Gamie: GUI & Aesthetic Design

## 🕯️ Theme: "The Bard's Corner"
- **Background:** High-quality, slightly blurred (Gaussian blur) digital art of a candle-lit medieval tavern.
- **Color Palette:** Warm ambers, deep wood browns, parchment cream, and iron charcoal.
- **Typography:** Serif fonts (like *Lora* or *Crimson Text*) for the story; clean Sans-Serif for stats.

## 📜 The "Chronicle Scroll" (Right Sidebar)
- **Visual:** A vertical parchment scroll that "unfurls" as the story grows.
- **Function:** A real-time, read-only Markdown view of the `Journal.md`.
- **Content:** 
  - **The Tale So Far:** Automated summaries of previous chapters.
  - **The Current Scene:** The last few DM descriptions.
- **Sticky Header:** The character's name and current location (e.g., *"Sir Alistair @ The Whispering Woods"*).

## 📖 The "Hero's Ledger" (Character Sheet)
- **Visual:** A high-quality "Two-Page Spread" book overlay that opens when clicking the character's portrait.
- **Left Page (The Body):**
  - **Portrait:** AI-generated image of the character.
  - **Core Stats:** Large, ornate circles for STR, DEX, CON, INT, WIS, CHA.
  - **Combat Stats:** HP, AC, Initiative, and Speed clearly displayed.
- **Right Page (The Soul):**
  - **Skill List:** A list of proficiencies (Acrobatics, Insight, Stealth, etc.) with checkboxes for proficiency.
  - **Interactive Rolling:** Every skill name is a **clickable button**. Clicking "Stealth" automatically triggers the Dice Tray to roll `1d20 + DEX + Proficiency`.
  - **The Legend:** A short, scrollable area for the "Backstory" generated during character creation.

## 📊 The "Status HUD" (Top or Left Overlay)
- **Health Bar:** A classic red "liquid" bar with a gold ornate border.
- **Mana/Stamina:** A blue/green secondary bar.
- **Active Buffs:** Small icons for "Inspired," "Blessed," or "Injured."

## 🎲 The "Dice Tray" (Bottom Center)
- **Interactive:** When a roll is required, a 3D-style dice tray slides up from the bottom.
- **Result:** The roll animation plays, and the final number flashes before being sent to the "Chronicle Scroll."

## 🎒 The "Inventory Pouch" (Floating Action Button)
- **Visual:** A small leather pouch icon.
- **Function:** Opens a modal/drawer showing:
  - **Equipped:** Weapon, Armor, Trinket.
  - **Loot:** A list of items found during the session.
  - **Gold:** A coin counter.

## 🕹️ User Interaction
- **Chat Field:** Minimalist input at the bottom, styled like a "Writing Desk" with an inkwell icon as the 'Send' button.
- **Rolling Context:** Every 10 turns, the chat history is "Archived" into the Scroll, and the Chat Context is wiped to keep the AI (Ollama) fast and focused.
