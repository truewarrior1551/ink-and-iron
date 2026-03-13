import sqlite3;
conn = sqlite3.connect('/app/data/gamie.db');
cols = [
    ('sessions', 'race', 'TEXT NOT NULL DEFAULT "Human"'),
    ('sessions', 'charisma', 'INTEGER DEFAULT 10'),
    ('sessions', 'speed', 'INTEGER DEFAULT 30'),
    ('sessions', 'perception', 'INTEGER DEFAULT 10'),
    ('sessions', 'str', 'INTEGER DEFAULT 10'),
    ('sessions', 'dex', 'INTEGER DEFAULT 10'),
    ('sessions', 'con', 'INTEGER DEFAULT 10'),
    ('sessions', 'int', 'INTEGER DEFAULT 10'),
    ('sessions', 'wis', 'INTEGER DEFAULT 10'),
    ('sessions', 'cha', 'INTEGER DEFAULT 10'),
    ('sessions', 'proficiencies', 'TEXT DEFAULT "[]"'),
    ('sessions', 'npc_image', 'TEXT DEFAULT ""')
];
for t, c, d in cols:
    try: conn.execute(f'ALTER TABLE {t} ADD COLUMN {c} {d}'); print(f'Added {c}');
    except Exception as e: print(f'Skipped {c}: {e}');
conn.commit();
