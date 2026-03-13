import random
import re


def roll_d20(modifier: int = 0) -> dict:
    roll = random.randint(1, 20)
    total = roll + modifier
    if roll == 20:
        description_suffix = " — CRITICAL HIT!"
    elif roll == 1:
        description_suffix = " — CRITICAL FAIL!"
    elif total >= 15:
        description_suffix = " — Success"
    elif total >= 10:
        description_suffix = " — Partial success"
    else:
        description_suffix = " — Failure"
    return {
        "roll": roll,
        "modifier": modifier,
        "total": total,
        "description": f"d20({roll}) + {modifier} = {total}{description_suffix}",
    }


def parse_roll_requests(text: str) -> list[str]:
    """Scan DM response for [ROLL: SkillName] tags and return list of skill names."""
    pattern = r"\[ROLL:\s*([^\]]+)\]"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [m.strip() for m in matches]


def roll_dn(n: int) -> int:
    """Roll a single n-sided die."""
    return random.randint(1, n)
