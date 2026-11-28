---
name: d2r-skill
description: Create, balance or rework a Diablo II Resurrected skill, including tree slot, tooltip, icon, missiles, states and HD animation.
---

# Make a D2R skill

1. Confirm class or item/monster use, replacement and unusual behavior. Use `modkit functions --column srvdofunc` (also client/start columns) and `modkit show skills "<name>"` to compare vanilla functions and their inputs. Use `d2r-engine` when no vanilla function can do it.
2. Replace a class row to preserve ID/tree/save byte (30 retail skills per class). More needs explicit extended saves and compatible characters. Retrieve `modkit-ops` → `Skills` for patch syntax, `tables` → `Skill damage and animation fields` for numbers/modes, or `engine-limits` → `Calc codes and formulas` for syntax.
3. SQ requires vanilla sequence fields and a compatible same-class HD state; preserve Whirlwind stop funcs. Give new missiles HD models and overlays a Character folder. Clone tooltip line types. For ports retrieve `porting-classic-mods` → `5. Function numbers` or `7. Skills that can't be selected`.
4. Build to zero errors and resolve references to renamed skills in all tables. Via `d2r-in-game-testing`, get the skill, cast in town and on monsters, verify tooltip numbers at levels 1 and 2, HD/classic animation, icon and hold-to-repeat. Record TESTING.md evidence.
