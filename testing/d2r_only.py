"""Checks for content D2R 3.3 has and a mod switches off: Terror Zones, Heralds and the Colossal Summit portal.

The pure parts (no game, no imports from the toolkit) read what a mod installed; the in-game parts need a character in a
game and the test harness. A mod's check module imports them and registers its own `@check`s:

    import d2r_only

    @check("terror-zones-config", tags=["d2r-only"])
    def terror_zones_config(ctx):
        doc = json.load(open(zones_json_path, encoding="utf-8-sig"))
        assert not d2r_only.zone_switches(doc), d2r_only.zone_switches(doc)

    @check("no-terror-zone-in-game", tags=["d2r-only", "game", d2r_only.LEAVES_TOWN])
    def no_terror_zone_in_game(ctx):
        ...   # character in a game, then:
        seen = d2r_only.scan_zones(ctx, zone_level_ids)
        d2r_only.assert_none_lit(seen)
        d2r_only.assert_control_lit(d2r_only.herald_control(ctx, monster_row))

How Terror Zones work in the data (D2R 3.3, build 93847): `desecratedzones.json` has, per game mode and difficulty,
`ladder_enabled`, `non_ladder_enabled` and `max_herald_tiers`; a Herald spawns only in a Terror Zone with a tier cap of
1 or more. The in-game scan leaves town (it warps with `cheat goto`), so only the pure parts run in the unit tests; the
rest needs a game slot you locked. Every check that leaves town carries the tag `LEAVES_TOWN` ("leaves-town"): run those
only on a slot locked for out-of-town checks, never under a starting-town-only rule.

The pixel detector is calibrated on build 93847 at a 1920x1080 client, default brightness, HDR off; at another client
size the sample counts change, so `purple_in` refuses it (pass `client=None` to turn the check off in a unit test).
"""
from __future__ import annotations

import time

LEAVES_TOWN = "leaves-town"   # check tag: the check warps out of town; slot locked for out-of-town checks only
COLOSSAL_SUMMIT = 137    # levels.txt Id of Act 5 - Colossal Summit (build 93847; Reign of the Warlock table set only)
ZONE_FIELDS = ("ladder_enabled", "non_ladder_enabled", "max_herald_tiers")
# Purple samples that mean Terror Zone text. Calibrated on build 93847 at 1920x1080 client, default brightness, HDR off:
# 0 without the text, 114+ with it. The count scales with client area, hence CALIBRATED_CLIENT.
TERROR_PURPLE_MIN = 40
CALIBRATED_CLIENT = (1920, 1080)
OVERLAY_BOX = (0, 0.04, 1, 0.8)   # client fractions scanned: the map overlay's text area, not the HUD band
SETTLE = 4.0             # seconds after a warp before the shot
CONTROL_SETTLE = 2.0     # seconds after the Herald spawn before the shot


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
            if len(r) > max(enabled, output) and f"lvl={level}" in r[output].split(",") and r[enabled] == "1"]


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


def purple_in(img, fractions: tuple[float, float, float, float] = OVERLAY_BOX,
              client: tuple[int, int] | None = CALIBRATED_CLIENT) -> int:
    """terror_purple of a game_ctl.Image, over a box given as client fractions. The threshold is calibrated at a
    `client` size (default 1920x1080); another size fails loudly. `client=None` skips that check."""
    if client is not None:
        assert (img.width, img.height) == tuple(client), \
            f"client is {img.width}x{img.height}, the Terror Zone threshold is calibrated at {client[0]}x{client[1]}"
    return terror_purple(img.width, img.height, img.rgb, img.box(*fractions))


# ---------------------------------------------------------------- in game (need a game; not run by the unit tests)

def scan_zones(ctx, level_ids, settle: float = SETTLE, sleep=time.sleep, client=CALIBRATED_CLIENT) -> dict[int, int]:
    """LEAVES TOWN (tag `LEAVES_TOWN`): run only on a slot locked for out-of-town checks, never under a
    starting-town-only rule.

    With the minimap overlay open (the key `tab`) and debug mode on, warp to each level with `cheat goto` and count
    Terror Zone text samples. Returns {level id: samples}. The character must be in a game."""
    assert ctx.game.console("debug_mode"), "debug_mode not handled"
    ctx.game.key("tab")  # the overlay, where a terrorized level shows its line
    seen = {}
    for level in level_ids:
        assert ctx.game.console(f"cheat goto {level}"), f"cheat goto {level} not handled"
        sleep(settle)
        ctx.shot(f"zone-{level}")
        seen[level] = purple_in(ctx.game.screenshot(), client=client)
    return seen


def assert_none_lit(seen: dict, minimum: int = TERROR_PURPLE_MIN) -> str:
    assert seen, "no levels scanned"
    lit = {k: v for k, v in seen.items() if v >= minimum}
    assert not lit, f"Terror Zone text in: {lit}"
    return f"{len(seen)} levels visited, Terror Zone text samples max {max(seen.values(), default=0)} (< {minimum})"


def herald_control(ctx, monster_row: int, settle: float = CONTROL_SETTLE, sleep=time.sleep,
                   client=CALIBRATED_CLIENT) -> int:
    """LEAVES TOWN (tag `LEAVES_TOWN`): run only on a slot locked for out-of-town checks, never under a
    starting-town-only rule.

    Positive control: `cheat heraldspawn <monstats row>` spawns a Herald at the player; it is expected to show the
    overlay's Terror Zone line, which the same detector must then see. Not yet confirmed in game, in particular with
    Terror Zones switched off in data (the command may refuse). Returns the samples."""
    assert ctx.game.console(f"cheat heraldspawn {monster_row}"), "cheat heraldspawn refused (level/monster validation)"
    sleep(settle)
    ctx.shot("control-heraldspawn")
    return purple_in(ctx.game.screenshot(), client=client)


def assert_control_lit(samples: int, minimum: int = TERROR_PURPLE_MIN) -> str:
    assert samples >= minimum, f"positive control: the forced Terror Zone text was not seen ({samples})"
    return f"positive control {samples}"
