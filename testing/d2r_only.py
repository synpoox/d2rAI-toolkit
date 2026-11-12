"""Checks for content D2R 3.3 has and a mod switches off: Terror Zones, Heralds and the Colossal Summit portal.

The pure parts (no game, no imports from the toolkit) read what a mod installed; the in-game parts need a character in a
game and the test harness. A mod's check module imports them and registers its own `@check`s:

    import d2r_only

    @check("terror-zones-config", tags=["d2r-only"])
    def terror_zones_config(ctx):
        doc = json.load(open(zones_json_path, encoding="utf-8-sig"))
        assert not d2r_only.zone_switches(doc), d2r_only.zone_switches(doc)

    @check("no-terror-zone-in-game", tags=["d2r-only", "game"])
    def no_terror_zone_in_game(ctx):
        ...   # character in a game, then:
        seen = d2r_only.scan_zones(ctx, zone_level_ids)
        d2r_only.assert_none_lit(seen)
        d2r_only.assert_control_lit(d2r_only.herald_control(ctx, monster_row))

How Terror Zones work in the data (D2R 3.3, build 93847): `desecratedzones.json` has, per game mode and difficulty,
`ladder_enabled`, `non_ladder_enabled` and `max_herald_tiers`; a Herald spawns only in a Terror Zone with a tier cap of
1 or more. The in-game scan leaves town (it warps with `cheat goto`), so only the pure parts run in the unit tests; the
rest needs a game slot you locked.
"""
from __future__ import annotations

import time

COLOSSAL_SUMMIT = 137    # levels.txt Id of Act 5 - Colossal Summit (Reign of the Warlock table set only)
ZONE_FIELDS = ("ladder_enabled", "non_ladder_enabled", "max_herald_tiers")
TERROR_PURPLE_MIN = 40   # purple samples that mean Terror Zone text; calibrated on 93847: 0 without it, 114+ with it
OVERLAY_BOX = (0, 0.04, 1, 0.8)   # client fractions scanned: the map overlay's text area, not the HUD band
SETTLE = 4.0             # seconds after a warp before the shot


# ---------------------------------------------------------------- data

def zone_switches(doc) -> list[str]:
    """Every Terror Zone switch in a desecratedzones.json document that is still on, as
    'config/mode/difficulty: field=value'."""
    on = []
    for n, config in enumerate(doc["desecrated_zones"]):
        for mode, difficulties in config["game_difficulties"].items():
            if not isinstance(difficulties, dict):
                continue  # the "type"/"name" strings next to the modes
            for name, d in difficulties.items():
                if not isinstance(d, dict):
                    continue
                for field in ZONE_FIELDS:
                    if d.get(field):
                        on.append(f"{n}/{mode}/{name}: {field}={d[field]}")
    return on


def colossal_portals(cubemain_text: str, level: int = COLOSSAL_SUMMIT) -> list[str]:
    """Descriptions of the enabled cube recipes whose output is a portal to `level` (the Colossal Summit)."""
    lines = cubemain_text.splitlines()
    head = lines[0].split("\t")
    enabled, output = head.index("enabled"), head.index("output")
    return [r[0] for r in (line.split("\t") for line in lines[1:])
            if len(r) > output and f"lvl={level}" in r[output] and r[enabled] == "1"]


# ---------------------------------------------------------------- pixels

def terror_purple(width: int, height: int, rgb: bytes, box: tuple[int, int, int, int] | None = None) -> int:
    """Samples (every 2nd pixel each way) in the colour of the Terror Zone level names ("Corrupted tremors strike
    <levels>", the overlay's terrorized line). `box` is (left, top, right, bottom) in pixels."""
    l, t, r, b = box or (0, 0, width, height)
    n = 0
    for y in range(t, b, 2):
        row = (y * width) * 3
        for x in range(l, r, 2):
            i = row + x * 3
            red, green, blue = rgb[i], rgb[i + 1], rgb[i + 2]
            if blue >= 200 and 110 <= red <= 200 and blue - green >= 90 and red - green >= 20:
                n += 1
    return n


def purple_in(img, fractions: tuple[float, float, float, float] = OVERLAY_BOX) -> int:
    """terror_purple of a game_ctl.Image, over a box given as client fractions."""
    return terror_purple(img.width, img.height, img.rgb, img.box(*fractions))


# ---------------------------------------------------------------- in game (need a game; not run by the unit tests)

def scan_zones(ctx, level_ids, settle: float = SETTLE, sleep=time.sleep) -> dict[int, int]:
    """With the minimap overlay open (the key `tab`) and debug mode on, warp to each level with `cheat goto` and count
    Terror Zone text samples. Returns {level id: samples}. The character must be in a game; this leaves town."""
    assert ctx.game.console("debug_mode"), "debug_mode not handled"
    ctx.game.key("tab")  # the overlay, where a terrorized level shows its line
    seen = {}
    for level in level_ids:
        ctx.game.console(f"cheat goto {level}")
        sleep(settle)
        ctx.shot(f"zone-{level}")
        seen[level] = purple_in(ctx.game.screenshot())
    return seen


def assert_none_lit(seen: dict, minimum: int = TERROR_PURPLE_MIN) -> str:
    lit = {k: v for k, v in seen.items() if v >= minimum}
    assert not lit, f"Terror Zone text in: {lit}"
    return f"{len(seen)} levels visited, Terror Zone text samples max {max(seen.values(), default=0)} (< {minimum})"


def herald_control(ctx, monster_row: int, settle: float = 2.0, sleep=time.sleep) -> int:
    """Positive control: `cheat heraldspawn <monstats row>` forces the level Terror-Zoned whatever the data says, so the
    same detector must see it. Returns the samples."""
    ctx.game.console(f"cheat heraldspawn {monster_row}")
    sleep(settle)
    ctx.shot("control-heraldspawn")
    return purple_in(ctx.game.screenshot())


def assert_control_lit(samples: int, minimum: int = TERROR_PURPLE_MIN) -> str:
    assert samples >= minimum, f"positive control: the forced Terror Zone text was not seen ({samples})"
    return f"positive control {samples}"
