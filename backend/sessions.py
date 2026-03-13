import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent.parent / "gamie.db")))


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                archetype   TEXT NOT NULL,
                race        TEXT NOT NULL DEFAULT 'Human',
                hp          INTEGER NOT NULL,
                max_hp      INTEGER NOT NULL,
                mana        INTEGER NOT NULL,
                max_mana    INTEGER NOT NULL,
                gold        INTEGER DEFAULT 0,
                alignment   INTEGER DEFAULT 0,
                str         INTEGER DEFAULT 10,
                dex         INTEGER DEFAULT 10,
                con         INTEGER DEFAULT 10,
                int         INTEGER DEFAULT 10,
                wis         INTEGER DEFAULT 10,
                cha         INTEGER DEFAULT 10,
                charisma    INTEGER DEFAULT 10,
                speed       INTEGER DEFAULT 30,
                perception  INTEGER DEFAULT 10,
                proficiencies TEXT DEFAULT '[]',
                level       INTEGER DEFAULT 1,
                xp          INTEGER DEFAULT 0,
                xp_to_next_level INTEGER DEFAULT 100,
                turn_number INTEGER NOT NULL DEFAULT 1,
                location    TEXT NOT NULL DEFAULT 'tavern',
                x           INTEGER DEFAULT 0,
                y           INTEGER DEFAULT 0,
                in_combat      INTEGER NOT NULL DEFAULT 0,
                enemy_name     TEXT    NOT NULL DEFAULT '',
                enemy_hp       INTEGER NOT NULL DEFAULT 0,
                enemy_max_hp   INTEGER NOT NULL DEFAULT 0,
                enemy_ac       INTEGER NOT NULL DEFAULT 10,
                enemy_atk_bonus INTEGER NOT NULL DEFAULT 2,
                npc_image      TEXT DEFAULT '',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spellbook (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                spell_name   TEXT NOT NULL,
                level        INTEGER DEFAULT 0,
                description  TEXT,
                UNIQUE(session_id, spell_name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                item_name    TEXT NOT NULL,
                quantity     INTEGER DEFAULT 1,
                durability   INTEGER DEFAULT 100,
                max_durability INTEGER DEFAULT 100,
                upgrade_level INTEGER DEFAULT 0,
                is_weapon    BOOLEAN DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS world_objects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                object_name TEXT NOT NULL,
                description TEXT,
                location    TEXT NOT NULL,
                x           INTEGER DEFAULT 0,
                y           INTEGER DEFAULT 0,
                portable    INTEGER DEFAULT 1,
                state       TEXT DEFAULT 'intact'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                name        TEXT NOT NULL,
                archetype   TEXT NOT NULL DEFAULT 'default',
                hp          INTEGER NOT NULL,
                max_hp      INTEGER NOT NULL,
                active      INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                quest_id    TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'active',
                UNIQUE(session_id, quest_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL DEFAULT '0',
                UNIQUE(session_id, key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                data        TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS world_map (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                x               INTEGER NOT NULL,
                y               INTEGER NOT NULL,
                terrain_type    TEXT NOT NULL DEFAULT 'Path',
                poi_name        TEXT DEFAULT '',
                poi_description TEXT DEFAULT '',
                is_explored     INTEGER DEFAULT 0,
                state           TEXT DEFAULT '',
                state_turns     INTEGER DEFAULT 0,
                UNIQUE(session_id, x, y)
            )
        """)

        # New Migrations for Crafting
        migration_cols = [
            ("inventory", "durability", "INTEGER DEFAULT 100"),
            ("inventory", "max_durability", "INTEGER DEFAULT 100"),
            ("inventory", "upgrade_level", "INTEGER DEFAULT 0"),
            ("inventory", "is_weapon", "BOOLEAN DEFAULT 0"),
            ("world_map", "is_explored", "INTEGER DEFAULT 0"),
            ("sessions", "race", "TEXT NOT NULL DEFAULT 'Human'"),
            ("sessions", "charisma", "INTEGER DEFAULT 10"),
            ("sessions", "speed", "INTEGER DEFAULT 10"),
            ("sessions", "perception", "INTEGER DEFAULT 10"),
            ("sessions", "str", "INTEGER DEFAULT 10"),
            ("sessions", "dex", "INTEGER DEFAULT 10"),
            ("sessions", "con", "INTEGER DEFAULT 10"),
            ("sessions", "int", "INTEGER DEFAULT 10"),
            ("sessions", "wis", "INTEGER DEFAULT 10"),
            ("sessions", "cha", "INTEGER DEFAULT 10"),
            ("sessions", "proficiencies", "TEXT DEFAULT '[]'"),
            ("sessions", "available_stat_points", "INTEGER DEFAULT 0"),
            ("sessions", "available_skill_points", "INTEGER DEFAULT 0"),
            ("sessions", "pending_roll_skill", "TEXT"),
            ("sessions", "pending_roll_modifier", "INTEGER DEFAULT 0"),
            ("sessions", "last_roll_total", "INTEGER DEFAULT 0"),
            ("sessions", "character_name", "TEXT DEFAULT 'Adventurer'"),
        ]
        for table, col, defn in migration_cols:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass
        
        # New Lore-Book Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lore_book (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                location_name   TEXT NOT NULL,
                description     TEXT,
                discovered_at   TEXT NOT NULL,
                UNIQUE(session_id, location_name)
            )
        """)
        # New Bestiary Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bestiary (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                monster_name TEXT NOT NULL,
                kills        INTEGER DEFAULT 0,
                last_level   INTEGER DEFAULT 1,
                UNIQUE(session_id, monster_name)
            )
        """)
        conn.commit()


def record_discovery(session_id: str, location_name: str, description: str) -> bool:
    """Record a new discovery. Returns True if it was a new discovery."""
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO lore_book (session_id, location_name, description, discovered_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, location_name, description, now))
        return cursor.rowcount > 0


def get_lore_book(session_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM lore_book WHERE session_id = ? ORDER BY discovered_at DESC", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def mark_area_explored(session_id: str, x: int, y: int, radius: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE world_map SET is_explored = 1
            WHERE session_id = ? AND x BETWEEN ? AND ? AND y BETWEEN ? AND ?
        """, (session_id, x - radius, x + radius, y - radius, y + radius))


def get_inventory_item(session_id: str, item_name: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM inventory WHERE session_id = ? AND LOWER(item_name) = LOWER(?)", 
            (session_id, item_name)
        ).fetchone()
        return dict(row) if row else None


def get_highest_upgrade_weapon(session_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM inventory WHERE session_id = ? AND is_weapon = 1 ORDER BY upgrade_level DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        return dict(row) if row else None


def record_monster_kill(session_id: str, monster_name: str, player_level: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO bestiary (session_id, monster_name, kills, last_level)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(session_id, monster_name) DO UPDATE SET
                kills = kills + 1,
                last_level = ?
        """, (session_id, monster_name, player_level, player_level))


def get_bestiary(session_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bestiary WHERE session_id = ?", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def get_session(session_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def create_session(archetype: str, race: str, character_name: str, hp: int, max_hp: int, mana: int, max_mana: int, 
                   s_str: int = 10, s_dex: int = 10, s_con: int = 10, 
                   s_int: int = 10, s_wis: int = 10, s_cha: int = 10,
                   spd: int = 30, profs: list = []) -> str:
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sessions (id, archetype, race, character_name, hp, max_hp, mana, max_mana, str, dex, con, int, wis, cha, charisma, speed, perception, proficiencies, turn_number, location, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,'tavern',?,?)",
            (session_id, archetype, race, character_name, hp, max_hp, mana, max_mana, s_str, s_dex, s_con, s_int, s_wis, s_cha, s_cha, spd, s_wis, json.dumps(profs), now, now),
        )
    return session_id


def get_spellbook(session_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM spellbook WHERE session_id = ?", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def add_spell(session_id: str, spell_name: str, level: int = 0, description: str = "") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO spellbook (session_id, spell_name, level, description) VALUES (?,?,?,?)",
            (session_id, spell_name, level, description),
        )


def update_session(session_id: str, **kwargs) -> None:
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [session_id]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE sessions SET {cols} WHERE id = ?", vals)


def update_inventory_item(session_id: str, item_id: int, **kwargs) -> None:
    if not kwargs: return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [item_id, session_id]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE inventory SET {cols} WHERE id = ? AND session_id = ?", vals)


def get_inventory(session_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM inventory WHERE session_id = ?", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def add_to_inventory(session_id: str, item_name: str, quantity: int = 1) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT id FROM inventory WHERE session_id = ? AND LOWER(item_name) = LOWER(?)", (session_id, item_name)
        ).fetchone()
        if existing:
            conn.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (quantity, existing[0]))
        else:
            conn.execute(
                "INSERT INTO inventory (session_id, item_name, quantity) VALUES (?,?,?)",
                (session_id, item_name, quantity),
            )


def get_visible_objects(session_id: str, location: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM world_objects WHERE session_id = ? AND LOWER(location) = LOWER(?)", (session_id, location)
        ).fetchall()
        return [dict(r) for r in rows]


def pick_up_object(session_id: str, object_name: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        obj = conn.execute(
            "SELECT * FROM world_objects WHERE session_id = ? AND LOWER(object_name) = LOWER(?) AND portable = 1",
            (session_id, object_name),
        ).fetchone()
        if obj:
            add_to_inventory(session_id, obj["object_name"]) # Use the original name from DB
            conn.execute("DELETE FROM world_objects WHERE id = ?", (obj["id"],))
            return True
        return False


def object_exists(session_id: str, object_name: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM world_objects WHERE session_id = ? AND object_name = ?", (session_id, object_name)
        ).fetchone()
        return row is not None


def spawn_object(session_id: str, name: str, description: str, location: str, portable: bool) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO world_objects (session_id, object_name, description, location, portable, state) VALUES (?,?,?,?,?,?)",
            (session_id, name, description, location, int(portable), "intact"),
        )


def seed_world_objects(session_id: str) -> None:
    default_objects = [
        ("Rusty Sword", "A battered old sword mounted on the tavern wall.", "tavern", 1),
        ("Barrel", "A large barrel of ale.", "tavern", 0),
        ("Mysterious Chest", "A locked chest in the corner.", "tavern", 0),
    ]
    with sqlite3.connect(DB_PATH) as conn:
        for name, desc, loc, portable in default_objects:
            conn.execute(
                "INSERT INTO world_objects (session_id, object_name, description, location, portable, state) VALUES (?,?,?,?,?,?)",
                (session_id, name, desc, loc, portable, "intact"),
            )


def get_active_companions(session_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM companions WHERE session_id = ? AND active = 1", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_companion(session_id: str, name: str, archetype: str, hp: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO companions (session_id, name, archetype, hp, max_hp, active) VALUES (?,?,?,?,?,1)",
            (session_id, name, archetype, hp, hp),
        )


def update_companion_hp(session_id: str, name: str, damage: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE companions SET hp = max(0, hp - ?) WHERE session_id = ? AND name = ?",
            (damage, session_id, name),
        )


def get_all_flags(session_id: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT key, value FROM flags WHERE session_id = ?", (session_id,)).fetchall()
        return {r[0]: r[1] for r in rows}


def get_flag(session_id: str, key: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM flags WHERE session_id = ? AND key = ?", (session_id, key)
        ).fetchone()
        return row[0] if row else "0"


def set_flag(session_id: str, key: str, value: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO flags (session_id, key, value) VALUES (?,?,?)", (session_id, key, value)
        )


def get_quests(session_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM quests WHERE session_id = ?", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def set_quest(session_id: str, quest_id: str, status: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO quests (session_id, quest_id, status) VALUES (?,?,?)",
            (session_id, quest_id, status),
        )


def create_snapshot(session_id: str, turn_number: int) -> None:
    session = get_session(session_id)
    inventory = get_inventory(session_id)
    data = json.dumps({"session": session, "inventory": inventory})
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO snapshots (session_id, turn_number, data) VALUES (?,?,?)",
            (session_id, turn_number, data),
        )


def restore_snapshot(session_id: str, target_turn: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT data FROM snapshots WHERE session_id = ? AND turn_number = ? ORDER BY id DESC LIMIT 1",
            (session_id, target_turn),
        ).fetchone()
        if not row:
            return False
        saved = json.loads(row[0])
        s = saved["session"]
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE sessions SET archetype=?, race=?, hp=?, mana=?, gold=?, alignment=?, charisma=?, speed=?, perception=?, level=?, xp=?, xp_to_next_level=?, "
            "turn_number=?, location=?, x=?, y=?, in_combat=?, enemy_name=?, enemy_hp=?, enemy_max_hp=?, updated_at=? WHERE id=?",
            (
                s["archetype"], s["race"], s["hp"], s["mana"], s["gold"], s["alignment"], s["charisma"], s["speed"], s["perception"], s["level"], s["xp"], s["xp_to_next_level"],
                s["turn_number"], s["location"], s["x"], s["y"],
                s["in_combat"], s["enemy_name"], s["enemy_hp"], s["enemy_max_hp"],
                now, session_id,
            ),
        )
        conn.execute("DELETE FROM inventory WHERE session_id = ?", (session_id,))
        for item in saved["inventory"]:
            conn.execute(
                "INSERT INTO inventory (session_id, item_name, quantity, durability, max_durability, upgrade_level, is_weapon) VALUES (?,?,?,?,?,?,?)",
                (session_id, item["item_name"], item["quantity"], item["durability"], item["max_durability"], item["upgrade_level"], item["is_weapon"]),
            )
        return True
