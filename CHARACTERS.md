# AI-Gamie Character System

## 🛡️ Pre-Built Archetypes (The "Quick-Start" Trio)

### 1. The Iron-Bound (Warrior/Tank)
- **Role:** Physical powerhouse, expert with heavy armor and blades.
- **Core Stats:** High STR/CON, Low INT/WIS.
- **Specialty:** "Unyielding Resolve" (Bonus to saving throws against fear).

### 2. The Shadow-Walker (Rogue/Infiltrator)
- **Role:** Stealth, lockpicking, and high-crit backstabs.
- **Core Stats:** High DEX/CHA, Low STR/CON.
- **Specialty:** "Evasive Maneuver" (Once per encounter, dodge a direct physical attack).

### 3. The Arcanist (Mage/Controller)
- **Role:** Glass-cannon, master of elemental and utility magic.
- **Core Stats:** High INT/WIS, Low STR/DEX.
- **Specialty:** "Echoes of Knowledge" (Automatically knows basic history/lore of encountered locations).

---

## 🏗️ Custom Character Builder (The "Hero's Path")

### Custom Sheet Template (Stored as JSON/MD)
- **Name:** (User Input)
- **Race:** (Human, Elf, Dwarf, Halfling, etc.)
- **Class:** (Warrior, Mage, Rogue, Cleric, Paladin, Ranger)
- **Stats (4d6 drop lowest):** 
  - Strength (STR)
  - Dexterity (DEX)
  - Constitution (CON)
  - Intelligence (INT)
  - Wisdom (WIS)
  - Charisma (CHA)
- **Backstory Fragment:** (User-written or AI-generated based on prompts)
- **Initial Inventory:** (Class-based starting gear)

### The Builder Workflow:
1. **Selection:** UI presents the 3 Archetypes or "Create Custom".
2. **Dice Phase (Custom Only):** Virtual dice roll for each stat.
3. **Bio Phase:** Player inputs backstory or asks the AI to generate one.
4. **Finalization:** The data is committed to the `SQLite` database and written to the `Journal.md` as the "Character Genesis" entry.
