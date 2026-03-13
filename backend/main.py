import json
import os
import random
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dice import parse_roll_requests, roll_d20, roll_dn
from journal import append_journal, init_journal, read_journal, read_journal_summary
from loot import roll_loot
from map_generator import generate_map, get_surroundings, get_terrain_at
from ollama_client import call_ollama
from sd_client import quick_generate
from sessions import (
    add_companion,
    add_to_inventory,
    create_session,
    create_snapshot,
    get_active_companions,
    get_all_flags,
    get_flag,
    get_inventory,
    get_quests,
    get_session,
    get_visible_objects,
    init_db,
    object_exists,
    pick_up_object,
    restore_snapshot,
    seed_world_objects,
    set_flag,
    set_quest,
    spawn_object,
    update_companion_hp,
    update_session,
    get_spellbook,
    add_spell,
    record_monster_kill,
    get_bestiary,
    record_discovery,
    get_lore_book,
    mark_area_explored,
    get_inventory_item,
    get_highest_upgrade_weapon,
)

app = FastAPI(title="AI-Gamie", version="0.8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORLD_PATH = Path(__file__).parent / "data" / "World_Data.json"
BESTIARY_PATH = Path(__file__).parent / "data" / "Bestiary_Data.json"
DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent.parent / "gamie.db")))
LOOT_PATH = Path(__file__).parent / "data" / "loot_tables.json"

COMPANION_ARCHETYPES: dict[str, dict] = {
    "warrior": {"attack_bonus": 3, "damage_die": 6, "str_mod": 2},
    "mage":    {"attack_bonus": 1, "damage_die": 8, "str_mod": 0},
    "rogue":   {"attack_bonus": 2, "damage_die": 4, "str_mod": 1},
    "default": {"attack_bonus": 1, "damage_die": 6, "str_mod": 0},
}


@app.on_event("startup")
async def startup():
    init_db()


def load_world() -> dict:
    return json.loads(WORLD_PATH.read_text(encoding="utf-8"))


def build_system_prompt(
    world: dict,
    archetype: str,
    race: str,
    character_name: str,
    hp: int,
    mana: int,
    alignment: int,
    charisma: int,
    speed: int,
    perception: int,
    level: int,
    xp: int,
    xp_to_next_level: int,
    location_key: str,
    x: int,
    y: int,
    terrain: str,
    poi_name: str,
    poi_desc: str,
    is_new_discovery: bool,
    surroundings: list,
    companions: list,
    journal_content: str,
    visible_objects: list,
    inventory: list,
    quests: list | None = None,
    flags: dict | None = None,
) -> str:
    arch = world["archetypes"].get(archetype, world["archetypes"]["warrior"])
    loc = world["locations"].get(location_key, world["locations"]["tavern"])
    journal_section = journal_content.strip() if journal_content.strip() else "This is the beginning of the adventure."

    obj_list = "\n".join([f"- {o['object_name']}: {o['description']} (State: {o['state']})" for o in visible_objects]) or "Nothing notable."
    inv_list = "\n".join([f"- {i['item_name']} (x{i['quantity']})" for i in inventory]) if inventory else "Empty"
    comp_list = "\n".join([f"- {c['name']} ({c['archetype']}) | HP: {c['hp']}/{c['max_hp']}" for c in companions]) if companions else "None"
    surround_desc = ", ".join([f"({s['x']},{s['y']}): {s['terrain_type']}" for s in surroundings])

    poi_section = ""
    if poi_name and is_new_discovery:
        poi_section = f"\nNEW DISCOVERY ON THIS TILE: {poi_name} — {poi_desc}"
    elif poi_name:
        poi_section = f"\nKNOWN LANDMARK HERE: {poi_name}"

    # Stats display
    hp_display = f"{hp}/{arch['max_hp']}"
    mana_display = f" | Mana: {mana}/{arch['max_mana']}" if arch.get("max_mana", 0) > 0 else ""
    prog_display = f" | Level: {level} (XP: {xp}/{xp_to_next_level}) | Alignment: {alignment}"
    stat_display = f" | Race: {race} | CHA: {charisma} | SPD: {speed} | PER: {perception}"

    # Quests context
    quest_lines = ""
    if quests:
        active = [q for q in quests if q["status"] == "active"]
        if active:
            quest_lines = "\nACTIVE QUESTS:\n" + "\n".join(
                f"- {q['quest_id'].replace('_', ' ').title()} ({q['status']})"
                for q in active
            )

    # World flags context
    flag_lines = ""
    if flags:
        relevant = {k: v for k, v in flags.items() if v != "0"}
        if relevant:
            flag_lines = "\nWORLD STATE: " + ", ".join(f"{k}={v}" for k, v in relevant.items())

    npc_section = ""
    if "npc" in loc:
        npc = loc["npc"]
        npc_section = (
            f"\nNPC IN SCENE: {npc['name']} {npc['title']} — {npc['description']}"
            f"\nNPC BEHAVIOUR: {npc['secret']}"
        )

    encounter_section = ""
    if "encounter" in loc:
        enc = loc["encounter"]
        encounter_section = (
            f"\nENCOUNTER PRESENT: {enc['name']} "
            f"(HP {enc['hp']}, AC {enc['ac']}, ATK +{enc['attack_bonus']}) — {enc['description']}"
        )

    location_keys = ", ".join(world["locations"].keys())

    return f"""You are a Dungeon Master for a solo fantasy RPG. Be immersive, concise, and reactive to dice rolls.

CURRENT LOCATION: {loc['name']} at Coordinates ({x}, {y})
TERRAIN: {terrain}{poi_section}
SURROUNDINGS: {surround_desc}

VISIBLE OBJECTS:
{obj_list}

CHARACTER NAME: {character_name}
PLAYER ARCHETYPE: {arch['display_name']}{stat_display}
STATS: HP: {hp_display}{mana_display}{prog_display}
PLAYER INVENTORY: {inv_list}

ACTIVE COMPANIONS:
{comp_list}{quest_lines}{flag_lines}

CHRONICLE (story so far):
{journal_section}

RULES:
- AUTHORITATIVE TAGS: You MUST use these tags to change the game state. If you narrate an item pickup without [GET: Item Name], the player DOES NOT receive it.
- Use the character name "{character_name}" in your narration when appropriate.
- If an action requires a skill check, output exactly: [ROLL: SkillName]
- To change alignment (Honor), output: [ALIGNMENT: N] (e.g. [ALIGNMENT: -5] for cruelty, [ALIGNMENT: 5] for heroism)
- To award XP for discovery/deeds, output: [XP: N] (Small discovery = 10, Major deed = 50)
- If the player takes damage, output exactly: [DAMAGE: N]
- If the player is healed, output exactly: [HEAL: N]
- If the player moves, output exactly: [MOVE: X, Y] or [MOVE_TO: location_key]
- If you grant loot, output exactly: [LOOT: Tier] (1=Common, 2=Rare, 3=Epic).
- To give a specific item, output exactly: [GET: Item Name]
- To cast a spell (Player or NPC), output exactly: [CAST: SpellName]
- If a companion joins, output exactly: [COMPANION_JOIN: Name | Archetype | HP]
- TACTICAL ENVIRONMENT:
    - To break an object, output: [BREAK: ObjectName]
    - To set a tile state (fire/ice/oil), output: [TILE_STATE: X | Y | state | turns]
    - To move an object, output: [PUSH: ObjectName | TargetX | TargetY]
    - Use these to let the player crush enemies with boulders, freeze water, or ignite oil.
- Keep narration under 100 words. DO NOT repeat "Dungeon Master:" or "**DM:**" in your output.
- If the player just bought or used an item via a (System: ...) note, narrate the transaction or the effect (e.g. drinking the potion) as part of the story.
- Stay in the medieval fantasy setting
- The Python engine handles all stat changes — your tags trigger them{npc_section}{encounter_section}"""


# ── Tag parsing ───────────────────────────────────────────────────────────────

def parse_stat_tags(text: str) -> dict:
    """Return a dictionary of all parsed tags."""
    damage = sum(int(m.group(1)) for m in re.finditer(r"\[DAMAGE:\s*(\d+)\]", text))
    heal = sum(int(m.group(1)) for m in re.finditer(r"\[HEAL:\s*(\d+)\]", text))
    mana = sum(int(m.group(1)) for m in re.finditer(r"\[MANA:\s*(\d+)\]", text))
    alignment = sum(int(m.group(1)) for m in re.finditer(r"\[ALIGNMENT:\s*([+-]?\d+)\]", text))
    xp = sum(int(m.group(1)) for m in re.finditer(r"\[XP:\s*(\d+)\]", text))
    
    loot_tiers = [int(m.group(1).strip()) for m in re.finditer(r"\[LOOT:\s*(\d+)\]", text)]

    move_to_m = re.search(r"\[MOVE_TO:\s*([^\]]+)\]", text)
    move_to = move_to_m.group(1).strip().lower() if move_to_m else None

    move_m = re.search(r"\[MOVE:\s*(\d+)\s*,\s*(\d+)\]", text)
    move_coords = (int(move_m.group(1)), int(move_m.group(2))) if move_m else None

    get_items = [m.group(1).strip() for m in re.finditer(r"\[GET:\s*([^\]]+)\]", text)]

    spawn_items = []
    for m in re.finditer(r"\[SPAWN:\s*([^\]]+)\]", text):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 4:
            spawn_items.append({
                "name": parts[0], "description": parts[1],
                "location": parts[2].lower(), "portable": parts[3] == "1"
            })

    spawn_enemies = []
    for m in re.finditer(r"\[SPAWN_ENEMY:\s*([^\]]+)\]", text):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 4:
            spawn_enemies.append({
                "name": parts[0], "hp": int(parts[1]), "ac": int(parts[2]), "atk": int(parts[3])
            })

    companion_joins = []
    for m in re.finditer(r"\[COMPANION_JOIN:\s*([^\]]+)\]", text):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 3:
            companion_joins.append({"name": parts[0], "archetype": parts[1], "hp": int(parts[2])})

    companion_dmg = []
    for m in re.finditer(r"\[COMPANION_DAMAGE:\s*([^\]]+)\]", text):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 2:
            companion_dmg.append({"name": parts[0], "amount": int(parts[1])})

    flags = {}
    for m in re.finditer(r"\[FLAG:\s*([^=\]]+)=([^\]]+)\]", text):
        flags[m.group(1).strip()] = m.group(2).strip()

    quest_updates = {}
    for m in re.finditer(r"\[QUEST:\s*([^=\]]+)=([^\]]+)\]", text):
        quest_updates[m.group(1).strip()] = m.group(2).strip()

    cast_spells = [m.group(1).strip() for m in re.finditer(r"\[CAST:\s*([^\]]+)\]", text)]

    return {
        "damage": damage, "heal": heal, "mana": mana,
        "alignment": alignment, "xp": xp,
        "loot_tiers": loot_tiers,
        "move_to": move_to, "move_coords": move_coords,
        "get_items": get_items, "spawn_items": spawn_items,
        "spawn_enemies": spawn_enemies,
        "companion_joins": companion_joins, "companion_dmg": companion_dmg,
        "flags": flags, "quest_updates": quest_updates,
        "cast_spells": cast_spells,
    }


def strip_stat_tags(text: str) -> str:
    return re.sub(
        r"\[(DAMAGE|HEAL|MANA|MOVE|MOVE_TO|GET|SPAWN|SPAWN_ENEMY|COMPANION_JOIN|COMPANION_DAMAGE|FLAG|QUEST|LOOT|ALIGNMENT|XP|BREAK|TILE_STATE|PUSH|REST|FORGE):\s*[^\]]+\]",
        "", text
    ).strip()


# ── Terrain encounters ────────────────────────────────────────────────────────

def _get_scaled_monster(monster: dict, player_level: int) -> dict:
    """Scale monster stats based on player level compared to CR."""
    base_level = max(1, int(monster["cr"] * 4)) # CR 1/4 -> Lvl 1, CR 1 -> Lvl 4
    delta = player_level - base_level
    
    # Scaling math
    hp = int(monster["base_hp"] * (1 + (0.2 * max(0, delta))))
    ac = monster["base_ac"] + max(0, delta // 2)
    atk = monster["base_atk"] + max(0, delta // 2)
    
    return {
        "name": monster["name"],
        "hp": hp,
        "ac": ac,
        "attack_bonus": atk,
        "description": monster["description"],
        "xp": int(monster["cr"] * 100) + (player_level * 10)
    }


def _random_encounter_for_terrain(terrain_type: str, player_level: int) -> dict | None:
    if not BESTIARY_PATH.exists(): return None
    monsters = json.loads(BESTIARY_PATH.read_text())["monsters"]
    
    # Filter by terrain
    eligible = [m for m in monsters if terrain_type in m["terrains"]]
    if not eligible: return None
    
    # Filter by CR (don't show extremely hard monsters early)
    # Allow CR up to Level/2 + 1
    max_cr = (player_level / 2) + 1
    reasonable = [m for m in eligible if m["cr"] <= max_cr]
    
    if not reasonable: reasonable = eligible # Fallback
    
    monster = random.choice(reasonable)
    return _get_scaled_monster(monster, player_level)


# ── Quest helpers ─────────────────────────────────────────────────────────────

def _advance_quests(session_id: str, world: dict) -> None:
    """Check world flags and activate/complete quests automatically."""
    flags = get_all_flags(session_id)
    existing = {q["quest_id"]: q["status"] for q in get_quests(session_id)}
    for qid, qdef in world.get("quests", {}).items():
        trigger = qdef.get("trigger_flag", "")
        complete = qdef.get("complete_flag", "")
        if flags.get(trigger, "0") != "0" and qid not in existing:
            set_quest(session_id, qid, "active")
        if flags.get(complete, "0") != "0" and existing.get(qid) == "active":
            set_quest(session_id, qid, "complete")


# ── Models ────────────────────────────────────────────────────────────────────

class NewSessionRequest(BaseModel):
    archetype: str = "warrior"
    race: str = "human"
    character_name: str = "Adventurer"


class PendingRoll(BaseModel):
    skill: str
    modifier: int


class SessionResponse(BaseModel):
    session_id: str
    archetype: str
    race: str
    character_name: str = "Adventurer"
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    speed: int = 30
    perception: int = 10
    proficiencies: list[str] = []
    traits: list[str] = []
    spellbook: list[dict] = []
    available_stat_points: int = 0
    available_skill_points: int = 0
    pending_roll: PendingRoll | None = None
    jester_msg: str | None = None
    bestiary: list[dict] = []
    lore_book: list[dict] = []
    gold: int = 0
    alignment: int = 0
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    turn_number: int
    location: str
    location_name: str
    inventory: list[dict]
    quests: list[dict] = []
    companions: list[dict] = []
    x: int = 0
    y: int = 0
    surroundings: list[dict] = []
    in_combat: int = 0
    enemy_name: str = ""
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    npc_image: str = ""


class TurnRequest(BaseModel):
    player_input: str
    session_id: str


class RollResult(BaseModel):
    roll: int
    modifier: int
    total: int
    description: str


class TurnResponse(BaseModel):
    narration: str
    roll_result: RollResult | None
    pending_roll: PendingRoll | None = None
    journal_entry: str
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    speed: int = 30
    perception: int = 10
    proficiencies: list[str] = []
    traits: list[str] = []
    spellbook: list[dict] = []
    available_stat_points: int = 0
    available_skill_points: int = 0
    bestiary: list[dict] = []
    lore_book: list[dict] = []
    gold: int = 0
    alignment: int = 0
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    turn_number: int
    location: str
    location_name: str
    inventory: list[dict]
    quests: list[dict] = []
    companions: list[dict] = []
    x: int = 0
    y: int = 0
    terrain: str = "Path"
    poi_name: str = ""
    surroundings: list[dict] = []
    in_combat: int = 0
    enemy_name: str = ""
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    npc_image: str = ""
    race: str = "Human"
    character_name: str = "Adventurer"


class RollSubmissionRequest(BaseModel):
    session_id: str
    roll_total: int
    skill: str
    modifier: int


class UndoRequest(BaseModel):
    session_id: str
    target_turn: int


class CombatActionRequest(BaseModel):
    session_id: str
    action: str  # "attack" | "defend" | "flee"


class CompanionAction(BaseModel):
    name: str
    roll: int
    hit: bool
    damage: int
    knocked_out: bool


class CombatRound(BaseModel):
    action: str
    player_roll: int
    player_hit: bool
    player_damage: int
    enemy_roll: int
    enemy_hit: bool
    enemy_damage: int
    fled: bool
    flee_success: bool
    companion_actions: list[CompanionAction] = []
    enemy_targeted_companion: str = ""
    enemy_companion_damage: int = 0


class CombatResponse(BaseModel):
    narration: str
    combat_round: CombatRound
    hp: int
    max_hp: int
    mana: int = 0
    max_mana: int = 0
    enemy_hp: int
    enemy_max_hp: int
    enemy_name: str
    in_combat: int
    turn_number: int
    location: str
    location_name: str
    inventory: list[dict]
    quests: list[dict] = []
    companions: list[dict] = []
    journal_entry: str
    victory: bool
    defeat: bool
    archetype: str = "warrior"
    race: str = "Human"
    character_name: str = "Adventurer"
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    speed: int = 30
    perception: int = 10
    proficiencies: list[str] = []
    traits: list[str] = []
    bestiary: list[dict] = []
    lore_book: list[dict] = []
    gold: int = 0
    alignment: int = 0
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    x: int = 0
    y: int = 0
    surroundings: list[dict] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/world")
async def get_world():
    world = load_world()
    world["version"] = "0.7.0"
    return world


@app.post("/session/new", response_model=SessionResponse)
async def new_session(req: NewSessionRequest):
    world = load_world()
    archetype_key = req.archetype.lower()
    race_key = req.race.lower()
    
    if archetype_key not in world["archetypes"]:
        raise HTTPException(status_code=400, detail=f"Unknown archetype: {req.archetype}")
    if race_key not in world["races"]:
        raise HTTPException(status_code=400, detail=f"Unknown race: {req.race}")

    arch = world["archetypes"][archetype_key]
    race_data = world["races"][race_key]
    
    # Base Stats from Archetype
    base_stats = arch.get("stats", {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10})
    s_str, s_dex, s_con = base_stats["str"], base_stats["dex"], base_stats["con"]
    s_int, s_wis, s_cha = base_stats["int"], base_stats["wis"], base_stats["cha"]
    
    # Apply Racial Bonuses
    bonuses = race_data.get("bonuses", {})
    s_str += bonuses.get("str", 0)
    s_dex += bonuses.get("dex", 0)
    s_con += bonuses.get("con", 0)
    s_int += bonuses.get("int", 0)
    s_wis += bonuses.get("wis", 0)
    s_cha += bonuses.get("cha", 0)
    
    # Derived Stats
    max_hp = arch["max_hp"] + bonuses.get("hp", 0) + ((s_con - 10) // 2)
    hp = max_hp
    speed = 30 + bonuses.get("speed", 0)
    profs = arch.get("profs", [])
    
    session_id = create_session(
        archetype=archetype_key,
        race=race_data["display_name"],
        character_name=req.character_name,
        hp=hp, max_hp=max_hp,
        mana=arch.get("mana", 0), max_mana=arch.get("max_mana", 0),
        s_str=s_str, s_dex=s_dex, s_con=s_con,
        s_int=s_int, s_wis=s_wis, s_cha=s_cha,
        spd=speed, profs=profs
    )

    # Add starting spells if any
    for sname in arch.get("starting_spells", []):
        if sname in world["spells"]:
            sdef = world["spells"][sname]
            add_spell(session_id, sname, sdef["level"], sdef["description"])

    generate_map(session_id)
    seed_world_objects(session_id)
    set_flag(session_id, "game_start", "1")
    _advance_quests(session_id, world)
    init_journal(world["initial_hook"])

    loc = world["locations"]["tavern"]
    return SessionResponse(
        session_id=session_id,
        archetype=archetype_key,
        race=race_data["display_name"],
        character_name=req.character_name,
        hp=hp, max_hp=max_hp,
        mana=arch.get("mana", 0), max_mana=arch.get("max_mana", 0),
        strength=s_str, dexterity=s_dex, constitution=s_con, 
        intelligence=s_int, wisdom=s_wis, charisma=s_cha,
        speed=speed, perception=s_wis,
        proficiencies=profs,
        traits=race_data.get("traits", []),
        spellbook=get_spellbook(session_id),
        bestiary=get_bestiary(session_id),
        lore_book=get_lore_book(session_id),
        available_stat_points=0,
        available_skill_points=0,
        gold=0, turn_number=1,
        location="tavern", location_name=loc["name"],
        inventory=[], quests=get_quests(session_id),
        x=0, y=0, surroundings=get_surroundings(session_id, 0, 0, radius=2),
        in_combat=0,
    )


@app.get("/session/{session_id}", response_model=SessionResponse)
async def resume_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    world = load_world()
    loc = world["locations"].get(session["location"], world["locations"]["tavern"])
    cx, cy = session.get("x", 0), session.get("y", 0)
    race_key = session.get("race", "Human").lower()
    traits = world["races"].get(race_key, {}).get("traits", [])

    return SessionResponse(
        session_id=session_id,
        archetype=session["archetype"],
        race=session.get("race", "Human"),
        character_name=session.get("character_name", "Adventurer"),
        hp=session["hp"],
        max_hp=session["max_hp"],
        mana=session["mana"],
        max_mana=session["max_mana"],
        strength=session.get("str", 10),
        dexterity=session.get("dex", 10),
        constitution=session.get("con", 10),
        intelligence=session.get("int", 10),
        wisdom=session.get("wis", 10),
        charisma=session.get("cha", 10),
        speed=session.get("speed", 30),
        perception=session.get("perception", 10),
        proficiencies=json.loads(session.get("proficiencies", "[]")),
        traits=traits,
        spellbook=get_spellbook(session_id),
        bestiary=get_bestiary(session_id),
        lore_book=get_lore_book(session_id),
        available_stat_points=session.get("available_stat_points", 0),
        available_skill_points=session.get("available_skill_points", 0),
        gold=session.get("gold", 0),
        alignment=session.get("alignment", 0),
        level=session.get("level", 1),
        xp=session.get("xp", 0),
        xp_to_next_level=session.get("xp_to_next_level", 100),
        turn_number=session["turn_number"],
        location=session["location"],
        location_name=loc["name"],
        inventory=get_inventory(session_id),
        quests=get_quests(session_id),
        companions=get_active_companions(session_id),
        x=cx, y=cy,
        surroundings=get_surroundings(session_id, cx, cy, radius=2),
        in_combat=session.get("in_combat", 0),
        enemy_name=session.get("enemy_name", ""),
        enemy_hp=session.get("enemy_hp", 0),
        enemy_max_hp=session.get("enemy_max_hp", 0),
    )


@app.post("/turn", response_model=TurnResponse)
async def take_turn(req: TurnRequest):
    world = load_world()
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Start a new game.")

    create_snapshot(req.session_id, session["turn_number"])

    archetype_key = session["archetype"]
    race = session.get("race", "Human")
    arch = world["archetypes"][archetype_key]
    hp = session["hp"]
    mana = session["mana"]
    gold = session.get("gold", 0)
    alignment = session.get("alignment", 0)
    s_str = session.get("str", 10)
    s_dex = session.get("dex", 10)
    s_con = session.get("con", 10)
    s_int = session.get("int", 10)
    s_wis = session.get("wis", 10)
    s_cha = session.get("cha", 10)
    speed = session.get("speed", 30)
    profs = json.loads(session.get("proficiencies", "[]"))
    spellbook = get_spellbook(req.session_id)
    level = session.get("level", 1)
    xp = session.get("xp", 0)
    xp_to_next_level = session.get("xp_to_next_level", 100)
    max_hp = session["max_hp"]
    max_mana = session["max_mana"]
    turn_number = session["turn_number"]
    location_key = session["location"]
    x, y = session.get("x", 0), session.get("y", 0)

    # Handle System Actions (Authoritative)
    if req.player_input.startswith("[SYSTEM_ACTION:"):
        action_parts = req.player_input.strip("[]").split("|")
        cmd = action_parts[0].replace("SYSTEM_ACTION:", "").strip()
        
        if cmd == "BUY":
            item_name = action_parts[1].strip()
            price = int(action_parts[2].strip())
            if gold >= price:
                gold -= price
                add_to_inventory(req.session_id, item_name)
                req.player_input = f"(System: Purchased {item_name} for {price} gold)"
            else:
                raise HTTPException(status_code=400, detail="Insufficient gold.")
                
        elif cmd == "USE":
            item_name = action_parts[1].strip()
            if "Health Potion" in item_name or "Bread" in item_name:
                heal_amt = 10 if "Potion" in item_name else 2
                hp = min(max_hp, hp + heal_amt)
                req.player_input = f"(System: Used {item_name}, restored {heal_amt} HP)"
            elif "Shadow-Wine" in item_name:
                mana = min(max_mana, mana + 5)
                hp = max(0, hp - 2)
                req.player_input = f"(System: Drank Shadow-Wine, +5 Mana, -2 HP)"
            
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE session_id = ? AND item_name = ?", (req.session_id, item_name))
                conn.execute("DELETE FROM inventory WHERE session_id = ? AND item_name = ? AND quantity <= 0", (req.session_id, item_name))

    # Fetch world state
    t_info = get_terrain_at(req.session_id, x, y)
    terrain = t_info["terrain_type"]
    poi_name = t_info["poi_name"]
    poi_desc = t_info["poi_description"]
    
    # vision_radius calc
    vision_radius = 2
    if int(get_flag(req.session_id, "far_sight_active") or "0") > 0:
        vision_radius = 5

    # Update Fog of War
    mark_area_explored(req.session_id, x, y, vision_radius)

    is_new_discovery = False
    if poi_name:
        if record_discovery(req.session_id, poi_name, poi_desc):
            is_new_discovery = True
            xp += 10
    
    surroundings = get_surroundings(req.session_id, x, y, radius=vision_radius)
    companions = get_active_companions(req.session_id)
    visible_objects = get_visible_objects(req.session_id, location_key)
    inventory = get_inventory(req.session_id)
    quests = get_quests(req.session_id)
    flags = get_all_flags(req.session_id)

    journal_content = read_journal_summary(max_turns=10)
    
    # Standard D&D Skill Map
    skill_mods = {
        "Athletics": (s_str-10)//2, "Acrobatics": (s_dex-10)//2, "Stealth": (s_dex-10)//2,
        "Arcana": (s_int-10)//2, "History": (s_int-10)//2, "Insight": (s_wis-10)//2,
        "Perception": (s_wis-10)//2, "Medicine": (s_wis-10)//2,
        "Persuasion": (s_cha-10)//2, "Intimidation": (s_cha-10)//2
    }
    # Apply Proficiencies (+2)
    for p in profs:
        if p in skill_mods: skill_mods[p] += 2

    system_prompt = build_system_prompt(
        world, archetype_key, race, session.get("character_name", "Adventurer"), hp, mana, alignment, s_cha, speed, s_wis, level, xp, xp_to_next_level,
        location_key, x, y, terrain, poi_name, poi_desc, is_new_discovery, surroundings, companions,
        journal_content, visible_objects, inventory,
        quests=quests, flags=flags,
    )
    # Add specific D&D context to prompt
    dnd_context = f"\nPLAYER D&D STATS: STR:{s_str}, DEX:{s_dex}, CON:{s_con}, INT:{s_int}, WIS:{s_wis}, CHA:{s_cha}\nPROFICIENCIES: {', '.join(profs)}\nSPELLBOOK: {', '.join([s['spell_name'] for s in spellbook])}"
    active_spells = []
    if vision_radius > 2: active_spells.append("Far Sight (Active)")
    if int(get_flag(req.session_id, "feather_fall_active") or "0") > 0: active_spells.append("Feather Fall (Active)")
    if active_spells: dnd_context += f"\nACTIVE SPELL EFFECTS: {', '.join(active_spells)}"
    
    system_prompt += dnd_context

    narration = await call_ollama(system_prompt, req.player_input)
    narration = re.sub(r"^(Dungeon Master|DM):\s*", "", narration, flags=re.IGNORECASE)
    narration = re.sub(r"^\*\*DM:\*\*\s*", "", narration, flags=re.IGNORECASE)

    roll_result = None
    roll_requests = parse_roll_requests(narration)
    if roll_requests:
        skill_name = roll_requests[0]
        modifier = skill_mods.get(skill_name, 0)
        
        # Save pending roll state
        update_session(req.session_id, pending_roll_skill=skill_name, pending_roll_modifier=modifier)
        
        # Strip the tag but don't do follow-up yet
        clean_narration = re.sub(r"\[ROLL:\s*[^\]]+\]", "", narration).strip()
        
        return TurnResponse(
            narration=clean_narration, roll_result=None, pending_roll=PendingRoll(skill=skill_name, modifier=modifier),
            journal_entry="",
            hp=hp, max_hp=max_hp, mana=mana, max_mana=max_mana,
            strength=s_str, dexterity=s_dex, constitution=s_con, 
            intelligence=s_int, wisdom=s_wis, charisma=s_cha,
            speed=speed, perception=s_wis,
            proficiencies=profs, traits=traits, spellbook=spellbook,
            bestiary=get_bestiary(req.session_id),
            lore_book=get_lore_book(req.session_id),
            available_stat_points=stat_pts, available_skill_points=skill_pts,
            gold=gold, alignment=alignment, level=level, xp=xp, xp_to_next_level=xp_to_next_level,
            turn_number=turn_number, location=location_key, location_name=loc["name"],
            inventory=get_inventory(req.session_id), quests=get_quests(req.session_id),
            companions=companions, x=x, y=y,
            terrain=terrain, poi_name=poi_name, surroundings=get_surroundings(req.session_id, x, y, radius=vision_radius),
            in_combat=session.get("in_combat", 0),
            enemy_name=session.get("enemy_name", ""),
            enemy_hp=session.get("enemy_hp", 0),
            enemy_max_hp=session.get("enemy_max_hp", 0),
            npc_image=npc_image, race=race,
            character_name=session.get("character_name", "Adventurer")
        )

    tags = parse_stat_tags(narration)
    rest_match = re.search(r"\[REST:\s*(short|long)\]", narration)
    forge_matches = list(re.finditer(r"\[FORGE:\s*([^\]]+)\]", narration))
    narration = strip_stat_tags(narration)

    hp = max(0, min(max_hp, hp - tags["damage"] + tags["heal"]))
    if max_mana > 0:
        mana = max(0, min(max_mana, mana - tags["mana"]))
    
    alignment = max(-100, min(100, alignment + tags["alignment"]))
    xp += tags["xp"]
    stat_pts = session.get("available_stat_points", 0)
    skill_pts = session.get("available_skill_points", 0)
    
    if xp >= xp_to_next_level:
        level += 1
        xp -= xp_to_next_level
        xp_to_next_level = int(xp_to_next_level * 1.5)
        
        # Grant D&D Style ASI (2 points) and 1 Skill point
        stat_pts += 2
        skill_pts += 1
        
        # Automatic Max HP Increase: Class Hit Die + Con Mod
        hit_die = {"warrior": 10, "rogue": 8, "mage": 6}.get(archetype_key, 8)
        con_mod = (s_con - 10) // 2
        hp_increase = max(1, hit_die + con_mod)
        max_hp += hp_increase
        hp = max_hp
        
        narration += f"\n\n🌟 LEVEL UP! You are now level {level}! (+{hp_increase} Max HP, +2 Stat Points, +1 Skill Point)"

    # Apply Loot
    loot_data = json.loads(LOOT_PATH.read_text())
    for tier in tags.get("loot_tiers", []):
        actual_tier = tier
        if actual_tier == 3 and random.random() < 0.10: actual_tier = 4
        t_str = str(actual_tier)
        if t_str in loot_data["tiers"]:
            t_cfg = loot_data["tiers"][t_str]
            g_gain = random.randint(t_cfg["gold_range"][0], t_cfg["gold_range"][1])
            gold += g_gain
            item_chance = 0.8 if t_cfg.get("is_legendary") else 0.5
            if random.random() < item_chance:
                item = random.choice(t_cfg["items"])
                add_to_inventory(req.session_id, item["name"])
                narration += f"\n\n(Loot: {item['name']} and {g_gain} gold!)"
            else:
                narration += f"\n\n(Loot: {g_gain} gold!)"

    # Sync Named Location
    LOCATION_MAP = {"tavern": (0, 0), "vault_entrance": (10, 10), "swamp_hut": (5, 5), "shadow_camp": (3, 8)}
    if tags["move_to"] and tags["move_to"] in world["locations"]:
        location_key = tags["move_to"]
        x, y = LOCATION_MAP.get(location_key, (x, y))
        new_loc = world["locations"][location_key]
        if "encounter" in new_loc and not session.get("in_combat", 0):
            enc = new_loc["encounter"]
            update_session(req.session_id, in_combat=1, enemy_name=enc["name"], enemy_hp=enc["hp"], enemy_max_hp=enc["hp"], enemy_ac=enc.get("ac", 11), enemy_atk_bonus=enc.get("attack_bonus", 2))

    # Apply coordinate move
    if tags["move_coords"]:
        nx, ny = tags["move_coords"]
        if max(abs(nx - x), abs(ny - y)) <= 1:
            new_terrain_info = get_terrain_at(req.session_id, nx, ny)
            new_terrain = new_terrain_info["terrain_type"]
            if new_terrain not in ["Mountain", "Water", "Unknown"]:
                x, y = nx, ny
                if new_terrain == "Swamp": hp = max(0, hp - 2)

    # Enemy Spawning
    for enemy in tags.get("spawn_enemies", []):
        update_session(req.session_id, in_combat=1, enemy_name=enemy["name"], enemy_hp=enemy["hp"], enemy_max_hp=enemy["hp"], enemy_ac=enemy["ac"], enemy_atk_bonus=enemy["atk"])

    for item in tags["get_items"]: pick_up_object(req.session_id, item) or add_to_inventory(req.session_id, item)
    for s in tags["spawn_items"]: spawn_object(req.session_id, s["name"], s["description"], s["location"], s["portable"])
    for c in tags["companion_joins"]: add_companion(req.session_id, c["name"], c["archetype"], c["hp"])
    for d in tags["companion_dmg"]: update_companion_hp(req.session_id, d["name"], d["amount"])
    for key, val in tags["flags"].items(): set_flag(req.session_id, key, val)
    for qid, status in tags["quest_updates"].items(): set_quest(req.session_id, qid, status)

    # REST handling
    if rest_match:
        rtype = rest_match.group(1).lower()
        if rtype == "short":
            hp_gain = (max_hp - hp) // 2
            mana_gain = (max_mana - mana) // 2
            hp = min(max_hp, hp + hp_gain)
            mana = min(max_mana, mana + mana_gain)
            narration += f"\n\n(Short Rest: Restored {hp_gain} HP and {mana_gain} Mana.)"
        else:
            if location_key != "tavern" and random.random() < 0.20:
                hp = max_hp // 2
                mana = max_mana // 2
                narration += "\n\n⚠️ AMBUSH! You were attacked in your sleep! You wake up exhausted and wounded."
                enc = _random_encounter_for_terrain(terrain)
                if enc:
                    update_session(req.session_id, in_combat=1, enemy_name=enc["name"], enemy_hp=enc["hp"], enemy_max_hp=enc["hp"], enemy_ac=enc.get("ac", 11), enemy_atk_bonus=enc.get("attack_bonus", 2))
            else:
                hp = max_hp
                mana = max_mana
                narration += "\n\n(Long Rest: All stats fully restored.)"

    # FORGE handling
    for m in forge_matches:
        wpn_name = m.group(1).strip()
        d1, d2 = roll_dn(20), roll_dn(20)
        total = d1 + d2
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            wpn = conn.execute("SELECT * FROM inventory WHERE session_id = ? AND item_name = ? AND is_weapon = 1", (req.session_id, wpn_name)).fetchone()
            if wpn:
                if total >= 30:
                    new_lvl = wpn["upgrade_level"] + 1
                    conn.execute("UPDATE inventory SET upgrade_level = ?, max_durability = max_durability + 20, durability = max_durability + 20 WHERE id = ?", (new_lvl, wpn["id"]))
                    narration += f"\n\n🛠️ FORGE SUCCESS! {wpn_name} is now +{new_lvl}! (Rolled {total}: {d1}+{d2})"
                elif total >= 15:
                    new_lvl = wpn["upgrade_level"] + 1
                    conn.execute("UPDATE inventory SET upgrade_level = ? WHERE id = ?", (new_lvl, wpn["id"]))
                    narration += f"\n\n🛠️ FORGE SUCCESS! {wpn_name} is now +{new_lvl}. (Rolled {total}: {d1}+{d2})"
                else:
                    conn.execute("UPDATE inventory SET durability = max(0, durability - 20) WHERE id = ?", (wpn["id"],))
                    narration += f"\n\n🛠️ FORGE FAIL! The metal screams under the hammer. {wpn_name} lost durability. (Rolled {total}: {d1}+{d2})"

    # Tactical Environment
    for m in re.finditer(r"\[BREAK:\s*([^\]]+)\]", narration):
        obj_name = m.group(1).strip()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE world_objects SET state = 'broken' WHERE session_id = ? AND object_name = ?", (req.session_id, obj_name))
            if "Oil" in obj_name:
                conn.execute("UPDATE world_map SET state = 'slippery_oil', state_turns = 5 WHERE session_id = ? AND x = ? AND y = ?", (req.session_id, x, y))

    for m in re.finditer(r"\[TILE_STATE:\s*([^\]]+)\]", narration):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 4:
            tx, ty, tstate, tturns = int(parts[0]), int(parts[1]), parts[2], int(parts[3])
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE world_map SET state = ?, state_turns = ? WHERE session_id = ? AND x = ? AND y = ?", (tstate, tturns, req.session_id, tx, ty))

    for m in re.finditer(r"\[PUSH:\s*([^\]]+)\]", narration):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 3:
            obj_name, tx, ty = parts[0], int(parts[1]), int(parts[2])
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE world_objects SET location = 'grid', x = ?, y = ? WHERE session_id = ? AND object_name = ?", (tx, ty, req.session_id, obj_name))

    # NPC Image Generation Disabled
    npc_image = ""
    loc = world["locations"].get(location_key, world["locations"]["tavern"])
    
    for item in tags["get_items"]: pick_up_object(req.session_id, item) or add_to_inventory(req.session_id, item)
    for s in tags["spawn_items"]: spawn_object(req.session_id, s["name"], s["description"], s["location"], s["portable"])
    for c in tags["companion_joins"]: add_companion(req.session_id, c["name"], c["archetype"], c["hp"])
    for d in tags["companion_dmg"]: update_companion_hp(req.session_id, d["name"], d["amount"])
    for key, val in tags["flags"].items(): set_flag(req.session_id, key, val)
    for qid, status in tags["quest_updates"].items(): set_quest(req.session_id, qid, status)

    # Spell Handling
    for sname in tags.get("cast_spells", []):
        if sname in world["spells"]:
            sdef = world["spells"][sname]
            cost = sdef.get("mana", 0)
            if mana >= cost:
                mana -= cost
                narration += f"\n\n✨ YOU CAST: {sname}!"
                if sname == "Far Sight":
                    set_flag(req.session_id, "far_sight_active", "3") # Active for 3 turns
                elif sname == "Feather Fall":
                    set_flag(req.session_id, "feather_fall_active", "5")
            else:
                narration += f"\n\n❌ FAILD TO CAST: {sname} (Not enough Mana!)"

    # Tick down active spell flags
    fs_turns = int(get_flag(req.session_id, "far_sight_active") or "0")
    if fs_turns > 0: set_flag(req.session_id, "far_sight_active", str(fs_turns - 1))
    
    ff_turns = int(get_flag(req.session_id, "feather_fall_active") or "0")
    if ff_turns > 0: set_flag(req.session_id, "feather_fall_active", str(ff_turns - 1))

    _advance_quests(req.session_id, world)

    if moved_coord := (tags["move_coords"] and (x != session.get("x", 0) or y != session.get("y", 0))):
        # Resource Gathering
        material_found = None
        gather_roll = random.random()
        if gather_roll < 0.20: # 20% chance to find materials
            terrain_materials = {
                "Mountain": "Iron Ore",
                "Swamp": "Ancient Scrap",
                "Woodland": "Thick Leather",
                "Path": "Iron Scraps",
                "Water": "Arcane Dust"
            }
            mat = terrain_materials.get(terrain)
            if mat:
                add_to_inventory(req.session_id, mat)
                material_found = mat
                narration += f"\n\n🛠️ GATHERED: You found some {mat} while traveling."

        if not session.get("in_combat", 0):
            if (enc := _random_encounter_for_terrain(get_terrain_at(req.session_id, x, y)["terrain_type"], level)) and random.random() < 0.15:
                update_session(req.session_id, in_combat=1, enemy_name=enc["name"], enemy_hp=enc["hp"], enemy_max_hp=enc["hp"], enemy_ac=enc.get("ac", 11), enemy_atk_bonus=enc.get("attack_bonus", 2))

    new_turn = turn_number + 1
    update_session(req.session_id, hp=hp, max_hp=max_hp, mana=mana, gold=gold, alignment=alignment, level=level, xp=xp, xp_to_next_level=xp_to_next_level, turn_number=new_turn, location=location_key, x=x, y=y, npc_image=npc_image, available_stat_points=stat_pts, available_skill_points=skill_pts)
    append_journal(f"**Player:** {req.player_input}\n**DM:** {narration}", turn_number)

    race_key = race.lower()
    traits = world["races"].get(race_key, {}).get("traits", [])

    return TurnResponse(
        narration=narration, roll_result=roll_result, journal_entry="",
        hp=hp, max_hp=max_hp, mana=mana, max_mana=max_mana,
        strength=s_str, dexterity=s_dex, constitution=s_con, 
        intelligence=s_int, wisdom=s_wis, charisma=s_cha,
        speed=speed, perception=s_wis,
        proficiencies=profs,
        traits=traits,
        spellbook=spellbook,
        bestiary=get_bestiary(req.session_id),
        lore_book=get_lore_book(req.session_id),
        available_stat_points=stat_pts,
        available_skill_points=skill_pts,
        gold=gold, 
        alignment=alignment, level=level, xp=xp, xp_to_next_level=xp_to_next_level,
        turn_number=new_turn, location=location_key, location_name=loc["name"],
        inventory=get_inventory(req.session_id), quests=get_quests(req.session_id),
        companions=get_active_companions(req.session_id), x=x, y=y,
        terrain=terrain, poi_name=poi_name, surroundings=get_surroundings(req.session_id, x, y, radius=2),
        in_combat=get_session(req.session_id).get("in_combat", 0),
        enemy_name=get_session(req.session_id).get("enemy_name", ""),
        enemy_hp=get_session(req.session_id).get("enemy_hp", 0),
        enemy_max_hp=get_session(req.session_id).get("enemy_max_hp", 0),
        npc_image=npc_image,
        race=race,
        character_name=session.get("character_name", "Adventurer")
    )


@app.post("/session/roll", response_model=TurnResponse)
async def submit_roll(req: RollSubmissionRequest):
    world = load_world()
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 1. Prepare context (mostly copied from take_turn)
    # Using session data directly
    s_str, s_dex, s_con = session.get("str", 10), session.get("dex", 10), session.get("con", 10)
    s_int, s_wis, s_cha = session.get("int", 10), session.get("wis", 10), session.get("cha", 10)
    
    archetype_key = session["archetype"]
    race = session.get("race", "Human")
    hp, max_hp = session["hp"], session["max_hp"]
    mana, max_mana = session["mana"], session["max_mana"]
    gold = session.get("gold", 0)
    alignment = session.get("alignment", 0)
    level = session.get("level", 1)
    xp = session.get("xp", 0)
    xp_to_next_level = session.get("xp_to_next_level", 100)
    turn_number = session["turn_number"]
    location_key = session["location"]
    x, y = session.get("x", 0), session.get("y", 0)
    
    # Vision
    vision_radius = 2
    if int(get_flag(req.session_id, "far_sight_active") or "0") > 0:
        vision_radius = 5

    # Update Fog of War
    mark_area_explored(req.session_id, x, y, vision_radius)

    # Surroundings/Inventory/etc
    surroundings = get_surroundings(req.session_id, x, y, radius=vision_radius)
    t_info = get_terrain_at(req.session_id, x, y)
    terrain, poi_name, poi_desc = t_info["terrain_type"], t_info["poi_name"], t_info["poi_description"]
    
    if poi_name:
        if record_discovery(req.session_id, poi_name, poi_desc):
            xp += 10
    
    companions = get_active_companions(req.session_id)
    visible_objects = get_visible_objects(req.session_id, location_key)
    inventory = get_inventory(req.session_id)
    quests = get_quests(req.session_id)
    flags = get_all_flags(req.session_id)
    profs = json.loads(session.get("proficiencies", "[]"))
    spellbook = get_spellbook(req.session_id)

    # 2. Build follow-up prompt
    system_prompt = build_system_prompt(
        world, archetype_key, race, session.get("character_name", "Adventurer"), hp, mana, alignment, s_cha, 30, s_wis, level, xp, xp_to_next_level,
        location_key, x, y, terrain, poi_name, poi_desc, False, surroundings, companions,
        read_journal_summary(max_turns=10), visible_objects, inventory,
        quests=quests, flags=flags,
    )
    
    # 3. Create the roll result context
    # Calculate modifiers for display (D&D standard: (Stat-10)/2)
    # Note: req.modifier already includes proficiency if applicable from take_turn
    roll_val = req.roll_total - req.modifier
    roll_result = RollResult(roll=roll_val, modifier=req.modifier, total=req.roll_total, description=f"{roll_val}+{req.modifier}={req.roll_total}")
    
    roll_context = f"The player attempted a {req.skill} check and rolled: {roll_result.description}. Continue narration based on this result."
    
    narration = await call_ollama(system_prompt, roll_context)
    narration = re.sub(r"^(Dungeon Master|DM):\s*", "", narration, flags=re.IGNORECASE)
    narration = re.sub(r"^\*\*DM:\*\*\s*", "", narration, flags=re.IGNORECASE)

    # 4. Parse follow-up tags
    tags = parse_stat_tags(narration)
    narration = strip_stat_tags(narration)

    # Apply tag effects
    hp = max(0, min(max_hp, hp - tags["damage"] + tags["heal"]))
    if max_mana > 0:
        mana = max(0, min(max_mana, mana - tags["mana"]))
    alignment = max(-100, min(100, alignment + tags["alignment"]))
    xp += tags["xp"]
    
    # Level up check (copy-pasted for simplicity, should be a helper)
    stat_pts = session.get("available_stat_points", 0)
    skill_pts = session.get("available_skill_points", 0)
    if xp >= xp_to_next_level:
        level += 1; xp -= xp_to_next_level; xp_to_next_level = int(xp_to_next_level * 1.5)
        stat_pts += 2; skill_pts += 1
        hit_die = {"warrior": 10, "rogue": 8, "mage": 6}.get(archetype_key, 8)
        hp_inc = max(1, hit_die + ((s_con - 10) // 2))
        max_hp += hp_inc; hp = max_hp
        narration += f"\n\n🌟 LEVEL UP! You are now level {level}!"

    for item in tags["get_items"]: pick_up_object(req.session_id, item) or add_to_inventory(req.session_id, item)
    for key, val in tags["flags"].items(): set_flag(req.session_id, key, val)
    # Clear pending roll
    update_session(req.session_id, pending_roll_skill=None, pending_roll_modifier=0, last_roll_total=req.roll_total)
    
    new_turn = turn_number + 1
    update_session(req.session_id, hp=hp, max_hp=max_hp, mana=mana, level=level, xp=xp, xp_to_next_level=xp_to_next_level, turn_number=new_turn, last_roll_total=req.roll_total, available_stat_points=stat_pts, available_skill_points=skill_pts)
    append_journal(f"**Roll ({req.skill}):** {roll_result.description}\n**DM:** {narration}", turn_number)

    loc = world["locations"].get(location_key, world["locations"]["tavern"])
    return TurnResponse(
        narration=narration, roll_result=roll_result, pending_roll=None,
        hp=hp, max_hp=max_hp, mana=mana, max_mana=max_mana,
        strength=s_str, dexterity=s_dex, constitution=s_con, 
        intelligence=s_int, wisdom=s_wis, charisma=s_cha,
        speed=session.get("speed", 30), perception=s_wis,
        proficiencies=profs, traits=race_data_traits(world, race), spellbook=spellbook,
        bestiary=get_bestiary(req.session_id),
        lore_book=get_lore_book(req.session_id),
        available_stat_points=stat_pts, available_skill_points=skill_pts,
        gold=gold, alignment=alignment, level=level, xp=xp, xp_to_next_level=xp_to_next_level,
        turn_number=new_turn, location=location_key, location_name=loc["name"],
        inventory=get_inventory(req.session_id), quests=get_quests(req.session_id),
        companions=companions, x=x, y=y,
        terrain=terrain, poi_name=poi_name, surroundings=get_surroundings(req.session_id, x, y, radius=vision_radius),
        in_combat=session.get("in_combat", 0),
        enemy_name=session.get("enemy_name", ""),
        enemy_hp=session.get("enemy_hp", 0),
        enemy_max_hp=session.get("enemy_max_hp", 0),
        npc_image=session.get("npc_image", ""), race=race,
        character_name=session.get("character_name", "Adventurer")
    )

def race_data_traits(world, race):
    return world["races"].get(race.lower(), {}).get("traits", [])


@app.post("/session/undo", response_model=SessionResponse)
async def undo_turn(req: UndoRequest):
    # 1. Peek at current state before undoing to check for "scumming"
    current = get_session(req.session_id)
    jester_msg = None
    
    if current:
        last_roll = current.get("last_roll_total", 10)
        # If player undoes a low roll or a death/near-death
        if last_roll < 10 or current["hp"] <= 5:
            quotes = [
                "Back so soon? I could have sworn I saw you falling into that pit... must be the ale playing tricks on my eyes.",
                "A curious ripple in the song of your life... almost as if the strings were plucked backwards. Shall we try that verse again?",
                "The Fates have a sense of humor today, it seems. Averting destiny, are we? Fine, let's pretend that never happened.",
                "Wait, didn't you just die? No? Ah, the 'Chrono-Flu' must be hitting me hard today.",
                "Rewinding time again? Careful, hero. Do it too much and you might wake up as a garden gnome."
            ]
            jester_msg = random.choice(quotes)

    if not restore_snapshot(req.session_id, req.target_turn): raise HTTPException(status_code=400, detail="Undo failed")
    s = get_session(req.session_id)
    world = load_world()
    loc = world["locations"].get(s["location"], world["locations"]["tavern"])
    return SessionResponse(
        session_id=req.session_id, archetype=s["archetype"], race=s.get("race", "Human"), 
        character_name=s.get("character_name", "Adventurer"),
        hp=s["hp"], max_hp=s["max_hp"],
        mana=s["mana"], max_mana=s["max_mana"], 
        strength=s.get("str", 10), dexterity=s.get("dex", 10), constitution=s.get("con", 10),
        intelligence=s.get("int", 10), wisdom=s.get("wis", 10), charisma=s.get("cha", 10),
        speed=s.get("speed", 30), perception=s.get("perception", 10), 
        proficiencies=json.loads(s.get("proficiencies", "[]")),
        traits=world["races"].get(s.get("race", "Human").lower(), {}).get("traits", []),
        spellbook=get_spellbook(req.session_id),
        available_stat_points=s.get("available_stat_points", 0),
        available_skill_points=s.get("available_skill_points", 0),
        pending_roll=None,
        jester_msg=jester_msg,
        bestiary=get_bestiary(req.session_id),
        lore_book=get_lore_book(req.session_id),
        gold=s["gold"], alignment=s.get("alignment", 0),
        level=s.get("level", 1), xp=s.get("xp", 0), xp_to_next_level=s.get("xp_to_next_level", 100),
        turn_number=s["turn_number"],
        location=s["location"], location_name=loc["name"], inventory=get_inventory(req.session_id),
        quests=get_quests(req.session_id), companions=get_active_companions(req.session_id),
        x=s["x"], y=s["y"], surroundings=get_surroundings(req.session_id, s["x"], s["y"], radius=2),
        in_combat=s["in_combat"], enemy_name=s["enemy_name"], enemy_hp=s["enemy_hp"], enemy_max_hp=s["enemy_max_hp"],
    )


class LevelUpRequest(BaseModel):
    session_id: str
    stat_to_increase: str | None = None  # "strength", "dexterity", etc.
    skill_to_learn: str | None = None


class ForgeRequest(BaseModel):
    session_id: str
    item_id: int
    material_name: str
    action: str  # "repair" or "upgrade"


class HireRequest(BaseModel):
    session_id: str
    npc_name: str


class ExportResponse(BaseModel):
    title: str
    stats: dict
    journal: str
    lore: list
    bestiary: list
    timestamp: str


@app.post("/session/level-up", response_model=SessionResponse)
async def level_up(req: LevelUpRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    stat_pts = session.get("available_stat_points", 0)
    skill_pts = session.get("available_skill_points", 0)
    
    updates = {}
    
    if req.stat_to_increase:
        if stat_pts <= 0:
            raise HTTPException(status_code=400, detail="No stat points available")
        
        # Map frontend names to DB names if necessary, but here they match or are handled
        stat_map = {
            "strength": "str", "dexterity": "dex", "constitution": "con",
            "intelligence": "int", "wisdom": "wis", "charisma": "cha"
        }
        db_col = stat_map.get(req.stat_to_increase.lower())
        if not db_col:
            raise HTTPException(status_code=400, detail="Invalid stat name")
        
        updates[db_col] = session.get(db_col, 10) + 1
        updates["available_stat_points"] = stat_pts - 1
        
        # If CON increased, increase Max HP
        if db_col == "con":
            updates["max_hp"] = session["max_hp"] + 1
            updates["hp"] = session["hp"] + 1

    if req.skill_to_learn:
        if skill_pts <= 0:
            raise HTTPException(status_code=400, detail="No skill points available")
        
        profs = json.loads(session.get("proficiencies", "[]"))
        if req.skill_to_learn in profs:
            raise HTTPException(status_code=400, detail="Skill already known")
        
        profs.append(req.skill_to_learn)
        updates["proficiencies"] = json.dumps(profs)
        updates["available_skill_points"] = skill_pts - 1

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    update_session(req.session_id, **updates)
    return await resume_session(req.session_id)


@app.post("/session/forge", response_model=SessionResponse)
async def forge_item(req: ForgeRequest):
    session = get_session(req.session_id)
    if not session: raise HTTPException(status_code=404, detail="Session not found")
    
    material = get_inventory_item(req.session_id, req.material_name)
    if not material or material["quantity"] <= 0:
        raise HTTPException(status_code=400, detail=f"Insufficient {req.material_name}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        item = conn.execute("SELECT * FROM inventory WHERE id = ? AND session_id = ?", (req.item_id, req.session_id)).fetchone()
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        
        # Consume material
        conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (material["id"],))
        conn.execute("DELETE FROM inventory WHERE id = ? AND quantity <= 0", (material["id"],))
        
        if req.action == "repair":
            conn.execute("UPDATE inventory SET durability = MIN(max_durability, durability + 50) WHERE id = ?", (req.item_id,))
        elif req.action == "upgrade":
            # Costs gold too? Let's say 50 gold
            if session["gold"] < 50: raise HTTPException(status_code=400, detail="Need 50 gold to upgrade")
            conn.execute("UPDATE sessions SET gold = gold - 50 WHERE id = ?", (req.session_id,))
            conn.execute("UPDATE inventory SET upgrade_level = upgrade_level + 1 WHERE id = ?", (req.item_id,))
        
        conn.commit()
    
    return await resume_session(req.session_id)


@app.post("/session/hire", response_model=SessionResponse)
async def hire_npc(req: HireRequest):
    session = get_session(req.session_id)
    if not session: raise HTTPException(status_code=404, detail="Session not found")
    
    world = load_world()
    loc = world["locations"].get(session["location"])
    if not loc or "npc" not in loc or loc["npc"]["name"] != req.npc_name:
        raise HTTPException(status_code=400, detail="NPC not here")
    
    npc = loc["npc"]
    if session["gold"] < 100:
        raise HTTPException(status_code=400, detail="Not enough gold (Hiring costs 100g)")
    
    add_companion(req.session_id, npc["name"], npc.get("archetype", "warrior"), npc.get("hp", 20))
    update_session(req.session_id, gold=session["gold"] - 100)
    
    return await resume_session(req.session_id)


@app.get("/session/export/{session_id}", response_model=ExportResponse)
async def export_legend(session_id: str):
    session = get_session(session_id)
    if not session: raise HTTPException(status_code=404, detail="Session not found")
    
    return ExportResponse(
        title=f"The Legend of {session.get('character_name', 'Adventurer')}",
        stats={
            "Level": session["level"],
            "Class": f"{session['race']} {session['archetype'].title()}",
            "Gold": session["gold"],
            "Alignment": session["alignment"]
        },
        journal=read_journal(),
        lore=get_lore_book(session_id),
        bestiary=get_bestiary(session_id),
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/journal")
async def get_journal():
    return {"content": read_journal()}


@app.post("/combat/action", response_model=CombatResponse)
async def combat_action(req: CombatActionRequest):
    world = load_world()
    session = get_session(req.session_id)
    if not session or not session.get("in_combat", 0): raise HTTPException(status_code=400, detail="Combat session not found")

    arch = world["archetypes"][session["archetype"]]
    hp = session["hp"]; max_hp = session["max_hp"]; xp = session.get("xp", 0); level = session.get("level", 1)
    enemy_hp = session["enemy_hp"]; enemy_max_hp = session["enemy_max_hp"]; enemy_name = session["enemy_name"]
    enemy_ac = session.get("enemy_ac", 11); enemy_atk = session.get("enemy_atk_bonus", 2)
    player_ac = 10; inventory = get_inventory(req.session_id)

    action = req.action.lower()
    player_roll = 0; player_hit = False; player_damage = 0
    enemy_roll = 0; enemy_hit = False; enemy_damage = 0
    fled = False; flee_success = False
    defending = (action == "defend")
    summary = ""

    # Weapon Stats
    wpn_bonus = 0
    equipped_wpn = None
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        equipped_wpn = conn.execute("SELECT * FROM inventory WHERE session_id = ? AND is_weapon = 1", (req.session_id,)).fetchone()
        if equipped_wpn: wpn_bonus = equipped_wpn["upgrade_level"]

    if action == "flee":
        fled = True; player_roll = roll_dn(20); flee_success = player_roll >= 12
        if not flee_success: enemy_damage = roll_dn(4); hp = max(0, hp - enemy_damage)
    else:
        player_roll = roll_dn(20) + arch.get("attack_modifier", 0) + wpn_bonus
        player_hit = player_roll >= enemy_ac
        if player_hit:
            # Durability Check
            if equipped_wpn:
                new_dur = equipped_wpn["durability"] - 5
                with sqlite3.connect(DB_PATH) as conn:
                    if new_dur <= 0:
                        conn.execute("DELETE FROM inventory WHERE id = ?", (equipped_wpn["id"],))
                        summary += f" YOUR {equipped_wpn['item_name'].upper()} SHATTERED!"
                    else:
                        conn.execute("UPDATE inventory SET durability = ? WHERE id = ?", (new_dur, equipped_wpn["id"]))
                    conn.commit()

            player_damage = roll_dn(6) + max(0, arch["skills"].get("Strength", 0)) + wpn_bonus
            enemy_hp = max(0, enemy_hp - player_damage)

        if enemy_hp > 0:
            enemy_roll = roll_dn(20) + enemy_atk; eff_ac = player_ac + (2 if defending else 0)
            enemy_hit = enemy_roll >= eff_ac
            if enemy_hit: raw = roll_dn(4); enemy_damage = raw // 2 if defending else raw; hp = max(0, hp - enemy_damage)

    victory = (enemy_hp <= 0); defeat = (hp <= 0)
    in_combat = 0 if (victory or defeat or flee_success) else 1

    if victory:
        xp += 25
        if xp >= session["xp_to_next_level"]:
            level += 1
            xp -= session["xp_to_next_level"]
            session["xp_to_next_level"] = int(session["xp_to_next_level"] * 1.5)
            hp = max_hp

    companions = get_active_companions(req.session_id); companion_actions = []
    if not fled and enemy_hp > 0:
        for comp in companions:
            stats = COMPANION_ARCHETYPES.get(comp["archetype"], COMPANION_ARCHETYPES["default"])
            c_roll = roll_dn(20) + stats["attack_bonus"]; c_hit = c_roll >= enemy_ac; c_dmg = 0
            if c_hit and enemy_hp > 0: c_dmg = roll_dn(stats["damage_die"]) + stats["str_mod"]; enemy_hp = max(0, enemy_hp - c_dmg)
            companion_actions.append(CompanionAction(name=comp["name"], roll=c_roll, hit=c_hit, damage=c_dmg, knocked_out=(comp["hp"] <= 0)))
        victory = (enemy_hp <= 0); in_combat = 0 if (victory or defeat or flee_success) else 1

    enemy_targeted_companion = ""; enemy_companion_damage = 0
    if not fled and not victory and not defeat and companions and enemy_hit:
        if random.random() < 0.3:
            target = random.choice(companions); enemy_targeted_companion = target["name"]; enemy_companion_damage = enemy_damage
            update_companion_hp(req.session_id, target["name"], enemy_damage); hp = session["hp"]; enemy_hit = False; enemy_damage = 0

    loot_items = []
    if victory:
        loot_items = roll_loot(enemy_name)
        for ln in loot_items: add_to_inventory(req.session_id, ln)
        set_flag(req.session_id, enemy_name.lower().replace(" ", "_") + "_defeated", "1")
        record_monster_kill(req.session_id, enemy_name, level)
        _advance_quests(req.session_id, world); inventory = get_inventory(req.session_id)

    summary = f"Combat: player {action}. P-Atk: {player_roll} vs {enemy_ac}. E-HP: {enemy_hp}/{enemy_max_hp}. "
    if victory: summary += f"VICTORY. Loot: {', '.join(loot_items)}."
    if defeat: summary += "DEFEAT."

    sys_p = build_system_prompt(
        world, session["archetype"], session.get("race", "Human"), session.get("character_name", "Adventurer"),
        hp, session["mana"], session.get("alignment", 0), 
        session.get("cha", 10), session.get("speed", 30), session.get("wis", 10),
        level, xp, session.get("xp_to_next_level", 100),
        session["location"], session["x"], session["y"], 
        get_terrain_at(req.session_id, session["x"], session["y"])["terrain_type"], 
        "", "", False, 
        get_surroundings(req.session_id, session["x"], session["y"], radius=2), 
        get_active_companions(req.session_id), read_journal_summary(10), 
        get_visible_objects(req.session_id, session["location"]), inventory
    )
    narration = strip_stat_tags(await call_ollama(sys_p, summary))

    update_session(req.session_id, hp=hp, xp=xp, level=level, turn_number=session["turn_number"]+1, in_combat=in_combat, enemy_hp=enemy_hp if in_combat else 0, enemy_name=enemy_name if in_combat else "", enemy_max_hp=enemy_max_hp if in_combat else 0)
    append_journal(f"**Combat:** {action}\n**DM:** {narration}", session["turn_number"])

    loc = world["locations"].get(session["location"], world["locations"]["tavern"])
    return CombatResponse(
        narration=narration, 
        combat_round=CombatRound(action=action, player_roll=player_roll, player_hit=player_hit, player_damage=player_damage, enemy_roll=enemy_roll, enemy_hit=enemy_hit, enemy_damage=enemy_damage, fled=fled, flee_success=flee_success, companion_actions=companion_actions, enemy_targeted_companion=enemy_targeted_companion, enemy_companion_damage=enemy_companion_damage), 
        hp=hp, max_hp=max_hp, 
        mana=session.get("mana", 0), max_mana=session.get("max_mana", 0),
        enemy_hp=enemy_hp, enemy_max_hp=enemy_max_hp, enemy_name=enemy_name, 
        in_combat=in_combat, turn_number=session["turn_number"]+1, 
        location=session["location"], location_name=loc["name"], 
        inventory=inventory, quests=get_quests(req.session_id), 
        companions=get_active_companions(req.session_id), 
        victory=victory, defeat=defeat,
        archetype=session["archetype"], race=session.get("race", "Human"),
        character_name=session.get("character_name", "Adventurer"),
        strength=session.get("str", 10), dexterity=session.get("dex", 10), constitution=session.get("con", 10),
        intelligence=session.get("int", 10), wisdom=session.get("wis", 10), charisma=session.get("cha", 10),
        speed=session.get("speed", 10), perception=session.get("perception", 10),
        proficiencies=json.loads(session.get("proficiencies", "[]")),
        traits=world["races"].get(session.get("race", "Human").lower(), {}).get("traits", []),
        bestiary=get_bestiary(req.session_id),
        lore_book=get_lore_book(req.session_id),
        gold=session.get("gold", 0), alignment=session.get("alignment", 0),
        level=level, xp=xp, xp_to_next_level=session.get("xp_to_next_level", 100),
        x=session["x"], y=session["y"], surroundings=get_surroundings(req.session_id, session["x"], session["y"], radius=2)
    )
