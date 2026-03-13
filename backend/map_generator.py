import os
import random
import sqlite3
import json
import math
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent.parent / "gamie.db")))
POI_PATH = Path(__file__).parent / "data" / "poi_registry.json"

def lerp(a, b, x):
    return a + x * (b - a)

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def grad(hash, x, y):
    h = hash & 15
    grad_x = 1.0 if h & 8 == 0 else -1.0
    grad_y = 1.0 if h & 4 == 0 else -1.0
    if h & 1: grad_x *= x
    if h & 2: grad_y *= y
    return grad_x + grad_y

class PerlinNoise:
    def __init__(self):
        self.p = list(range(256))
        random.shuffle(self.p)
        self.p += self.p

    def noise(self, x, y):
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        u = fade(x)
        v = fade(y)
        A = self.p[X] + Y
        AA = self.p[A]
        AB = self.p[A + 1]
        B = self.p[X + 1] + Y
        BA = self.p[B]
        BB = self.p[B + 1]
        return lerp(v, lerp(u, grad(self.p[AA], x, y), grad(self.p[BA], x - 1, y)),
                    lerp(u, grad(self.p[AB], x, y - 1), grad(self.p[BB], x - 1, y - 1)))

def generate_map(session_id: str, size: int = 30):
    """Perlin Noise based map generator."""
    perlin = PerlinNoise()
    scale = 0.15
    octaves = 3
    persistence = 0.5
    lacunarity = 2.0

    grid = []
    for x in range(size):
        row = []
        for y in range(size):
            noise_val = 0
            amplitude = 1.0
            frequency = 1.0
            for _ in range(octaves):
                noise_val += perlin.noise(x * scale * frequency, y * scale * frequency) * amplitude
                amplitude *= persistence
                frequency *= lacunarity
            
            # Normalize to 0-1 range (Perlin returns roughly -1 to 1)
            v = (noise_val + 1) / 2
            
            if v < 0.35: terrain = "Water"
            elif v < 0.45: terrain = "Path"
            elif v < 0.70: terrain = "Woodland"
            elif v < 0.85: terrain = "Swamp"
            else: terrain = "Mountain"
            
            if x == 0 and y == 0: terrain = "Tavern"
            row.append(terrain)
        grid.append(row)

    # Load POIs
    pois = {}
    if POI_PATH.exists():
        pois = json.loads(POI_PATH.read_text())["points_of_interest"]
    
    # Save to DB
    map_data = []
    for x in range(size):
        for y in range(size):
            terrain = grid[x][y]
            poi_name = ""
            poi_desc = ""
            
            # Special case for Tavern
            if x == 0 and y == 0:
                poi_name = "The Whispering Tankard"
                poi_desc = "Your starting point. A safe haven in a dark world."
                terrain = "Path" # Logic uses Path for Tavern coords
            elif terrain in pois and random.random() < 0.12:
                p = random.choice(pois[terrain])
                poi_name = p["name"]
                poi_desc = p["description"]
                
            map_data.append((session_id, x, y, terrain, poi_name, poi_desc, 1 if x==0 and y==0 else 0))
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            "INSERT INTO world_map (session_id, x, y, terrain_type, poi_name, poi_description, is_explored) VALUES (?, ?, ?, ?, ?, ?, ?)",
            map_data
        )
        conn.commit()
    
    return grid

def get_terrain_at(session_id: str, x: int, y: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT terrain_type, poi_name, poi_description, state FROM world_map WHERE session_id = ? AND x = ? AND y = ?",
            (session_id, x, y)
        ).fetchone()
        return dict(row) if row else {"terrain_type": "Unknown", "poi_name": "", "poi_description": "", "state": "normal"}

def get_surroundings(session_id: str, x: int, y: int, radius: int = 1):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT x, y, terrain_type, poi_name, state, is_explored FROM world_map WHERE session_id = ? AND x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
            (session_id, x-radius, x+radius, y-radius, y+radius)
        ).fetchall()
        return [dict(row) for row in rows]
