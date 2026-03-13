# AI-Gamie: Multiplayer & Party System

## 🌐 Networking: "Host-Join" Model
- **The Server (Host):** Runs the AI-Gamie Engine, Ollama, and the Master Database.
- **The Clients (Players):** Connect via a browser to the Host's IP/Tunnel.
- **Real-Time Sync:** Uses **WebSockets (Socket.io)** to ensure that when the DM speaks, everyone sees it at the same time.

## 👥 Party Management (The "Table")
- **The Party Table (SQLite):**
  - `sessions` (The active game world).
  - `players` (Linked to specific User Accounts).
  - `characters` (Stats, HP, and Inventory for each player).
- **The DM Prompt (Multi-Agent):**
  - The System Prompt is updated to: *"You are the DM for a party of 3. [Player 1: Warrior], [Player 2: Mage], [Player 3: Rogue]. Address them individually or as a group."*

## 🎲 Synchronized Interactions
- **Group Checks:** The DM can trigger a "Party Perception Check." A dice tray appears on every player's screen.
- **Turn Order:** The Engine manages the "Initiative Tracker" (visible in a small widget) so players know whose turn it is to act/speak.
- **Private Whispers:** A feature for the DM (AI) to send a secret message to only one player (e.g., *"Only you notice the trapdoor"*).

## 🛠 Multi-User GUI
- **Dashboard Synchronization:**
  - **Shared:** The "Chronicle Scroll" (The story history).
  - **Private:** The "Status Bars" and "Inventory Pouch" (Unique to each player's character).
- **The "Spectator" Mode:** Allows someone to join and read the scroll without having a character (great for "Legend PDF" generation later).

## 🛡 Security & Connectivity
- **Character Locking:** Players can only edit/roll for their assigned character.
- **Zero-Config Networking:** Recommended use of **Tailscale Funnels** or **Ngrok** to allow friends to join the local "Homelab" server securely.
