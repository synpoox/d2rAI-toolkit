# D2R address registry: build 93847

**Build 93847 only**: D2R 3.3.0 under D2RLoader 1.3.1, image PE timestamp **`0x6ab3782c`**. All values are RVAs
(image base + RVA) or byte offsets. Before using any of them on another build, verify in Ghidra
([engine-re.md](engine-re.md)). Signatures are Windows x64; "dataFlag" is the game's data-table selector byte
(`game + 0x106`, or `0x34a0e0(unit)`). Sources: a working D2RLoader plugin (hooked or called in game) and its
Ghidra notes. "Hooked" = installed with the entry bytes shown and ran in game.

## Image

| What | Value |
|---|---|
| PE TimeDateStamp | `0x6ab3782c` |
| Allocator object | `0x12063c0` -> allocator; vtable +0x20 frees a block |

## Game structure

| Offset | Meaning |
|---|---|
| game +0x104 | u8 difficulty (0 normal, 1 nightmare, 2 hell) |
| game +0x106 | u8 dataFlag passed to data-table getters |
| game +0x1aac8 | per-game counter map (used by the cube Red Portal; accessor `0x5d88b0`) |

## Units

| Offset | Meaning |
|---|---|
| unit +0x00 | i32 type: 0 player, 1 monster, 2 object, 3 missile, 4 item, 5 tile |
| unit +0x04 | class id (row in monstats / items / missiles / objects; `0x349860` returns it) |
| unit +0x08 | unit id (what `FindUnit` and the packets name a unit by; `0x34a330` returns it) |
| unit +0x10 | type-specific data (missile data, object data, item data) |
| unit +0x28 | seed {u32 lo, u32 hi}; RNG step `lo' = lo*0x6ac690c5 + hi`, `hi'` = carry (inlined everywhere) |
| unit +0x38 | path: dynamic (players, monsters, missiles) x u16 +0x02, y u16 +0x06; static (objects, items, tiles) x i32 +0x10, y i32 +0x14 |
| unit +0x88 | stat list (StatListEx when its flags +0x1c < 0); getter `0x34b870` |
| unit +0x124 | flags; bit 0x40 = "skill used" (classic 1.10 unit+0xc4) |
| unit +0x12c, +0x130 | passed by D2R's summon skills to pet setup (`0x55ef80` arg, `0x58d950` arg) |

| RVA | Signature | Meaning |
|---|---|---|
| `0x349860` | (unit, file, line) -> i32 | unit class id (row) |
| `0x34a330` | (unit, file, line) -> i32 | unit id (unit +0x08) |
| `0x34a0e0` | (unit) -> u8 | dataFlag (client functions use this) |
| `0x34a1e0` | (unit) -> u32* | &seed |
| `0x34a360` | (unit, file, line) -> inventory | unit inventory |
| `0x34b440` | (unit) -> room | unit's room |
| `0x34a040` | (unit, i32 xy[2]) | position |
| `0x34a110` | (unit) -> packed position | |
| `0x34ab60` | (unit) -> u32 | unit id |
| `0x34dbe0` | (unit, 1) | mark stats changed |
| `0x34e790` | (unit, on) | set unit +0x124 bit 0x40 |
| `0x34a5c0` | (unit) -> i32 | max speed (175; 250 for players in some states); min speed 15 at `0x34ab50` |
| `0x350a20` | (unit, x, y, mask) -> nonzero blocked | path collision test (teleport uses mask 0x804) |
| `0x491ca0` | (game, unit, 0, x, y, 0, 0) | move/teleport unit |
| `0x491960` | (player, message, player) | client message (0x15 = "can't do that") |
| `0x492790` | (game, a, b, char playerFlag) -> nonzero enemies | hostility test |
| `0x492cf0` | (game, room, x, y, monster, mode, search -1/4, flags) -> unit | spawn monster |
| `0x4327d0` | (game, unit, 0, 0, range, filter, callback, context, 0, file, line) | unit finder; callback (finderCtx {game, caster, count, context}, target) -> counted if nonzero (`0x4398b0` builds the context) |
| `0x2efc10` | (room) -> i32 | room -> level id |
| `0x2f0750` | (room) -> nonzero | room is in town |
| `0x38dfb0` | (room, x, y) -> room | room holding x/y near the given one |
| `0x32c4a0` | (dataFlag, level) -> record | levels.txt record; +0x0e u8 Teleport (0 no, 1 yes, 2 clear line) |
| `0x3e2b5c8` | (dataFlag, level id) -> act | level's act (address as used by the port; unusual range, verify) |

Client unit tables (build 93847; data addresses, read with ReadProcessMemory by `testing/unit_probe.py`; not yet confirmed against a running game: unit
ids and offsets as in the table above, class at unit +0x04, id at +0x08, mode at +0x0c, next in the bucket at +0x158):

| RVA | Meaning |
|---|---|
| `0x2a23910` | `ClientUnits`: 128 x Unit* per unit type, `type * 0x400` apart (players, monsters, objects, items), bucket = unit id & 0x7f. Dead monsters stay in the table (mode 0 or 12) |
| `0x2a25d10` | `ClientMissiles`: 128 x Unit* of the client's missiles, same bucket rule; found in the client owner lookup `0x9a7b0` |

## Stats and stat lists

| RVA | Signature | Meaning |
|---|---|---|
| `0x2f5020` | (unit, stat, layer) -> i32 | total stat value (thunk) |
| `0x2f48c0` | (unit, stat, layer) -> i32 | base value (`stat(...).base`) |
| `0x2f5c60` | (unit, stat) -> i32 | value without layer (mode 2; D2R's IAS read) |
| `0x2f5e80` | | stat compare helper used by cube conditions |
| `0x2f7d10` | (unit, stat, value, layer) | set stat |
| `0x2f34f0` | (unit, stat, value, layer) | add stat |
| `0x2f7c00` | (dataFlag, list, stat, value, layer) | set stat in a stat list |
| `0x2f3330` | (dataFlag, list, stat, value, layer) | add stat in a stat list |
| `0x2f5b80` | (unit, state, 0) -> list | the unit's stat list for a state (StatListEx: +0x20 state, +0x68 next, +0x90/+0x98 sub-list chains) |
| `0x2f5940` | (unit, state) -> list | stat list for a state |
| `0x2f7920` | (unit, list) | detach list |
| `0x2f4180` | (dataFlag, list) | free list |
| `0x3d5230` | (owner, item, state, flags) -> list | item stat list, created if missing (flags 0x40 = magic list) |

Pools: plain stat lists `0x2a9a430` (element 0x90); extended stat lists `0x2a9a4d0` (element **0x2b00**, 0x200 per
chunk; static constructor `0x3eb60`; pool +8 element size, +0x18/+0x28 chunk lists; chunk creation `0x1230260`);
create `0x2f65d0` (zero-fills 0x2b00), release `0x2f9eb0`. Extended list +0x2af0/+0x2af8: creation args.

## States

| RVA / offset | Meaning |
|---|---|
| `0x3074d0` | states.txt load: asserts `size <= 0x1ff` (MAX_STATES 511), then uses blocks = (count + 31) >> 5 |
| StatListEx **+0xaf0** | current state bits (blocks dwords), then "changed" flags at +0xaf0 + blocks*4; room 16 + 16 dwords to +0xb70; fields at +0xb70/+0xb78 follow (only copied from a zeroed template) |
| `0x2f6220` | check state (reads +0xaf0) |
| `0x2f7ea0` | (unit, state, on) set/clear state bit. Hooked; entry `40 53 56 41 57 48 83 EC 50 48 63 DA 45 8B F8` (PUSH RBX / PUSH RSI / PUSH R15 / SUB RSP,0x50 / MOVSXD RBX,EDX / MOV R15D,R8D) |
| `0x2f6370` | state array pointer |
| `0x2f62d0` | "changed" array pointer (dword index 0x2bc) |
| `0x2f0d80` | stat-list copy routine (32 dword moves of the state area; only caller `0x2f65d0`). **Do not patch** |
| `0x336440` | (unit, mask) -> 1 if any state of the mask is set. Hooked; entry `48 89 5C 24 08 48 89 6C 24 10 56 57 41 56` |
| `0x3356c0`, `0x336330` | other state-array users (loop over the live block count) |
| `0x3351b0` | (unit, state) -> nonzero: has state |
| `0x3355a0` | (unit, state, on) set state (game level) |
| `0x3354c0` | (unit, state, 0) clear state |
| `0x53a210` | server: send changed states. **Replaced by D2RCore `SendChangedWideStateStats`** (`jmp [rip+x]` at entry) |
| `0x539890` | server: send all states. **Replaced by D2RCore `SendAllWideStateStats`** |
| `0x52f9d5` | D2R sets state 186 `sharedstash` on the player at game join |

Displacement sites a "move the state arrays" patch would touch (for reference only: **don't**; D2RCore reads
+0xaf0): `0x3eb79` (0x2b00 pool size), `0x2f66ee` (0x2b00 memset), `0x2f62ba`, `0x2f7f8f`, `0x2f7fb0`, `0x2f7fff`,
`0x2f63c6` (0xaf0), `0x2f634f` (0x2bc).

## Skills

### Tables and dispatch

| RVA | Meaning |
|---|---|
| `0x238ea00` | **srvdofunc table**, 191 x 8-byte pointers (.data). D2R fills 0-171; **172-190 empty** |
| `0x43acb0` | server skill dispatcher (`D2Game\src\Skills\Skills.cpp`): reads srvdofunc (u16 skills +0x4e), rejects > 0xbe, calls (game, unit, skillId, level) if non-null; nonzero = success |
| `0x238e710` | srvstfunc table (indexed by u16 skills +0x4c; 91 slots by the dispatcher's bound immediate `0x5a`, 94 by the span to `0x238ea00`; 71-90 free) |
| `0x43b3e0` | (game, unit, skill, level, force) start a skill (calls srvstfunc). Hooked; entry `48 89 5C 24 10 48 89 6C 24 18 48 89 74 24 20` |
| `0x235f7d0` | **cltdofunc table**, 130 x 8 bytes, bound at `0x235f7c4`; D2R uses up to 109, **110-129 empty** |
| `0x216d20` | client skill dispatcher: (unit, skill, level) -> nonzero ran |
| `0x33f360` | (unit, skill entry) -> 0 usable, else reason code (D2Common Skills.cpp). Hooked; entry `40 56 57 48 83 EC 28 48 8B FA 48 8B F1 48 85 D2` |

### Record (skills.txt, 748 = 0x2ec bytes)

Getter `0x97790` (dataFlag, skillId) -> record.

| Offset | Field |
|---|---|
| +0x24..+0x28 | flags: +0x24 bit0 decquant, bit1 lob; +0x25 bit0 InTown; +0x28 bit5 usemanaondo, bit7 rightskill |
| +0x4c | u16 srvstfunc |
| +0x4e | u16 srvdofunc |
| +0x58 | prgcalc1 (compiled formula index) |
| +0x66 | i16 srvmissile; +0x68/+0x6a/+0x6c srvmissilea/b/c |
| +0x70 | aurafilter |
| +0x74 | 6 x i16 aurastat1-6 |
| +0x84 | aurarangecalc |
| +0x88 | 6 x i32 aurastatcalc1-6 |
| +0xa0 | i16 aurastate; +0xa2 auratargetstate |
| +0xb4 | i16 passivestate |
| +0x110 | i16 summon (monstats row); +0x112 u8 pettype; +0x113 u8 summode (255 none); +0x114 petmax calc |
| +0x13e | i16 cltmissile; +0x140/+0x142/+0x144 cltmissilea/b/c |
| +0x188 | HitFlags; +0x18c HitClass |
| +0x190 | calc1..calc10 i32 (calc1 +0x190, calc2 +0x194, calc3 +0x198, calc4 +0x19c, calc7 +0x1a8, calc8 +0x1ac, calc9 +0x1b0, calc10 +0x1b4) |
| +0x1b8 | Param1..Param8 i32 (Param3 +0x1c0, Param4 +0x1c4, Param5 +0x1c8) |
| +0x214 | u16 reqlevel |
| +0x226 | i16 minmana; +0x228 u8 manashift; +0x22a i16 mana; +0x22c i16 lvlmana |
| +0x238 | compiled localdelay formula (-1 none) |
| +0x24d | u8 SrcDam (/128) |

### Formulas and calc codes

| RVA | Signature | Meaning |
|---|---|---|
| `0x3b5160` | (dataFlag, unit, calc, skillId, level) -> i32 | evaluate a skill formula |
| `0x33b3b0` | (dataFlag, unit, code, skillId, level) -> u64 | **skill calc code switch** (skillcalc row -> value; unknown rows -> 0). Hooked; entry `48 89 5C 24 10 48 89 6C 24 18 48 89 74 24 20`. D2R row 41 = `blvl` |
| `0x3b4a90` | (dataFlag, missile, owner, calc, class (-1 own), level (-1)) -> i32 | evaluate a missile formula; callback `0x3b5540` |
| `0x3b9dc0` | (dataFlag, missile, owner, code, missileId, level) -> u64 | **missile calc code switch**. Hooked; entry `48 89 5C 24 08 48 89 6C 24 18 56 57 41 56` |
| `0x3b4880` | (dataFlag, player, item, calc) -> i32 | evaluate an items.txt formula |

### Mana cost

| RVA | Meaning |
|---|---|
| `0x33aa00` | (dataFlag, skillId, level) -> cost << 8 (minmana << 8 floor); no unit. Hooked; entry `48 89 5C 24 08 57 48 83 EC 20 41 8B F8 33 DB` |
| `0x436830` | server skill charge (entry already hooked by D2RLoader); calls `0x33aa00` at `0x4369fb`, return `0x436a00`, unit in **RDI** |
| `0x2188b0` | client skill charge; call at `0x218937`, return `0x21893c`, unit in **RBX** |
| `0x338110`, `0x33d480` | other callers (tooltip, checks) |

### D2R server skill functions (srvdofunc slot -> RVA)

| Slot | RVA | Skill / behaviour |
|---|---|---|
| 11 | `0x5562b0` | melee then calc1 missiles (Charged Strike style) |
| 18 | `0x553e60` | self buff (Frozen Armor): builds a state-list request on the stack; expiry callback `0x5551f0` |
| 24 | `0x553950` | wall (Fire Wall); caps active walls |
| 27 | `0x554c40` | Teleport (levels.txt Teleport rule, `0x350a20`, `0x491ca0`) |
| 58 | `0x55e7e0` | Revive |
| 65 | `0x563d90` | stat aura (aurastate on caster, auratargetstate on targets) |
| 66 | `0x5630e0` | damage aura (Holy Fire/Shock); finder callback `0x561280` |
| 68 | `0x567500` | nova + buff (Shout style) |
| 76 | `0x568f30` | Whirlwind do: the slot holds a 5-byte `jmp` thunk to the body at `0x568f40`, the address to hook (hit delay `0x56ac00`, called at `0x56916d`, `0x569186`, `0x5691e2`) |
| 109 | `0x5822b0` | itemless town portal (skill 411); `0x46fa70` finds destination town and makes the portal, `0x470ae0` links the town side |
| 113 | `0x584b60` | scroll/book skills: only sends packet 0x3f to the client (`0x47f520`) |
| 121 | `0x576bb0` | Rabies (melee + state + missile; missile choice `0x571700`) |
| 124 | `0x575de0` | timed storm (Hurricane, Armageddon): aurastate + periodic event |
| (Raise Skeleton) | `0x55e440` | pet summon pattern |
| (Multiple Shot) | `0x557840` | missile params pattern |
| srvstfunc 38 | `0x56a420` | Whirlwind start (game, unit, skill, level) -> 1 started. Hooked; entry `48 89 5C 24 10 44 89 4C 24 20 55 56 57 41 54` |

`0x56ac00` (unit, weapon) -> frames until Whirlwind's next hit (weapon attack length at D2R speed: clamp(stat 68 +
120*IAS/(120+IAS), 15, 175); 10 without a weapon). Only Whirlwind calls it. Hooked; entry
`48 89 5C 24 18 55 56 57 41 56 41 57 48 81 EC 80 00 00 00`.

D2R client skill functions: cltdo 15 `0x2b3750` (random spray around the target), 19 `0x2ae540` (client Charged
Strike fan), 31 `0x2b0ac0` (missile on a corpse).

### Skill helpers

| RVA | Signature | Meaning |
|---|---|---|
| `0x432b70` | (game, unit, &x, &y) -> both nonzero | skill target position |
| `0x48fe20` | (game, unit) -> unit | skill target unit (runs the target check `0x491b50`) |
| `0x44b2b0` | (game, attacker, target, 0, 1) | apply the queued melee hit (SUnitDmg.cpp) |
| `0x589930` | (game, caster, skill, level, target, x, y, &type, &id, &x, &y, 0) | cast a skill as an event (item procs) |
| `0x433d20` | (&StateListParams) -> list | create a timed state stat list (self-buff path). Params (0x30): +0 caster, +8 target, +0x10 skill, +0x14 level, +0x18 duration frames, +0x1c -1, +0x20 0, +0x24 state, +0x28 expiry callback |
| `0x438470` | | client state message sent by buffs |
| `0x9a570` | (unit) -> unit | client: the unit's skill target |
| `0x214c80` | (unit, &x, &y) -> nonzero | client: skill target point |
| `0x3b6700` | | animation lookup by mode (crashes when a skill's mode resolves to -1) |

### Pets

| RVA | Signature | Meaning |
|---|---|---|
| `0x4350e0` | (game, &SummonParams) -> pet | summon and register (enforces petmax). Params (0x30): +0 flags (1 = at x/y), +8 owner, +0x10 u16 monster, +0x14 AI state, +0x18 mode, +0x1c x, +0x20 y, +0x24 pettype, +0x28 petmax |
| `0x55fb50` | (game, owner, pet, 0, level) | pet level from the owner (monlvl AC/AR) |
| `0x55ef80` | (game, owner, pet, skill, level, owner+0x12c, 0) | skill's passive/aura stats and state on the pet |
| `0x58d950` | (game, pet, 0, owner+0x130) | party / AI |

## Damage

| RVA | Signature | Meaning |
|---|---|---|
| `0x437d00` | (unit, &damage, skill, level) | skill's elemental damage (EType/EMin/EMax, synergies) into a block |
| `0x4494b0` | (&to, &from) | copy a damage block |
| `0x44c030` | (game, attacker, target, &damage, 0, srcDam byte) | add weapon damage (srcDam/128; 0 = 128) |
| `0x44ce80` | (game, attacker, target, 1, &damage) | hit |
| `0x44a9b0` | (game, attacker, target, &damage) | apply |

Damage block: **0x180 bytes**: +0 u32 hit flags, +4 u16 result flags, +0x40/+0x48/+0x50 small list (data, count,
capacity; bit 63 = inline storage at +0x58, 16 x 12 bytes), +0x144 hit class, +0x158 tagged callback pointer (1 =
empty). Functions holding one inline its destruction (see `0x5630e0`'s epilogue).

## Missiles

| RVA | Meaning |
|---|---|
| `0x5371a0` | (game, &MissileParams) -> missile: create (server) |
| `0x1b7760` | (&MissileParams, 0) -> missile: create (client) |
| `0x166040` | (dataFlag, missileId) -> record or null |
| `0x1b89a0` | (dataFlag) -> missiles.txt row count |
| `0x490300` | (game, missile) -> owner |
| `0x9a7b0` | (missile) -> owner (client) |
| `0x3bc450` / `0x3bb470` | (missile) -> skill / skill level |
| `0x3bb0f0` | (missile) -> frames elapsed |
| `0x3bb1e0` | (missile) -> frames left |
| `0x3bdbc0` / `0x3bd450` / `0x3bd8a0` | total frames / set frames left / set step counter |
| `0x2390e80` | **server do table** (record +0x2c), bound 54 (slots 0-53), dispatcher `0x466ce0`; **46-53 empty** |
| `0x2391030` | **server hit table** (record +0x2e), bound 71 at `0x2391404`, dispatcher `0x464ac0` (game, missile, target or null); **61-70 empty**. Return value: build 93847, unverified. A review read srvhit 4 (`0x45ddb0`) as returning 3 (bit 0x2 = deal the missile's damage) but this was not checked against the caller at `0x464ac0`, so the toolkit types the function as `void` and never reads a result |
| `0x2358430` | **client do table** (record +0x28), called (missile, float part-frame) from `0x1ba040` (the second argument is a float, in xmm1 on x64, not an int); 92 slots (0-91), **78-91 empty**, slot 14 unused |
| `0x2358710` | **client hit table** (record +0x2a), bound 81 at `0x2358a64` (slots 0-80); **66-80 empty**, slots 6, 7 empty (a mod's reading also lists 8, 11, 15, 17, 20-23, 27, 35, 45, 49, 58, 59 as empty; not checked here) |
| `0x4550e0` / `0x1b5380` | server / client do 1 (plain move) |
| `0x459380` / `0x1a8880` | server do 15 / client do 19 (Frozen Orb style spawner) |
| `0x45bc40` | server hit 1 (explosion: missile damage to units within sHitPar1 / calc1) |
| `0x45ef10` | server hit 21 (auratargetstate + aurastats on the target) |
| `0x1ac8f0` | client hit 2 (spawns CltHitSubMissile1) |
| `0x1b9840` | client spawner (16 directions) |

MissileParams (0xa0 bytes, classic 1.10 block +0x10 after three pointers): +0 u32 flags, +8 owner, +0x10 origin,
+0x18 target, +0x20 missile, +0x24 x, +0x28 y (0 = origin), +0x2c/+0x30 target x/y, +0x34 gfx arg, +0x38
velocity, +0x3c skill, +0x40 level, +0x44 loops, +0x4c frame, +0x50 activate frame, +0x54 activation (frames before
the missile starts; Multiple Shot puts skills.txt calc2 there; earlier read as attack bonus), +0x5c range (frames the
missile lives; with flag 0x8000), +0x68 source key (unit state key of the missile a chain starts from: Chain
Lightning's srvhit 12), **+0x70 create callback** (replaces classic init function pointer: an index into the create
callbacks, run on the new missile with +0x74 as its argument; 1 = Firestorm's, 0 = none). Observed in game.

Missile record (classic 1.13c layout moved +0x24 from +0x24): +0x28 u16 pCltDoFunc, +0x2a pCltHitFunc, +0x2c
pSrvDoFunc, +0x2e pSrvHitFunc, +0x3a i16 SubMissile1, +0x40 CltSubMissile1, +0x46 HitSubMissile1, +0x4e
CltHitSubMissile1, +0x5c/+0x60/+0x64/+0x68/+0x6c Param1-5, +0x70/+0x74 sHitPar1/2, +0x7c/+0x80/+0x84 CltParam1-3,
+0x8c CltParam5, +0x90/+0x94 cHitPar1/2, +0xa4 SrvCalc1, +0xa8 CltCalc1, +0xac SHitCalc1, +0xb0 CHitCalc1, +0x1b6
i16 Skill.

Missile data (unit +0x10): +0x0c skill, +0x0e level, +0x10 i16 total frames, +0x14 frames left (float, x40 per
frame), +0x30 step counter (Fire Wall's).

## Items and inventory

| RVA | Signature | Meaning |
|---|---|---|
| `0x314110` | (dataFlag, classId) -> record | items record (armor/weapons/misc): +0x80 code (a dword, but the engine keys items by its first 3 characters), +0x94 i32 pSpell, +0xa4 calc1-3, +0x144 i8 spellicon (layout as classic 1.13c up to +0x94) |
| `0x373890` | (item, itemtype) -> nonzero | item is of type |
| `0x36cf60` | (item) -> quality | item data +0 |
| `0x36cfe0` | (item) -> u8 | item data +0x55: page (0 inventory, 3 cube, 4 stash) |
| `0x36ca10` | (item) -> u8 | item data +0x54 |
| `0x36dea0` | (item, byte) | set item data +0x5c |
| `0x376de0` | (item, player) -> i32 | level requirement (-1 none) |
| `0x3d4620` | (type, unit, item, mods, index, set, &property, state, flags, 0) | apply a property (classic D2Common 10665); property {i32 prop, param, min, max}; property functions table `0x2386ab0` |
| `0x535f60` | (game, player, item, 1, 0, unit id, byte, byte, position) | item update packet (as after identify `0x46e8c0`) |
| `0x388c10` / `0x38aba0` | (inventory) -> first item / (item) -> next | inventory walk |
| `0x3886d0` | (inventory, bodyloc 0-12) -> item | equipped item |
| `0x382d20` | (i32 location[4], item) | item location: unit id, page, packed x/y |
| `0x472590` | (player, adds, removes, addIds, removeIds, nAdds, nRemoves, 0) -> bool | validated inventory change |
| `0x4712a0` | | removal pattern for a used-up tome |
| `0x43ec10` | (game, item) | free item |
| `0x236fe30` | **item spell table**: 20 x 12 bytes {u32 check, u32 use, u32 flag}; flag 1 = not used up; 16-19 empty; 20+ ignored. Check handlers `0x1d3ea30` (11), use handlers `0x1d3ea90` (16) |
| `0x5817f0` | (game, player, item, target) -> bool | item spell check dispatcher. Hooked; entry `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18` |
| `0x581680` | (game, player, item, target) | item spell use dispatcher (caller removes a used item). Hooked; entry `48 89 5C 24 18 48 89 6C 24 20 56 57 41 57` |
| `0x3731f0`, `0x373610`, `0x36f000` | | item getters (`0x3731f0` item type) seen in hang thread samples; signatures unverified |
| `0x300a90` | | data tables getter, seen in the same samples; unverified |
| `0x308e80` | (item) -> 1 when the slot flag is 0 | "used up"; client puts it in the use message (`0x1c7a30`), server use-item handler `0x4f40c0` refuses unless both agree |

## Portals and objects

| RVA | Meaning |
|---|---|
| `0x432ce0` | (game, unit, room, x, y, destLevel, &object, objectId, 0, 1) create portal (`D2Game\src\Items\ItemMode.cpp`); object 0x3b town portal, 60 red portal; also places the return portal (`0x435dd0`) |
| `0x517f90` | (game, room, xy[2], 3, 0x400, &room, 5, 100) free spot near xy |
| `0x34e9d0` | (object, level byte) set portal destination (clears the high byte) |
| `0x34ad40` | portal destination getter (16 bits: object data +0x08 low, +0x78 high) |
| `0x5da800` | cube output "Red Portal": (game, player, key, level, max). Needs the player in town and finds a free spot (`0x517f90`), makes object 60 to `level` through the portal maker `0x432ce0` (last argument 1 lifts the town portal's level whitelist), then adds 1 to the game counter named by `key` (`0x5d88b0`); with `max` 1 it refuses once the counter is 1 |
| `0x490410` | (unitType, row, x, y, game, room, 1, 0, 0, 0) -> unit: spawn a unit; type 2 = object. Tested from a game-thread callback |
| `0x4022a0` | debug `SpawnObject` handler: a worked example of the spawn. Game: `0x4062f0(0x4061e0(1))`; player: `0x484c90(*(game+0x138), 0)`; room: `0x34b440(unit)`; free spot: `0x402f50(room, xy, 5, 0x3e01, &room)`; objects row count: `0x38fc70(*(u8*)(game+0x106))` |
| `0x23a51c0` | object operate table, 75 entries, indexed by objects.txt `OperateFn` (compiled row `+0x15e`); entry = `int fn(args*)`, args = { game, object, player, seed, id }. Slot 60 is null and unused: a plugin can write its own function there, no hook needed. Called from `0x592c40` and `0x593630` |
| `0x239b980` | object init table, 81 entries, indexed by `InitFn` (compiled row `+0x15c`) |
| `0x5d88b0` | (game + 0x1aac8, &key) -> int* per-game counter |

## Cube

| RVA / offset | Meaning |
|---|---|
| data tables +0x1570 / +0x1578 | cubemain records / count; record **0x16c** bytes: +0 enabled, +1 min diff, +2 class (-1 any), +3 u8 op, +4 param, +8 value, +0xc numinputs, +0xe version, +0x10/+0x12 ladder seasons |
| `0x3e3f60` | (?, index) -> cubemain record (asserts in `D2Common\src\DataTbls\HoradricCube.cpp`) |
| `0x529090` | (int* result, game, player, out) recipe search (`D2Game\src\Player\PlrTrade.cpp`): per record checks enabled, version, ladder (`0x403fe0`), difficulty, class, numinputs, then the player condition switch for **ops 1-14 only** (1/2 date, 3-14 stat compares via `0x2f5020`/`0x2f48c0`/`0x2f5e80`; other ops pass), then `0x529d50` for inputs 0..6; all nonzero -> found |
| `0x529d50` | (game, inventory, record, input#) match one input against the cube items, checking item condition ops 15+ |

## Levels and automap

| RVA | Meaning |
|---|---|
| `0x32db30` | LvlTypes.txt loader (vector: extra types load) |
| `0x32cae0` | AutoMap.txt loader: matches LevelName against 36 names (table `0x1cfe110`, 0x10 bytes each); unmatched -> assert `ii < NUM_LEVEL_TYPES`, type 0 |
| `0x2a9a8e0` | 36 x 8-byte row ranges per level type (followed by another object at `0x2a9aa00`) |
| `0x2a9a8c8` | automap rows vector: data pointer, +8 count; row 0x20 bytes: +0 type, +4 tile type, +8 u8 style (0xff any), +9/+0xa start/end sequence (start 0xff any), +0xc four cels, +0x1c cel count |
| `0x32bdf0` | (levelType, tileType, style, sequence) -> cel or -1: automap tile lookup, **no bounds check on levelType**. Hooked; entry `48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20` |
| `0x2372a40` | pointer to the automap seed {lo, hi} |
| `0x3da650` | level-entry finder: with levels.txt `Position` (level record +0x90) set it picks the arrival spot with `0x3dac20`, a random room from the maze's entry-room table (count at level +0x200, entries at +0x34, stride 0xc); an empty table gives (0, 0) and `0x3289a0` then reads `[rdx+0x50]` of null |
| `0xd5fe0` / `0xd5710` / `0xd1710` | per-character map memory (`<char>.map`, `.ma0`-`.ma3`): save / load / level switch. 100 buckets indexed by levels `Layer` directly; the loader rejects a cel >= 1499 by writing the node's own offset into its `next` (the next save loops for ever) |

## Sounds

| RVA | Signature | Meaning |
|---|---|---|
| `0x3b20c0` | () -> int | sounds.txt row count |
| `0x3b1fd0` | (id) -> record | sounds.txt record |
| `0xd8c70` | (id) -> u64 | record +0xc7; **reads null+0xc7 for an id outside the table**. Entry `40 53 48 83 EC 20 8B D9` |
| `0xd9180` | (id) -> u64 | record +0xb0 & mask; null+0xb0 when out of range. Entry `40 53 48 83 EC 20 8B D9` |
| `0xd9030` | (id, buffer, size) | the sound's file path into buffer; copies from null+0x32 when out of range. Entry `40 53 55 57 48 83 EC 20` |
| `0xd9e60` | (id, ?, ?) -> id | picks the sound to play; null+0x96 when out of range. Entry `40 55 53 41 54 41 55 48 8D 6C 24 F8` |
| `0xda360` | (id, mode) -> id | sound group variant; null+0x96 when out of range. Entry `40 53 55 56 57 41 55 48 83 EC 20` |
| `0x107dd0` | (unit, id) -> playing sound or null | client unit sound wrapper (calls `0xd8c70`). Entry `48 89 5C 24 08 48 89 74 24 10 57 48 83 EC 20` |
| `0x1079e0` | | client monster update: plays the monsounds Neutral sound (record +0x68, NeuTime +0x6c) through `0x107dd0` |

`0xd9210`, `0xd92f0` test the record for null; `0xd96a0` returns null; `0xdb700`, `0xdb8f0`, `0x1fd600` walk all rows:
these need no guard.

## Death and events

| RVA | Signature | Meaning |
|---|---|---|
| `0x44db20` | (game, victim, killer or null, flag) | unit death function (`D2Game\src\Unit\SUnitDmg.cpp`); returns at once for a monster in mode 0 / 12 or a player in mode 0 / 17; flag 1 also takes a pet off its owner's list. Hooked; entry `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18 57 41 56 41 57 48 83 EC 50` (24 bytes) |
| `0x44d570` | (game, event, unit, other unit, arg) | unit event dispatch wrapper (raises an events.txt event on a unit) |
| `0x2a9a580` | data managers, 16 bytes apart | itemstatcost array at +0x1258, count at +0x1260; record 0x144 bytes, +0x44 first event id |
| unit +0x0c | u32 | unit mode |

## Missiles, pets, potions, cube outputs

| RVA | Meaning |
|---|---|
| `0x45ce90` | server missile hit function 6: spawns the monstats row `sHitPar1` through `0x50a050(game, room, sHitPar1, ...)` |
| `0x5c1400` | NecroPet AI think; branches on the pet's AI control (monster data +0x30) +0x44: 1 = ranged branch, 0 = melee (observed) |
| `0x57ecb0` | timed potion handler (item spell 3): stat calc = total over the duration for hitpoints, mana, manarecovery, hpregen (`<< 8`); other stats stored as calc / len |
| `0x5269c0` | cube executor. Its "portal" outputs: `Cow Portal` is fixed to the Cow Level; `Red Portal,lvl=<id>` (cubemain output column) opens a red portal to level `<id>` of the player's act through `0x5da800`, so a fixed destination needs no plugin. A different level per use is the plugin case |

## Item packets

| RVA | Meaning |
|---|---|
| `0x1c6b60` | client item packet handler (SCMD_ITEMEX); when the item could not be decoded it calls `0x1c6a40(0)` -> `0x34b870`, which returns `*(unit + 0x88)` with no null test (crash at `0x34b891`) |

### Item type test sites

`0x373890(item, type)` is called with these type numbers written into the code (25 sites with an immediate >= 67,
plus `jewl` 58 elsewhere). A mod's itemtypes.txt must give these codes these ids:

| Type | Code | Sites (instruction loading the type) |
|---|---|---|
| 75 | rune | `0x0cc192`, `0x1c85a4`, `0x23165a`, `0x2bd438`, `0x2c2934`, `0x2d9dc2`, `0x43c979`, `0x43cc33`, `0x475283`, `0x527f5a` |
| 77 | hpot | `0x15a026`, `0x2296d7`, `0x4f1e0e`, `0x4f4d1a` |
| 81 | apot | `0x15a037`, `0x2296f4`, `0x4f4d3c` |
| 82 | wpot | `0x15a046`, `0x2296e5`, `0x4f4d2c` |
| 68 | h2h | `0x3854f9` |
| 73 | pelt | `0x40bbef` |
| 83 | scha | `0x422fec` |
| 84 | mcha | `0x422ff7` |
| 96 | gem4 | `0x527eff` |

`mov edx, imm32` (`BA xx 00 00 00`) at most sites; `lea edx, [reg + imm8]` (`8D 50 xx` / `8D 51 xx`) at the potion
pairs and `scha`/`pelt`. The plugin template's `item_type_check.cpp` checks them.

## Renderer Pool

| What | RVA | Notes |
|---|---|---|
| Pool object | `0x2810ff0` | `+0` vptr, `+8` parent allocator, `+0x10` base, `+0x18` size, `+0x20` TLSF handle, `+0x28` lock |
| Pool start / stop | `0xf6efe0` / `0xf6ef70` | start takes `0xc00000` bytes (12 MB) from the parent, TLSF create `0x1215a30`; strings "Renderer Pool" / "TlsfAlloctor"; called once from the renderer start. Stop zeroes base and size |
| Vtable | `0x1d6d770` | 6 entries: `0x82dcf0` dtor, `0x82dad0` allocate(size, align), `0x82db40` reallocate(p, size, align), `0x82dbf0` TLSF realloc(p, size), `0x82dc60` free(p), `0x82dcb0` usable size(p). **Shared with six other allocator objects**: copy it, never patch it. No direct calls to the entries |
| Allocate wrapper | `0xf6f060` | (size, align); 100+ callers; on null reports "Failed to allocate from Renderer pool!" (`0xf6ef40`) and returns null |
| Free wrapper / object getter | `0xf6f0c0` / `0xf6efd0` | |
| A null-allocation crash site | `0xf3d028` in `0xf3cfd0` | moves 0x80-byte records into a new vector buffer (vector grow `0xf3d587`, model instance build, `D2Render\src\model_instance.cpp`) |

### Memory pools

The Renderer Pool is one of six TLSF pools. The size D2R gives a pool is its *start* size: memory can be added to a running pool (see [engine-limits.md](engine-limits.md) "Memory"). Build 93847.

| Pool | Object RVA | Start size (maker) | When it ran dry |
|---|---|---|---|
| Entity System | `0x2677438` | 70 MiB (`0xd714e0`) | A map preset over about 34,000 entities: the entity vector grow `0x6d17d0` memsets a null |
| Renderer | `0x2810ff0` | 12 MiB (`0xf6efe0`) | A full-density map: `0xdafe30` (from `0xeeb4d0`) writes through the null |
| JSON | `0x27d1770` | 40 MiB (`0xa0a230`) | A 46 MB generated preset: null write in the memcpy at `0x12d36f3` |
| Object | `0x27d7848` | 50 MiB (`0xa20bb0`) | - |
| Jobs | `0x34c3ce8` | 10 MiB (`0xa00000`; maker `0x9e91e0`) | A full-density map: `0xd9e740` writes through the null `0x9e8ca0` returned |
| Texture cache | `0x27ff098` | 24 MiB (`0xe8b100`) | - |

To add memory (tlsf_add_pool, which is inlined in `0x1215a30`): allocate a block, take the pool's lock (`+0x28`; `EntityPoolLock` `0x122ad60` / `EntityPoolUnlock` `0x122ad90`; the Jobs pool's `+0x28` is a spinlock instead: swap in its own address, spin while it is not 0, store 0 to release), write the block's size word (size | 1) and call `TlsfBlockInsert` `0x1215650` (control at pool `+0x20`, block 8 bytes before the size word), then write the sentinel (previous-block pointer, then a size word of 2) after the block. The pool objects exist only after D2R makes them (the control pointer at `+0x20` is null until then), so a plugin loaded early waits for it. Evidence: a classic port's plugin installs this on all six pools at start (it logs `on: +<n> MiB` per pool); it was written for the crashes above. The toolkit holds no growth code.

## HD asset indexes

| RVA | Meaning |
|---|---|
| `0xf75c60` | model asset cache init: reads `data/hd/model_lod_desc.bin`; a missing file asserts "Binary desc cache is missing! ALL model loads will be blocking!" |
| `0xf75fe0` | LOD resolver (cache, name, lodHint, out): FNV-1a 32 of the lower-cased path; unlisted: "Failed to find LOD for model %s" and the plain name is used (never drawn) |
| `0xf75af0` | lower-bound lookup in the 44-byte entry array |

## Engine-side crashes not caused by mods

| RVA | Meaning |
|---|---|
| `0x775fc0` | handler of event type 0x10 of the client's HD `UnitTranslationLayer` event loop (`0x77a3b0`); rarely reads a stale event payload and faults at `0x7761dc` while a character loads. A guard can skip events whose payload pointer is not readable |

## Client UI (crash locations seen)

| RVA | Meaning |
|---|---|
| `0x287a50` | skill tooltip line renderer (`D2Client UI/SkillDesc.cpp`): asserts `stringIndex1 != strdummy` when a line type's text is missing |
| `0x199cb0` | text formatting (`UI/text.cpp`), case 6 joins "was slain by" fragments and sprintf's them |
| `0x29538e` | access violation (null + 0x12e) when an item has no HD picture |

## Entry bytes summary (hooked in game)

| RVA | Bytes |
|---|---|
| `0x2f7ea0` | `40 53 56 41 57 48 83 EC 50 48 63 DA 45 8B F8` |
| `0x32bdf0` | `48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20` |
| `0x336440` | `48 89 5C 24 08 48 89 6C 24 10 56 57 41 56` |
| `0x33aa00` | `48 89 5C 24 08 57 48 83 EC 20 41 8B F8 33 DB` |
| `0x33b3b0` | `48 89 5C 24 10 48 89 6C 24 18 48 89 74 24 20` |
| `0x33f360` | `40 56 57 48 83 EC 28 48 8B FA 48 8B F1 48 85 D2` |
| `0x3b9dc0` | `48 89 5C 24 08 48 89 6C 24 18 56 57 41 56` |
| `0x43b3e0` | `48 89 5C 24 10 48 89 6C 24 18 48 89 74 24 20` |
| `0x56a420` | `48 89 5C 24 10 44 89 4C 24 20 55 56 57 41 54` |
| `0x56ac00` | `48 89 5C 24 18 55 56 57 41 56 41 57 48 81 EC 80 00 00 00` |
| `0x5817f0` | `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18` |
| `0x581680` | `48 89 5C 24 18 48 89 6C 24 20 56 57 41 57` |
| `0x44db20` | `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18 57 41 56 41 57 48 83 EC 50` |
| `0xd8c70` | `40 53 48 83 EC 20 8B D9` (an 8-byte expected-bytes check; D2RLoader accepted it and the hook ran in game) |

Table slots are written with `PatchWriteU64(table + 8*slot, expected, 8, function)`: expected 0 for an empty slot,
the current pointer when wrapping a D2R function. srvdofunc `0x238ea00` (free 172-190), cltdofunc `0x235f7d0` (free
110-129), server missile hit `0x2391030` (free 61-70), client missile hit `0x2358710` (66-80 empty, 6, 7 empty; more listed at the table row), server missile
do `0x2390e80` (46-53 empty), client missile do `0x2358430` (78-91 empty, 14 unused). Item spell flag:
`PatchWriteU32(0x236fe30 + 12*slot + 8, 0 -> 1)`.

## Inventory grid widget (build 93847)
- Vtable of the inventory grid: `0x1CF3800`. Slot `0xC0` is the item info build (`0x2C4AC0`, widget, out, item) and slot `0xF8` is the item placement (`0x2C4B80`, widget, out origin, packed size, visual). The belt has its own vtable, `0x1CE2FA0`.
- The placement's origin is x, y, width, height in screen px. Writing an entry with `PatchWrite` needs no code bytes and leaves the item draw hook at `0x2A72D0` free for one other plugin.
- The item draw `0x2A72D0` (widget, item) draws the item picture and is called once per item widget; the first 15 bytes are `48 85 D2 0F 84 D7 00 00 00 56 57 48 83 EC 68`. D2R's text draw is `0x902E20` (text, int32 rect[4] in screen px, font block, scale); the font block is 0xA4 bytes, built with defaults by `0x86D1B0`. A hook on the item draw is the way to draw a number on an item while the loader's overlay draws nothing ([d2rloader.md](d2rloader.md), *Loader gaps*). Read from code, not yet re-checked in a dump.
- The highlight behind an item is placed one cell at a time, so its size argument is not the item's size.
- Odd-size centring moves drawing only: clicks and tooltips keep the real cells.
- `WidgetHandle` from the widget service is an id, not a widget pointer.
- Unit reads: unit bucket `0x4925B0` (type, game, id; list next +0x158, id +8), missile owner `0x490300` (game, missile), monster flag test `0x38E870` (unit, u16; 8 Unique seen in code), monster affixes `0x38E310` (unit, zero-terminated bytes).
- Self-buff do-function `0x553E60` (game, unit, skill, level) casts any Frozen Armor-style skill row. `0x34E790` clears the skill-used flag it leaves, `0x4370B0` (unit, state, 1) clears a state and replaces same-group states, `0x3351B0` tests a state.
- Monster type flags for `0x38E870`, named by the debug display at `0x167130`: 2 Super Unique, 4 Champion, 8 Unique, 0x10 Minion, 0x200 Herald, 0x400 Herald Minion. The same function shows 9 affix slots at `0x38E310`.

## Item property lines (`D2Client/UI/mods.cpp`)

| RVA | Signature | Meaning |
|---|---|---|
| `0x2dc4b0` | (item, char* out, int size, int, u32, int, u32, u32, void*, void*) | merges the item's stat lists and writes its blue property lines to `out` (size 1024). No direct callers in the dump. An inline hook at the entry works: bytes `48 89 5C 24 20 55 56 57 41 54 41 55 41 56 41 57` (16) |
| `0x2da760` | (flag, out, size, item, ...) | builds the lines from the merged list. D2RLoader has patched its entry (`jmp [rip+...]`, table in `.maho`), so hook `0x2dc4b0` instead |

After `0x2dc4b0` returns, `out` is plain ASCII with one line per LF, bottom line first and no colour codes (tested in game). Lines with the same stat are already merged, so a line can hold values from more than one source.

Unlike tooltip listeners, this buffer takes colour codes: U+E07E plus the code character. `;` is purple and `3` is the property blue; a code holds for the rest of its line and later lines (tested in game).

## Header coverage: every RVA in rvas_93847.h and rvas_93847/

Each RVA the per-build header declares has a row in this file (`tests/test_rva_knowledge.py` fails otherwise). Rows above
this section hold the detail; the rows here cover what had no row yet, in RVA order, with the header name in the first
column. Signatures are Windows x64 and come from the header comment; "-" means the header gives none.

Evidence: **H** hook or patch with D2R's original entry bytes in the header (checked before a hook or patch);
**C** a plugin calls it with this signature; **T** a dispatch table or slot, read from the image and bounded by the slot
count; **R** read from the dumped image and its Ghidra decompile, not called by the toolkit's own code; **P** a patch address inside a
function (bytes in the header, checked before the patch); **D** data: a variable, mask or constant array in the image.

| RVA | Header name | Signature | Meaning | Ev |
|---|---|---|---|---|
| `0x8b2d0` | LocalPlayerSlot | () -> slot of the local player | Returns slot of the local player | R |
| `0x976e0` | MonStatsRecord | (dataFlag, classId) -> monstats record or null | Returns monstats record or null | R |
| `0x97790` | GetSkillRecord | (dataFlag, skillId) -> record or null | The skills.txt record of a skill; bound as d2r::api.getSkillRecord | C |
| `0x9a480` | ClientPlayer | (slot) -> the client's player unit in that slot | Returns the client's player unit in that slot | R |
| `0x9a5d0` | ClientFindUnit | (id, type) -> the client's unit or null | Returns the client's unit or null | R |
| `0xcd6d0` | SetActPalette | (act byte) -> void | sets ActPalette. The client's unit placement 0x9bf00 sets it from the level record's Pal, the act load 0x86bc0 from the act. The global it writes: 0x2a2adc0. | R |
| `0x112620` | NpcMenuHire | - | Hire's handler: opens HireMenuPanel, for any NPC | R |
| `0x116480` | NpcMenuOpen | (record, resurrect) -> 1 | inserts or removes Resurrect before Hire, then the menu opens. push rbp / push rbx / push rdi / lea rbp,[rsp-0x47] / sub rsp,0x90 | H |
| `0x193a80` | SetMissileOffset | - | The client's 3D offset and motion of a missile's graphic, as D2R's Meteor (cltdo 9, 0x1b6480) sets them (1.13c's D2Client 0xc7e30 and its writes to gfx +0x30 +0x10..0x18): (missile, x, y, z) << 11; (missile, x, y, z, shift), shift 0 stores the values as given (1.13c's raw writes), else << 11. | R |
| `0x193ad0` | SetMissileMotion | - | Client: sets a missile graphic's motion, next to SetMissileOffset | R |
| `0x213f50` | ClientThrowSkillMissile | (unit, missile, skill, level, UnitStateKey(unit)) | Client half of ThrowSkillMissile | R |
| `0x2142d0` | ClientAreaUnits | (center unit, x, y, radius, unit mask, callback, arg, 0) | Client: callback(&ClientAreaContext, unit) for each unit in range; x/y 0 = the center unit's position, radius 0 does nothing (Fist of the Heavens' clthit 26 0x1adcb0) | R |
| `0x22f9a0` | CltDoLeap | (unit, skillId) | D2R cltdo 43: Leap's client half | R |
| `0x2aed4a` | CltDoStrikeLocalOnly | - | Power Strike's client do function (cltdo 22, 1.13c D2Client 0x15660) draws the strike only for the local player: 'je' at this address skips its early return. | P |
| `0x2ef4d0` | RoomUnitRemoved | (room, unit type, unit id); (game, unit) | How operate 15 removes a used town portal: the first call tells the room's clients, the second frees the unit | R |
| `0x2ef8b0` | ActSpawnSpot | (dataFlag, act, level, spot, int32* x, int32* y, unit size) -> room or null | D2Common's DUNGEON_FindActSpawnLocationEx (1.13c's ordinal 10816), as WarpToLevel calls it: the room holding the free spot near the level's spot, its coordinates in x/y. With the levels record's +0x90 set, spot picks a special tile of the level's presets (0x3dac20; 13 the level's entry); without it, spot is unused. It builds the level if needed | R |
| `0x2efd90` | RoomFirstUnit | (room) | First unit of a room | R |
| `0x2efde0` | NearRooms | (room, &rooms, &count) | The room walk of 0x593630 (finds an object by class near a unit): the room and its neighbours. RoomFirstUnit gives a room's first unit, NextUnitInRoom the next one | R |
| `0x2f0530` | RoomPortalMark | (room, 0) | sets bit 0x400000 of the room's level-gen room (+0x18, flags +0x50; 0x328860), (room, 1) clears it. The portal maker sets it on each portal's room, operate 15 clears it on removal: an unmarked room is freed with its units once no player is near. | R |
| `0x2f0630` | RoomReleasable | - | The room-release pass 0x4088c0 asks (act, room) -> nonzero for each room 10+ ticks without a player; a yes frees the room and its units (0x504260 each, then 0x2f0110). Its only caller. 0 when the room is marked (RoomPortalMark). push rbx / sub rsp,0x20 / cmp dword [rcx+0x80],0 / mov rbx,rdx | H |
| `0x2f2cb0` | AttachStatList | (unit, list, 1) | It does not set the list's state bit: UnitHasState read 0 after it in game, and D2R's 0x339d70 calls SetStateBit after it. Its body is D2RCore's (jmp [0x3e2a270], filled at runtime). | R |
| `0x2f4190` | UnitAlignment | (unit) -> alignment | stat 172 for players and monsters (0 hostile, 1 neutral, 2 ally; pets 2), 2 for other types. 1.13c's D2Common #10830. D2RLoader hooks its entry: call it, never hook it. | R |
| `0x2f4d20` | UnitMaxLife | (unit) -> max life, 1/256 | Returns max life, 1/256 | R |
| `0x2f56a0` | ListSkill | (list) -> its skill id | Returns its skill id | R |
| `0x2f56e0` | ListLevel | (list) -> its skill level | Returns its skill level | R |
| `0x2f5a00` | UnitListByFlags | (unit, state, flags) -> its stat list with those flags, or null | Returns its stat list with those flags, or null | R |
| `0x2f5df0` | ListStatValue | (dataFlag, list, stat, layer) -> value | Returns value | R |
| `0x2f65d0` | StatCallbackInit | (unit, flags, callback, arg) | Sets up the unit's stat list with its callback (unit creation 0x4252c0, 0x543120). Entry: mov [rsp+0x10],rbx / mov [rsp+0x18],rsi / mov [rsp+0x20],rdi / push rbp | R |
| `0x2f72f0` | SetListState | (list, state) | list +0x20 = state (0x49bef0, 0x339d70 use it) | R |
| `0x2f7300` | NewStatList | (flags, expire frame, unit type, unit id) -> list or null | Returns list or null | R |
| `0x2f7c20` | SetListStatOf | (dataFlag, list, stat, value, layer, unit) | (a D2RCore jump) | R |
| `0x2f81a0` | StatListLink | (parent, unit, 1) | its stat list under the parent's | R |
| `0x2f8290` | StatListUnlink | (unused, unit) | its stat list off its parent's | R |
| `0x2f84b0` | UnitStatEntries | - | How a charge use (0x4368a0) and the repair (0x46f3be) move an item_charged_skill (204) value, charges / max << 8 at layer skill << TablesSkillLayerShift / level: (unit, stat, out, max) -> count: the unit's full-stat entries of the stat, 8 bytes each {u16 layer, u16 stat, i32} | R |
| `0x300830` | DifficultyRecord | (dataFlag, difficulty) -> record | difficultylevels.txt record (0x84 bytes); StaticFieldMin at +0x68. Static Field (srvdo 20 0x5546b0, per unit 0x5556a0) builds its hit from it | R |
| `0x313ef0` | ItemRowByCode | (dataFlag, u32 code, 'wss ' = 0x20737377) -> items row, < 0 if none | Returns items row, < 0 if none | R |
| `0x324fc0` | UnitDistance | (a, b) -> distance in subtiles | Returns distance in subtiles | R |
| `0x325c50` | QuestFlag | (questRecord, quest, bit) -> non-zero when set | D2Common QuestRecord.cpp. A player's record for a difficulty is at player data + 0x40 + difficulty * 8 (the item-use quest checks in 0x4734f0). Bit 0: the quest is done | R |
| `0x3267c0` | LevelGet | - | The steps ActSpawnSpot's 0x3da650 takes from a level id to a room (D2Common Drlg): (dataFlag, act +ActDrlg, level id) -> the act's level (made if missing); (dataFlag, level) builds its rooms when level +0x10 (the first room ex) is null; (level, tile x, tile y) -> the room ex holding the tile; (dataFlag, room ex) -> its room, made if needed. A level's origin is in tiles at +0x24/+0x28. | R |
| `0x3271c0` | LevelBuild | - | Builds a level of the act's dungeon (D2Common Drlg) | R |
| `0x3275b0` | LevelRoomExAt | - | The room at a point of a built level (D2Common Drlg) | R |
| `0x3289a0` | RoomExRoom | - | Level-gen room ex step after the level-entry finder 0x3da650: reads [rdx+0x50] of the room it is given (null when the entry-room table is empty) | R |
| `0x335a40` | StateIsCurse | (dataFlag, state) -> non-zero for a curse | True when the states.txt row is a curse | R |
| `0x337da0` | ElementalLength | (dataFlag, unit, skillId, level, 1) -> ELen with ELevLen, the length ElementalDamage gives cold and poison | Returns ELen with ELevLen, the length ElementalDamage gives cold and poison | R |
| `0x338160` | SkillPhysMax | (dataFlag, unit, skillId, level, 0) | The skill's own physical max in 1/256, the partner of SkillPhysMin | R |
| `0x3385b0` | SkillPhysMin | (dataFlag, unit, skillId, level, 0) -> min in 1/256 | The skill's own physical min / max (MinDam/MaxDam with MinLevDam...; a kick's from strength and dexterity), the pair MeleeFill reads; 1.13c's D2Game 0x9f1a0 adds min + rand(max - min) to the hit's physical damage. SkillPhysMax is the max | R |
| `0x339040` | SkillToHit | (unit, skillId, level) -> attack rating for the roll | Returns attack rating for the roll | R |
| `0x33d1e0` | UnitSkillLevel | (unit, unitSkill, bonus) -> level | bonus 0 = hard points | R |
| `0x33d4f0` | MasteryBonus | (unit, weapon, 0, kind) -> the weapon mastery's bonus | kind 2 is the crit chance (D2RCore jumps it at its entry) | R |
| `0x33dd40` | GetUnitSkill | (unit, skillId, 0) -> the unit's skill (flags +0x14) or null | Returns the unit's skill (flags +0x14) or null | R |
| `0x33e080` | UnitSkillId | (unitSkill, file, line) -> skill id | The skills.txt id of a unit skill | R |
| `0x33e380` | LeapStart | (unit, unitSkill) -> non-zero | leap path to the skill's point, type 9 | R |
| `0x340e70` | PathSteer | (path, unit, 0, 1) | re-aim the path at its target unit | R |
| `0x342740` | PathSetCollisionMask | (path, mask) | path +0x64, what the path collides with (1.13c D2Common #11164, +0x50); missile create 0x5371a0 sets it from CollideType's row of the mask table 0x2391378 (CollideType 3: 0x184) | R |
| `0x342920` | PathSetTargetUnit | (path, unit) | path +0x70 target unit | R |
| `0x342a50` | PathSetTargetXY | (path, x, y) | path +0x10/+0x12 target point; clears +0x70 | R |
| `0x342ae0` | PathSetVelocity | (path, velocity) | ignored while the skill has flag 0x1000 | R |
| `0x348650` | UnitInReach | (unit, target, reach, 0) -> non-zero when in reach | Returns non-zero when in reach | R |
| `0x349020` | SetOverlay | (unit, overlay, layer) | overlay.txt row as stat 0xb2 on the given layer; 1.13c's D2Common #10689 has no layer (0). Asserts on a row past the table, so check DataTables + TablesOverlayCount first, as Leap Attack (0x56b170) does. | R |
| `0x349560` | UnitFrame | (unit) -> animation frame (+0x5c >> 8) | Returns animation frame (+0x5c >> 8) | R |
| `0x3495d0` | UnitHitClass | (unit) -> the value Leap Attack puts at DmgHitClass | Returns the value Leap Attack puts at DmgHitClass | R |
| `0x34aa90` | UnitReach | (unit) -> 1 for a player, 3 for a monster | Returns 1 for a player, 3 for a monster | R |
| `0x34b000` | ClientUnitWeapon | (unit) -> the client's weapon item, or null | Returns the client's weapon item, or null | R |
| `0x34b240` | UnitPlayerData | (player) -> player data | its pet table at +0x98 | R |
| `0x34b4a0` | NextUnitInRoom | (unit) | Next unit in a room's list | R |
| `0x34b580` | UnitSize | (unit) -> collision size | a missile's row Size, 2 for a player | R |
| `0x34b6c0` | UnitStateKey | (unit) -> value Frozen Armor passes to 0x435920 | Returns value Frozen Armor passes to 0x435920 | R |
| `0x34ba40` | CurrentSkill | (unit) -> unit skill or null | The unit skill the unit is using. D2R's Inferno (srvdo 19 0x554460 -> 0x551730, cltdo 24 0x2203f0) and Nest (srvst 49) keep their channel and spawn data on it | R |
| `0x34c2c0` | UnitDead | (unit) -> non-zero when dying or dead | Returns non-zero when dying or dead | R |
| `0x34d8c0` | SetUnitAnimSpeed | (unit, n) | +0x64 = n << 8 | R |
| `0x34d990` | SetUnitFrames | (unit, n) | +0x4c = n << 8, keeping its low byte | R |
| `0x34da20` | SetUnitFrame | (unit, frame) | +0x5c and +0x60 = frame << 8 | R |
| `0x34da60` | SetMissileAnimRange | (missile, MsAnimSpeed << 8 / range) | cltdo 24 calls it on each flame it draws | R |
| `0x34e140` | SetUnitFlag | (unit, flag, on) | Sets or clears a bit of the unit's flags | R |
| `0x34e190` | SetUnitFlags | (unit, flags, on) | unit flags +0x124 (bit 0x10000 is dead, see UnitDead); 0x20000 is 1.13c's no-treasure-class bit | R |
| `0x34e5f0` | SetObjectMode | (object, mode) | Puts an object into a mode | R |
| `0x3525c0` | ActLightSet | - | An act's eclipse, the way the Tainted Sun quest (a2q3.cpp 0x5a7370) darkens act II. ActEclipseOn: (dataFlag, act) eclipse on (1.13c D2Common #10337). ActLightSet: (dataFlag, act, room or null, period, time, eclipse) sets the act's light, as the client's packet 0x53 handler (0x12cb50) does; period 2, time 0, eclipse 0 is 1.13c #10895's eclipse off, which also puts back the speed (EnvSpeedNormal) and clears the pause. The act's light at act +8: period +0, speed +0x2c, pause +0x30, eclipse +0x34 (0x351df0 reads it). A unit's act at unit +0x20 (0x34a1a0). | R |
| `0x3526f0` | ActEclipseOn | - | An act's eclipse, the way the Tainted Sun quest (a2q3.cpp 0x5a7370) darkens act II. ActEclipseOn: (dataFlag, act) eclipse on (1.13c D2Common #10337). ActLightSet: (dataFlag, act, room or null, period, time, eclipse) sets the act's light, as the client's packet 0x53 handler (0x12cb50) does; period 2, time 0, eclipse 0 is 1.13c #10895's eclipse off, which also puts back the speed (EnvSpeedNormal) and clears the pause. The act's light at act +8: period +0, speed +0x2c, pause +0x30, eclipse +0x34 (0x351df0 reads it). A unit's act at unit +0x20 (0x34a1a0). | R |
| `0x3636d0` | ClearSpawnSpot | (room, x, y, 1, 0x100) | Nest calls it before spawning | R |
| `0x366250` | CollisionAt | (room, x, y, mask) -> bits set | The mask's bits set at subtile x/y (0x27 with no room there); 1.13c's single-point test | R |
| `0x36b410` | ItemSocketable | (item) -> non-zero | can take sockets (1.13c D2Common #10360) | R |
| `0x36c750` | ItemHasSockets | (item) -> non-zero when socketed | cube input flags 4 / 8 test it | R |
| `0x36cc80` | ItemSeed | (item) -> &its item seed {lo, hi}, which item rolls draw from (not the unit seed, UnitSeed) | Returns &its item seed {lo, hi}, which item rolls draw from (not the unit seed, UnitSeed) | R |
| `0x36ccf0` | ItemLevel | (item) -> item level (the matcher's out, 0x529d50) | Returns item level (the matcher's out, 0x529d50) | R |
| `0x36d730` | SetItemStorePage | (item, page) | item data +0x54 | R |
| `0x36d8f0` | SetItemFlag | (item, flag, on) | item data +0x18 flags (0x400000 ethereal) | R |
| `0x36de20` | SetItemPage | (item, page) | item data +0x55 (ItemPage); 0xff socketed | R |
| `0x36e2d0` | ItemTestFlag | (item, flag, line, file) -> non-zero when item data +0x18 has it | Returns non-zero when item data +0x18 has it | R |
| `0x36e880` | SetItemSockets | (item, n) | sockets, clamped to the type's max (1.13c #10599) | R |
| `0x36ef50` | ItemCode | (item) -> code dword | The items.txt code as a dword ('box ' = 0x20786f62) | R |
| `0x371b60` | ItemMissileType | (item) -> row | The weapons.txt missiletype row | R |
| `0x371d00` | ItemOwnerId | (item) -> the owner's unit id (item data +0xc), -1 for none | Returns the owner's unit id (item data +0xc), -1 for none | R |
| `0x372b80` | StaffModsClass | (item) -> itemtypes StaffMods class (0-6, 7 Warlock), or >7 | Returns itemtypes StaffMods class (0-6, 7 Warlock), or >7 | R |
| `0x3730d0` | ItemVersion | (item) -> version | 0 classic, 100 or more expansion (1.13c ordinal 10718) | R |
| `0x3740a0` | ItemIsEthereal | (item) -> non-zero when ethereal | cube input flags 0x10 / 0x20 | R |
| `0x37a451` / `0x37a47c` / `0x37a4a7` / `0x37a4d2` / `0x37a4fe` / `0x37a52a` | DecodeEtherealDamage[] | - | Item decoder (0x378860): the first of six sites that times a weapon's base damage by 3/2 when ethereal, stats 21-24, 159, 160; the others are `0x37a47c`, `0x37a4a7`, `0x37a4d2`, `0x37a4fe`, `0x37a52a` | P |
| `0x3856e0` | PlaceInSocket | (parent's inventory, item, 1) -> non-zero | in a socket | R |
| `0x3861c0` | CreateInventory | (item) | gives the item an empty inventory | R |
| `0x38ba30` | InventoryRemove | (item) -> non-zero | out of whatever inventory holds it | R |
| `0x38ebf0` | QueueUnitUpdate | (unit) | flags it (+0x124 bit 0x2000) for its room's update list; D2R's srvst 63 calls it on the corpse it takes | R |
| `0x38fd00` | ObjectRecord | (dataFlag, objects row) -> objects record (0x168 bytes) or null | Returns objects record (0x168 bytes) or null | R |
| `0x397290` | TcRecord | (dataFlag, u16 index, 0) -> compiled TreasureClassEx or null | Returns compiled TreasureClassEx or null | R |
| `0x3ba820` | MissileCritRoll | (unit, weapon) -> bool | a missile's crit or deadly strike, rolled by the missile fill 0x3bf9b0 (D2Common Missile.cpp) and the server's 0x432f90 / 0x4333f0; a hit doubles the physical part of a missile that carries it. mov [rsp+8],rbx / mov [rsp+0x10],rsi / push rdi / sub rsp,0x20 | H |
| `0x3bae80` | MissileActivateFrame | (missile) -> frame | 1.13c's data +0x08 (D2R +0x0a) | R |
| `0x3bc0a0` | MissileBounces | (missile) -> chain count left (Chain Lightning's) | Returns chain count left (Chain Lightning's) | R |
| `0x3bc190` | MissileTargetType | (missile) -> target unit type, 6 for none | Returns target unit type, 6 for none | R |
| `0x3bc280` | MissileTargetId | (missile) -> target unit id | Returns target unit id | R |
| `0x3bda20` | SetMissileTargetDx | (missile, tx - ux) | , set by srvdo 139 (0x585440) | R |
| `0x3d3420` | ApplyCubeMod | (item, &property {prop, param, min, max}) | a cube output mod on the item's magic list (mod type 7, 1.13c #10914) | R |
| `0x3d3510` | ItemApplyEthereal | (item) | sets the ethereal flag, then base stats times 3/2 (1.13c's D2Common #10890). Callers: the drop 0x442d60, the ethereal property 0x3ccc60, the cube output 0x5269c0. mov [rsp+0x10],rbx / push rdi / sub rsp,0x20 / mov rbx,rcx / test rcx,rcx | H |
| `0x3d4220` | AffixAllowed | (item, affix record) -> non-zero when the magicprefix/suffix record may roll on the item (item types, level 100+ rules) | both affix pickers (0x58c940, 0x58ce80) call it for each candidate, after the picker's own 'rare' test (record +0x64, a flag in D2R: 0 bars quality 6, 8 and 9). mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x18],rsi / mov [rsp+0x20],rdi | H |
| `0x3d4950` | ChargedSkillList | (item, skill, level, &charges, &list) -> non-zero | the item's list that holds the charged skill (a D2RCore jump) | R |
| `0x3d5860` | ItemRandom | (item, min, max) -> value | A value from min to max, drawn from the item's seed | R |
| `0x3d5940` | PropertySetStat | (dataFlag, a1, a2, item, Property*, set, stat, layer, value, a8, a9, a10) | put one stat on the item's list, as every D2R property function does (value shifted by the stat's ValShift) | R |
| `0x3e3f20` | CubeRecipeCount | (dataFlag) -> cubemain row count | Returns cubemain row count | R |
| `0x4061e0` | GameKey | (u16 id) -> key, 0 for an empty slot | Returns key, 0 for an empty slot | R |
| `0x4062f0` | GameById | (key) -> game or null | Returns game or null | R |
| `0x40fc39` | SpawnCheatKey | - | The 'cheat spawn' handler 0x40f670 builds its item-code key the same way (0x40fc39-0x40fc6e: the first 3 characters, spaces after a short code, a space in byte 3), then compares it with each item record's code (+0x80), so a 4-character code spawns nothing. On entry r8 holds the lowered code and cl its first character; 0x40fc6e is the compare loop. D2R's bytes are SpawnCheatKeyD2R. | P |
| `0x4242b0` | UnitWeapon | (unit) -> weapon item the server attacks with, or null | Returns weapon item the server attacks with, or null | R |
| `0x4251e0` | PlayerCount | (game) -> players, at least the /players setting | Returns players, at least the /players setting | R |
| `0x42d700` | HitRecoveryGate | - | Mode-change gate for a player in get-hit, block or knockback (modes 4, 9, 0x13), called by 0x42bfb0 (game, unit, requested mode, flag byte) -> 0 allow, 1 refuse, 4 buffer | H |
| `0x42d7d2` | HitRecoveryWindowBuffer | - | The immediates of its two "mode end - game frame > 1" tests (cmp eax,1): walk / run -> buffer, the rest -> refuse | P |
| `0x42d808` | HitRecoveryWindowRefuse | - | Patch address: the refuse-window immediate of the hit recovery gate | P |
| `0x42d840` | BusyModeGate | - | Mode-change gate for a busy player | H |
| `0x42e600` | PlayerRegenEvent | (game, player, a, b) | the player's life regen event (unit event 3, D2Game\src\Player\PlrModes.cpp). It adds itself again for the next frame first, so it runs every frame for every player, dead or alive. mov [rsp+0x20],rbx / push rbp / sub rsp,0x40 / mov eax,r9d / mov dword [rsp+0x30],0 | H |
| `0x42eea0` | AuraEvent32D2R | - | D2R's own function in aura event slot 32 | R |
| `0x42fa90` | RegisterSkillEvents | - | srvstfunc 66: (game, unit, skill, level) -> 1, registers the skill's auraevent1-4 / auraeventfunc1-4 on the unit for good (no stat list, no source), through 0x588670 and 0x438230 per event | R |
| `0x4331d0` | NearestTarget | (game, owner, x, y, range, flags, skip unit id, 0) -> nearest target to x/y other than the skipped unit, or null | Returns nearest target to x/y other than the skipped unit, or null | R |
| `0x4333f0` | ThrowSkillMissile | (game, missile, unit, skill, level, UnitStateKey(unit), 0, 0, 0, 0, 1) -> missile | Throws a missile at the skill's target | R |
| `0x435920` | StateListKey | (dataFlag, list, key) -> stat 202 value | Returns stat 202 value | R |
| `0x436e90` | AreaApply | (game, attacker, victim, &damage) | Applies an area hit's damage block to one victim | R |
| `0x4370b0` | RemoveSkillState | (unit, state, self) -> 1 if any removed | Removes every state of the unit in the same states.txt group as `state` (the state itself too with self 1). A state with no group (0) removes nothing | R |
| `0x437230` | ItemAuraTick | - | Unit event 9's handler, (game, unit, key, skill, stateKey): an item aura's tick. Casts the skill at item_aura's level for it (stat 151, layer skill) through SrvSkillDispatch (unit flag 0x20000000 and UnitStateKey = stateKey around the cast), then re-adds the event perdelay (calc +0x180, at least 5) frames on, on the frame grid; with no item_aura level (or a dead unit, or no aurastate) it removes the event. The item_aura case (0x581970) starts it. mov [rsp+0x20],rbx / push rbp / push rsi / push rdi / push r12 / push r14 / sub rsp,0x40 | H |
| `0x437820` | AreaKnockback | (game, unit, 0, 0, radius, &LeapKnockback, 0, &scratch) | Leap's landing knockback (srvdo 77), callback 0x43a740 | R |
| `0x437980` | AddElementDamage | (unit, &damage, etype, amount, length, &resist stat or null, &etype or null) | adds amount to the etype's field (2 lightning: +0x2c, hit class +0x144 = 0x40; resist stat 41) | R |
| `0x4398b0` | AreaUnits | (game, unit, &AreaCenter, radius, unit mask, callback, arg, 0) | callback(&AreaContext, victim) for each unit in range | R |
| `0x43cd50` | ItemSpawn | (game, drop, 0) -> item or null | makes an item from a drop request (1.13c's same function). The TC drop 0x444680 (game, unit, item row, quality, index, flags) fills the request and calls it at 0x444866. push rbp / push rbx / push rsi / push r12 / push r15 / lea rbp,[rsp-0x37] / sub rsp,0x90 | H |
| `0x43ea10` | ScheduleReplenish | - | Replenish (D2Game\src\Items\ItemMode.cpp). Item event 3 replenishes: (game, item) schedules it 2500 / stat + 1 frames on for item_replenish_durability (252), unless one is pending; the equip 0x46eb00 and the durability loss 0x441b10 call it, each beside its replenish_quantity (253) twin 0x43eaa0. The handler (game, item, ...) adds one durability or quantity (0x46f4f0) and schedules the next, at least 125 frames on. mov [rsp+8],rbx / mov [rsp+0x10],rsi / push rdi / sub rsp,0x40 | H |
| `0x4404f0` | TcDrop | (game, dropper, killer, TC record, quality, item level, 0, items* or 0, count* or 0, max) | rolls the TC and drops its picks by the dropper; with no items array it drops all picks (max under 1 means 6). The item level feeds the quality roll 0x4421b0. 1.13c's same function takes (..., tc, 0, ilvl, 0, 0, 0, 1). | R |
| `0x441b83` / `0x441ba6` | WeaponDurabilityChance[] | - | Weapon durability loss per hit (0x441b10): `mov ebx,4`, the chance (percent) for most weapons; `0x441ba6` is the same with `mov ebx,0xa` for the item types that take 10 | P |
| `0x444680` | DropItemAt | (game, unit, items row, quality, set/unique row + 1, flags) | drops the item by the unit at its item level, as the TC roller 0x4404f0 does | R |
| `0x44486b` | TcDropReturn | - | the TC drop's return address from ItemSpawn | P |
| `0x4471e0` | ModeCmdInit | (unit, mode, &cmd) | Fills the mode command AiIdle sends (cmd +0x10 the unit); ModeCmdRun runs it | H |
| `0x4475c0` | ModeCmdRun | (game, &cmd, 1) | Runs the mode command ModeCmdInit filled, as AiIdle does | R |
| `0x447b80` | MonsterTcDrop | (game, monster, flag, death*) -> the monster's own TC drop | its monstats TC for the difficulty and kind (champion, unique, quest), dropped by 0x441300. death +0x08 is the monster, +0x10 the killer (the quest-drop test and the quality roll's player). 1.13c's 0x6fc95680; D2R's death path 0x4479a0 passes flag 0. | R |
| `0x44b600` | QueueHit | (game, attacker, target, hit) | Queues a melee hit on the attacker's unit +0x108 list | H |
| `0x44b720` | MeleeRoll | (game, unit, target, toHit, flag, 0) -> result flags (bit 0 hit) | flag = skill byte SkRollFlags & the byte at MeleeRollFlagMask | R |
| `0x44b930` | AvoidRoll | (game, attacker, victim, 1, 0) -> 1 avoided, 2/4/0x10 block kinds | Returns 1 avoided, 2/4/0x10 block kinds | R |
| `0x44c2b4` | WeaponCritBlock | - | WeaponDamage's (0x44c030) roll: from 0x44c2b4, right after the physical roll is stored at damage +0x18, to 0x44c3d9 it rolls the weapon mastery's crit (when a5 is 0), passive_critical_strike, then deadly strike, and doubles the physical part with result flag 0x2000. Attacker in RSI, damage block in RDI, a5 in R14D; 0x44c3d9 needs R15D 0. The 28 bytes of the block: test r14d,r14d / jnz / mov rcx,rsi / call UnitWeapon / test / jz / lea r9d,[r14+2] / xor r8d,r8d / mov rdx,rax (nothing outside jumps into them). | P |
| `0x44c3d9` | WeaponCritBlockEnd | - | End of the WeaponCritBlock, where the roll rejoins | P |
| `0x44d660` | QueuedHit | (attacker, defender) -> the damage block of the attacker's queued hit on defender (unit +0x108 list), or null | Returns the damage block of the attacker's queued hit on defender (unit +0x108 list), or null | R |
| `0x44df10` | DamageEffects | (game, attacker, victim, &damage) | 0x44ce80 runs it for area hits | R |
| `0x451820` | AddLife | (unit, amount) -> life added | life + amount up to the max, unless the unit is dead or has state 92. Callers: the life leech 0x450c90 (attacker) and the hit's absorb heal in 0x44ce80 (victim). mov [rsp+0x18],rbx / push rsi / sub rsp,0x20 / mov esi,edx / mov rbx,rcx | H |
| `0x4518c0` | PoisonApply | - | type: +0 the int32* damage field; +0x28 int32 non-zero on the 9 types 1.13c flags (physical, fire, lightning, cold, magic, poison and the three leeches; not the cold, freeze and poison lengths) (attacker, victim, rate, length, a5, a6, a7): poison, stat 74 (hpregen) at -rate for length frames. Its entry tests the length (test r9d,r9d / jle, relative); a hook sits past it, at PoisonApplyHook, with the arguments still in place: mov rax,rsp / push rbp / push rsi / push r14 / push r15 / sub rsp,0x68 / mov r14d,r9d | R |
| `0x4518c9` | PoisonApplyHook | - | type: +0 the int32* damage field; +0x28 int32 non-zero on the 9 types 1.13c flags (physical, fire, lightning, cold, magic, poison and the three leeches; not the cold, freeze and poison lengths) (attacker, victim, rate, length, a5, a6, a7): poison, stat 74 (hpregen) at -rate for length frames. Its entry tests the length (test r9d,r9d / jle, relative); a hook sits past it, at PoisonApplyHook, with the arguments still in place: mov rax,rsp / push rbp / push rsi / push r14 / push r15 / sub rsp,0x68 / mov r14d,r9d | P |
| `0x45ddb0` | SrvHitSubMissiles | - | srvhit 4 (game, missile, hit): HitSubMissile1-4 at the missile | R |
| `0x462b20` | MissileFireDisc | - | srvhit 9's (Immolation Arrow, 0x45d020) helpers: (game, missile, radius, missile row, frames) creates the row at every open spot within radius of the missile (frames 0 = the row's own range), and (game, missile, hit, &block) fills the missile's damage into a d2r::LeapKnockback block | R |
| `0x463100` | MissileSrvDoDefault | - | srvdo 1 (game, missile): move, collide, count down range | R |
| `0x4639a0` | MissileSrvEnd | (game, missile, hit, 1) | what srvdo 1 does when range runs out | R |
| `0x465d60` | MissileDamageFill | - | Fills a missile hit's damage block | R |
| `0x46e8c0` | IdentifyItem | (game, player, item, 1) | Identifies the item and tells the client | R |
| `0x46fdd0` | StatCallback | - | The server's stat callback, (game, unit, item, stat << 32 / layer (a 64-bit r9), old, new), for stats with fCallback: a switch on stats 7-209 only ('lea eax,[r12-7]; cmp eax,0xca' at 0x46ff4a), item_aura (151) at 0x470470. Its entry is 'jmp [rip+x]': D2RCore hooks it, so wrap the pointer handed to StatCallbackInit instead. | R |
| `0x476060` | ReplenishEvent | - | mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x18],rsi | H |
| `0x477420` | SendPacket10 | (client, packet) | sends a 10-byte packet, a2q3's 0x53 {0x53, int period, int time, byte eclipse} (0x5a4290). The game's light tick 0x406550 sends the same packet to an act's clients when its light changes. Client +4: 4 in game. | R |
| `0x477a30` | SendChat | (*(game + GameClients), packet) | Sends a chat packet 0x26 (type at +1, unit type +3, unit id +4, colour +8, name at +10 up to 60 bytes, text at +0x47 up to 255) to the game's clients; it breaks on longer text. D2R's own GameChat (0x4016c0, the debug commands' "Warping to level") sends type 1 with unit type 2, which the client drops; type 4 or unit type 0 shows | R |
| `0x47a190` | SendUnitStat | (client, unit, 1, stat, value, layer) | sends the unit's stat to the client, as the charge use does | R |
| `0x484c90` | ClientUnit | (client, 0) -> its player | The game's clients are a list at game +0x138, the next client at +0x628 (0x484d90 walks it); this gives a client's player | R |
| `0x488180` | WarpToLevel | (game, player, level, 0) | moves the player into the level (D2Game\src\Game\Clients.cpp). In the same act it finds the level's arrival spot (ActSpawnSpot) and teleports there (TeleportUnit); else it changes act. The debug "Warping to level" handler 0x402820 calls it. | R |
| `0x489b70` | InTerrorZone | (game, level id) -> bool | the level is in the active Terror Zone | R |
| `0x48b230` | UnitEventFrame | (game, unit, event type, 0) -> earliest frame of the unit's timer events of that type (1 = mode end), 0 for none | Returns earliest frame of the unit's timer events of that type (1 = mode end), 0 for none | R |
| `0x48b720` | AddUnitEvent | (game, unit, event, frame, key, skill, stateKey) | zeros for most; item aura ticks (0x437419) pass them | R |
| `0x48b890` | RemoveUnitEvent | (game, unit, event, key) | 0 for most; an item aura passes its key | R |
| `0x48e820` | NestHold | (unit, 0) | Nest calls it before spawning; sets state 54 to the value | R |
| `0x48faa0` | RemoveUnit | (game, unit) | Removes a unit from the game | R |
| `0x48fde0` | PlayerClient | (player) -> its client; (player, client) | Player data +0xf0 holds the client (null for a non-player). How the chest operate plays its unlock sound: rva::ClientMessage(player, 0xb, player), then it sends the sound packet 0x2c to the client | R |
| `0x48fe80` | FindUnit | (game, unit type, id) -> unit or null | Returns unit or null | R |
| `0x4926b0` | PresetSpawn | (game, room, preset) | Spawns one room preset unit (1.13c D2Game 0x6fd013b0) through 0x48dc50 (1.13c 0x6fd012d0; type 1 goes to 0x50a050). The room's preset loop 0x48f190 (1.13c 0x6fd01430) is its only caller. Preset: +4 int32 id (a monstats id for a monster), +0x20 int32 unit type. A room's subtile rect, as 0x2f0680 (does the room hold x/y) reads it: int32 x, y, width, height. Entry: push rbx / push rsi / push rdi / sub rsp,0x80 | H |
| `0x494a60` | MonsterSpawned | (spawn params, monster) | D2R's per-class setup of a monster that its spawn core 0x493cc0 (D2Game\src\Monster\MonsterSpawn.cpp) just made; 0x493cc0 is its only caller, and 0x492cf0 and the other spawners all go through 0x493cc0. The monster's stats and its monstats Align alignment (0x48e600) are set by then. mov [rsp+0x18],rbx / mov [rsp+0x20],rbp / push rsi / push rdi / push r15 | H |
| `0x4a6d10` | AiIdle | (game, unit, frames) | mode neutral, think again after frames | R |
| `0x4a6e50` | AiSetDelay | (game, unit, frames) | think again after frames, mode kept | R |
| `0x4a78e0` | AiAttack | (game, unit, mode, target) | melee in mode 4 (A1) or 5 (A2) | R |
| `0x4a7bc0` | AiUseSkill | (game, unit, mode, skill, target, x, y, 0) -> non-zero once cast | Casts a skill from a think; on failure it idles 10 | R |
| `0x4a8740` | AiApproach | (game, unit, target, 0) | walk at the target | R |
| `0x4ff1a0` | FirstPet | (game, owner, pet type, 1) -> the type's first pet, or null | Returns the type's first pet, or null | R |
| `0x4ffd30` | RemovePet | (game, owner, pet id, 1) | takes the pet off the list and kills it, as the pet add's loop over a group does | R |
| `0x5013f0` | PetEntry | (dataFlag, pet table, pet type) -> the type's entry (stride 0x20) | Returns the type's entry (stride 0x20) | R |
| `0x508f80` | AreaMonsterLevelFn | (game, level id) -> monster level | The level's monster level: levels MonLvl / MonLvlEx of the difficulty (0x32c700), plus a terror zone's bump (MonsterRegionAdjustMonsterLevel). Monster spawns, uniques and item levels call it; D2R never reads the region's own monster level fields (+0x2dc, +0x2e0). GameMonRegions: 0x5098b0 builds every level's region once per game (0x508750), from its levels row. Entry: mov [rsp+0x10],rbx / mov [rsp+0x18],rsi / push rdi | R |
| `0x50a050` | SpawnMonsterAt | (game, room, monstats id, x, y, mode, 0) -> monster or null | srvhit 6's spawn at the missile | R |
| `0x50acf0` | RoomPopulate | (game, room) | spawns a room's monsters as it activates (1.13c D2Game 0x6fc67a20). Its first call (1.13c 0x6fc66cd0) counts the room in its level's monster region at +0x04. mov r11,rsp / push rbx / push rsi / sub rsp,0xb8 | H |
| `0x52922a` | CubeNumInputsJump | - | The numinputs filter of the cube search: a 6-byte jne on the item count (original bytes: CubeNumInputsJumpOrig in items.h); a 6-byte nop over it lifts the filter | P |
| `0x5396d0` | SendChargePacket | (unit, target, skill, level, seed, 0, charges) | the release packet an assassin charge-up skill sends after each hit | R |
| `0x5397f0` | SoundPacket | - | Sends a sound packet to a client | R |
| `0x5551f0` | SkillStateExpired | - | Frozen Armor's expiry callback: removes the state | R |
| `0x55a7e0` | ApplyCurse | - | D2Game\src\Skills\SkillNec.cpp: puts one curse on one unit, (target, &CurseParams) -> 1 applied. Every curse skill's srvdo reaches it once per target. It calls NewStateList (whose own entry D2RCore hooks), which removes the unit's first list flagged ListFlagCurse unless it is this state's, then sets aurastat2-6 on the list. mov [rsp+8],rbx / mov [rsp+0x18],rbp / mov [rsp+0x20],rsi / push rdi | H |
| `0x55bfb0` | CurseStatValue | (game, target, stat, value) -> value | what ApplyCurse sets for each aurastat (a fifth of a resist cut on an immune) | R |
| `0x55e7e0` | SrvDoReviveD2R | (game, unit, skillId, level) | D2R's own srvdo 58 (Revive); the expected value when SrvDoRevive's slot is wrapped | R |
| `0x564930` | SrvDoSmiteD2R | - | srvdofunc 150, Smite (also the monster Smites): builds the hit on its stack, QueueHit, then ApplyMeleeHit | R |
| `0x56b170` | SkillMeleeHit | (game, unit, skillId, level) | Leap Attack's hit on the skill target | R |
| `0x56b5e0` | LeapLanded | (game, unit, unitSkill) -> non-zero once the unit has landed | Returns non-zero once the unit has landed | R |
| `0x56c3e0` | SrvPrgDispatch | - | Release dispatcher (srvdo 1, 42, 46, 50, 52 call it with the queued hit): for each progressive state, n = min(max(charges, 1), 3) at max(list level, skill level); with prgstack it calls srvprgfunc1..n-1 first, setting the charge stat to i, then srvprgfunc n, all as (game, unit, skill, level), and sends SendChargePacket. | R |
| `0x56dae0` | AddCharge | (game, unit, skill, level, aurastate, aurastat1) -> 1 | one charge on the aurastate list (made with stats 350/351 if none), capped at 3, timer reset to auralencalc; aurastat2 grows by aurastatcalc2. srvdo 34 calls it on a hit. | R |
| `0x571700` | PickSkillMissile | (unit, skillId) -> missile row | The srvmissile a/b/c row by the skill's charges (1, 2, 3+), srvmissilea for a skill with no charges, -1 on error (vanilla's charge-missile helper; D2R's srvdo 37 uses it) | C |
| `0x573af0` | MeleeFill | (game, &block, unit, target, skill, level) | the hit's damage for a kick, into a damage block with DmgPercent set; D2R's srvdo 52 (0x56fc80) fills its kick with this after the roll (MeleeRoll) | R |
| `0x574480` | AddAuraStats | (unit, list, skillRecord, skillId, level) | aurastat1-6 (attackrate also sets stat 69) | R |
| `0x574600` | AddAuraStatsB | (unit, list, skillRecord, skillId, level) | AddAuraStats' partner with the same arguments; Frozen Armor calls both | R |
| `0x581bd0` | CrushingBlowApply | (game, unit, target, &CrushingBlowArgs) -> the event's result | called by D2R's event 16 after its roll | R |
| `0x583150` | AuraEvent16D2R | - | Slot 16 is D2R's crushing blow (item_crushingblow): chance = the stat at (skill >> 16, layer skill & 0xffff), roll % 100 on the unit's seed, then CrushingBlowApply (damage.h). | R |
| `0x5889e0` | DamageStep | (attacker, victim, &damage) | One step of DamageEffects' damage-type pass | R |
| `0x5896e0` | CastEventSkill | (unit, skill, level, target, 0) -> non-zero cast | a skill cast from unit at target as an event, sent to clients (aura event 33 0x42f300 casts this way); refuses while the unit has state 54 | R |
| `0x58a050` | ItemStaffMods | - | The staffmods roll on a new item (0x58a050, D2Game\src\Items\ItemsMagic.cpp; 1.13c D2Game +0x13de0): (item, drop params). It reads the itemtypes StaffMods class and that class's skill count, then rolls 1.13c's tiers in 0x58af50 (DropFlags 0x20 adds the item level as bonus) or, on a version-0 item, 0x58b7c0. Entry: mov [rsp+0x10],rbx / push rbp / push rdi / push r14 / sub rsp,0x30 / mov rdi,rdx | H |
| `0x58e2f0` | OperateChestFn | - | D2R's chest operate (OperateFn 4, D2Game\src\Objects\ObjMode.cpp): mode 0 only; it sets mode 1 with event 1 at the open frames (or mode 2), plays sound 0xb for a locked chest, then drops the act's chest TC. | R |
| `0x5a8450` | PrimesDrop | - | D2R's own drop on the three prime evils' deaths (1.13c 0x6fd0aa30, D2Game\src\Quests\QuestsFX.cpp): it flags 704/705/709 dead in the game and, once all three are, drops the Hellfire Torch and a Standard of Heroes per player. The unique-monster death switch 0x4a1480 tail-calls it (0x4a1645). A ret (0xc3) written over the first byte makes it return at once. | P |
| `0x5a8b80` | AiBaalCrab | - | Baal crab think function (monai row) | R |
| `0x5b1ca0` | AiMephisto | - | Mephisto think function (monai row) | R |
| `0x5b3040` | AiRegurgitator | - | Row 71's think, read from the table; its state opens with the same "state 5: idle 0x10" as 1.13c's 0x6fca3fe0 | R |
| `0x5b5ca0` | AiTrapMelee | - | row 87's think: melee by aip1, else idle aip2 | R |
| `0x5bae30` | AiHide | - | D2R's own hide and unhide, 1.13c D2Game 0x7be10 / 0x89730, as the FrogDemon (monai 52, 0x5afb80) and Vulture (23) thinks call them. Hide (game, unit): unit flags 0xe off, the room's collision 0x1000 and 0x100 at the unit cleared, path mask 0, think in 12. Unhide (game, unit) -> 0 when the unit has no room to stand: flags 0xe on, the unit placed (TeleportUnit), collision 0x100 marked, path mask 0x3c01, think in 12. | R |
| `0x5bafb0` | AiUnhide | - | D2R's own hide and unhide, 1.13c D2Game 0x7be10 / 0x89730, as the FrogDemon (monai 52, 0x5afb80) and Vulture (23) thinks call them. Hide (game, unit): unit flags 0xe off, the room's collision 0x1000 and 0x100 at the unit cleared, path mask 0, think in 12. Unhide (game, unit) -> 0 when the unit has no room to stand: flags 0xe on, the unit placed (TeleportUnit), collision 0x100 marked, path mask 0x3c01, think in 12. | R |
| `0x5c2290` | AiOverseer | - | row 120's think | R |
| `0x5c8d40` | AiDiablo | - | Diablo think function (monai row) | R |
| `0x5cfb20` | AiTrappedSoul | - | row 99's think, read from the table | R |
| `0x5e5a91` | SealSweepKillReturn | - | The Chaos Sanctuary sweep (0x5e5990, D2Game\src\Quests\a4q2.cpp; 1.13c's D2Game +0xbb3b0): once the fifth seal opens, it kills every monster but Diablo (243) in level 108's rooms, each through ModeCmdInit (unit, 0, &cmd) at 0x5e5a8c, then ModeCmdRun. This is the return address of that kill call. | P |
| `0x6639f9` | ItemsJsonKey | - | Patch address of the items.json item code key builder | P |
| `0x9041a0` | LoadActPalette | (act byte) -> void | loads data/global/palette/act<N+1>/pal.pl2 (legacy floor, light and colormap tables) and updates the palette texture. Only the load screen's end calls it with a level's palette (0xc5f80 passes the act palette), so a level entered without one keeps the last act's. SetActPalette sets that palette. | R |
| `0xa121f0` | TcIndexByName | (name map, name, 0) -> compiled index, > 0 when found | Returns compiled index, > 0 when found | R |
| `0x12063c0` | EngineAllocator | () -> allocator | The engine allocator object; vtable +0x20 frees a block (Leap Attack's cleanup) | C |
| `0x1215650` | TlsfBlockInsert | (control, block) -> void | Returns void | R |
| `0x122ad60` | EntityPoolLock | (lock*) -> void | Returns void | R |
| `0x122ad90` | EntityPoolUnlock | (lock*) -> void | Returns void | R |
| `0x1d1b650` | DirectionX | - | int32[64] x and y offsets of D2's 64 directions (radius 30), the ones Nova's srvhit 5 (0x45fd20) aims at | D |
| `0x1d1b750` | DirectionY | - | Data: int32[64] y offsets of D2's 64 directions, next to DirectionX | D |
| `0x1d996d0` | MeleeRollFlagMask | - | Data: int32 flag mask MeleeRoll reads with the skill byte | D |
| `0x1d996e4` | SkillTickMaskA | - | int32 masks ItemAuraTick tests the skill record's byte +0x24 with: either set, the aura ticks again | D |
| `0x1d996e8` | SkillTickMaskB | - | int32 masks ItemAuraTick tests the skill record's byte +0x24 with: either set, the aura ticks again | D |
| `0x235f590` | CltStTable | - | Client skill "start" functions (cltstfunc): 70 slots (bound dword 0x235f7c0), 62-69 free. Dispatcher 0x218030 calls int32_t fn(Unit* caster, int32_t skillId, int32_t level); 0 refuses the cast. | T |
| `0x2376848` | EnvSpeedNormal | - | int 128 (1.13c 0x6fdeb238); the eclipse's is 4 (0x237684c) | D |
| `0x237ea60` | NpcTable | - | The server's NPC table (D2Game\src\Unit\SUnitNpc.cpp, read by 0x3971a0): 43 entries of 0x1c bytes, +0 uint16 NPC class, +7 byte "hires mercenaries" (the hire handler 0x53d350 refuses an NPC without it). Kashya, Greiz, Asheara and Qual-Kehk have 1; Tyrael (entry 30) has 0. | T |
| `0x2381f30` | MissileCallbackTable | - | MissileParams::callback: run by the create (0x3bac90) from this table as fn(missile, callbackArg). 1 is Firestorm's (0x3b75c0; srvdo 117 / cltdo 67): frames capped at 77, seed from the arg, a type 10 path. | T |
| `0x2386ab0` | PropertyFuncTable | int32_t fn(dataFlag, a1, a2, item, Property*, set, stat, val, first func result, a8, a9, a10) | properties.txt func1-7 table, called from the property apply 0x3d4620; 37 slots (bound dword 0x2386bd8 = 37), 26-35 null | T |
| `0x238e5c0` | AuraEventTable | - | Aura event function table (skills.txt auraeventfunc1-4) | T |
| `0x2391270` | MissileSrvDmgTable | - | void fn(Game*, Unit* missile, Unit* hit, Damage*): 31 slots, 18-30 free. Called by srvhit 1 (0x45bc40) while it builds the hit's damage. | T |
| `0x2396ea0` | AiTable | - | Monster AI think table, indexed by the monai row | T |
| `0x2677438` | EntityPool | - | TlsfAlloctor objects (vtable 0x1d6d770): +0x20 the tlsf control, +0x28 its lock (0x14122ad60 locks, 0x14122ad90 unlocks). 0x1215650 is tlsf block_insert(control, block); tlsf_add_pool is inlined in 0x1215a30. Entity System Pool: every HD scene entity (singleton getter 0x913f60); 0xd714e0 gives it 70 MiB (0x4600000). A map preset over about 34k entities runs it dry and the entity vector grow (0x6d17d0) memsets a null. | D |
| `0x27d1770` | JsonPool | - | JSON Pool: 0xa0a230 gives it 40 MiB (0x2800000) for parsed JSON; a 46 MB generated preset ran it dry (null write in the memcpy at 0x12d36f3). ObjectPool: 0xa20bb0 gives it 50 MiB (0x3200000). | D |
| `0x27d7848` | ObjectPool | - | Pool: the object allocator (TlsfAlloctor object) | D |
| `0x27ff098` | TexturePool | - | Texture Cache TextureData Pool: 0xe8b100 gives it 24 MiB (0x1800000); a TlsfAlloctor like the Entity System Pool. | D |
| `0x2810ff0` | RendererPool | - | Renderer Pool: 0xf6efe0 gives it 12 MiB (0xc00000); allocations go through 0xf6f060. A full-density map ran it dry: 0xdafe30 (called from 0xeeb4d0) wrote through the null it returned | D |
| `0x2a48830` | NpcMenus | - | NPC menus (D2Client\src\UI\npcmenu.cpp): a vector of 0x48-byte records, one per NPC with a menu. +0 uint16 NPC class, +4 int32 entry count (the last entry is Cancel), +8 uint16 string id[5], +0x18 handler[5]. The client fills them from npc.txt and per-NPC setters (Kashya and Qual-Kehk get Hire, Tyrael Travel To Harrogath), then opens one with NpcMenuOpen. | D |
| `0x2a48838` | NpcMenuCount | - | NPC menus (D2Client\src\UI\npcmenu.cpp): a vector of 0x48-byte records, one per NPC with a menu. +0 uint16 NPC class, +4 int32 entry count (the last entry is Cancel), +8 uint16 string id[5], +0x18 handler[5]. The client fills them from npc.txt and per-NPC setters (Kashya and Qual-Kehk get Hire, Tyrael Travel To Harrogath), then opens one with NpcMenuOpen. | D |
| `0x34c3ce8` | JobsPool | - | Jobs: the job system (getter 0x9e8e70, static 0x34c3b40) holds a 10 MiB (0xa00000) TlsfAllocator at +0x1a8 (vtable 0x1d95618, set up by 0x9e91e0). Same +0x20 control, but +0x28 is a spinlock: 0x9e8c30 swaps in the lock's own address, spins while it is not 0 and stores 0 to release. A full-density map ran it dry: 0xd9e740 wrote through the null 0x9e8ca0 returned. | D |
| `0x3e2a420` | EventDispatchSlot | - | The unit event dispatcher 0x5881e0, (game, event, unit, target, damage, list), is jmp [here]: D2RCore's. The hit (0x44ce80) raises domeleedamage (5) / domissiledamage (6) on the attacker through 0x44d570 before the damage lands. | T |
| `0x3e2a448` | CrushingBlowApplySlot | - | CrushingBlowApply's entry is jmp [rip+0x38a8872]: the qword it jumps through, which a plugin can swap | T |
| `0x3e2aab0` | DamageTypeStepSlot | - | DamageEffects (0x44df10) runs its 12 damage types (1.13c's table, 0x40 bytes each here) through (&ctx, &type, flag), called as jmp [this slot]: D2RCore's resist step (1.13c's 0x6fcfbd00). | T |
| `0x3e2b652` | SetUnitStateKey | (unit, key) | UnitStateKey's setter (a jmp stub) | R |

## Rules the engine hard-codes: damage reduction cap, leech rounding, level packets (build 93847)

Engine facts a rule-changing plugin needs. Evidence letters as in the legend above.

### Damage reduction cap (stat 36, damageresist)

| RVA | Signature | Meaning | Ev |
|---|---|---|---|
| `0x4523e0` | (unit, stat) -> value | The resist getter. A resist with no max-resist stat starts from 75 (`0x4524a5`), at most 95 | R |
| `0x4524d0` | patch address, 13 bytes | Where the cap for stat 36 (physical damage reduction) is loaded: `41 83 7e 08 24` (cmp dword [r14+8],0x24) / `b8 32 00 00 00` (mov eax,50) / `0f 44 c8` (cmovz ecx,eax). **D2R caps damageresist at 50 (the byte at `0x4524d6`); 1.09d capped it at 75** (D2Game 0x7e580-0x7e59e: no max-resist stat gives 0 + 75, at most 95). Changing the byte to `0x4b` gives 75; check the 13 bytes first, as a patch | P |

No toolkit header names this address yet (no toolkit code uses it); a plugin that patches it keeps the 13 bytes above as its expected bytes.

### Life and mana leech (`0x450c90`)

| RVA | Signature | Meaning | Ev |
|---|---|---|---|
| `0x450c90` | (game, attacker, target, &damage) | The leech of a hit (header `Leech`, entry bytes `LeechEntry`; hooked in game with an entry check). Reads the life and mana steal percents at damage +0x120 / +0x124 | H |
| `0x3af240` | (unit) -> non-zero for a pet monster | D2R's leech asks it at `0x450e31` (header `IsPet`) | R |

D2R's rule: the percents are shifted `<< 6` (1/64 fixed point) first, and divided by the difficulty's LifeStealDivisor /
ManaStealDivisor (difficultylevels record from `0x300830(game +0x106, game +0x104)`, +0x1c / +0x20) only when the
attacker is a player. 3% in Nightmare (divisor 2) steals 1.5%. A monster target with monstats Drain (record +0xf2,
Nightmare +1, Hell +2) 0 ends the leech early. The elements count in the leeched damage only when damage flag 0x40 is set
(`0x450ebf`-`0x450ec8`: physical +0x18, then +0x20, +0x2c, +0x30, +0x34). The caller `0x44ce80` (after `0x44d038`) then
drains the target's mana by damage +0x124 and stamina by +0x128.

1.09d's rule (D2Game `0x6fcaf4a0`, SUnitDmg.cpp): when the **target is a monster** (whoever attacks) the percents are
integer-divided by the divisors first, then `damage * percent / 100`. 3% in Nightmare steals 1%. To give 1.09d's rounding
through D2R's code, hand it a percent whose steps end the same: `pct / d * d` for a player's hit on a monster (after D2R's
`(pct / d * d) << 6 / d` that is `(pct / d) << 6`), `pct / d` for any other attacker on a monster, `pct * d` for a
player's hit on a player (1.09d divides only on monsters). Everything else (Drain, the damage cap, the life and mana adds)
stays D2R's. Afterwards write back the steal fields stock D2R would have left, as the caller reads them.

### Level packets: act darkness (0x53) and level sound (0x2c)

The server has no PluginSDK service to send a packet or switch an act's light; both are engine calls.

| Packet | Layout | How it is sent | Ev |
|---|---|---|---|
| `0x53` act light | 10 bytes: `0x53`, int32 period, int32 time, byte eclipse | `SendPacket10` (`0x477420`) `(client, packet)` to each client in game (client +4 == 4). The light tick `0x406550` and a2q3 (`0x5a4290`) send the same packet. The client's handler is `0x12cb50` and calls `ActLightSet` (`0x3525c0`) with the fields | R |
| `0x2c` sound | built by `SoundPacket` (`0x5397f0`) `(player, client)` | First `ClientMessage` (`0x491960`) `(player, sound, player)` with the sound id (chest open is `0xb`), then `SoundPacket`; the client is the player's (`PlayerClient` `0x48fde0`) | R |

Darkening an act the way a mod's level effect does: on the server call `ActEclipseOn` (`0x3526f0`) `(dataFlag, act)` once
when the act's eclipse (act light +0x34) is off, send `{0x53, act index, 5, 1}` to every client, and to end it clear the
pause (+0x30), put back the speed (`EnvSpeedNormal` `0x2376848`, 128) at +0x2c and call `ActLightSet(dataFlag, act, null, 2,
0, 0)` before sending `{0x53, act index, 5, 0}`. The act index is the position of the unit's act (unit +0x20) in the
game's act list (header `GameActs`, `GameActCount`). The sound is played to the players of one level by walking the
clients (game +0x138, next +0x628) and comparing each player's room level.
## Unverified table addresses (tools/probe_tables.py, build 93847)

Built into `tools/probe_tables.py` and printed there as "(UNVERIFIED)". No Ghidra evidence is recorded for them yet: confirm each one (what it is, how found) and move it into the sections above, or drop it. Probe-only, so none belongs in `shared/plugin-common/src/rvas_93847*` unless plugin code starts using it. `0x235f590` (CltStTable), `0x2391270` (MissileSrvDmgTable) and `0x2386bd8` (the PropertyFuncTable bound) are verified in the coverage section above and no longer listed here.

| RVA | Guess | Status |
|---|---|---|
| `0x1d1945c` | u32 read as the compiled-formula (prgcalc) count, named `prgcalc_bound` | unverified |
| `0x238e710` | srvstfunc table size: 91 by the bound immediate `0x5a`, 94 by the span to the next table `0x238ea00`; both readings agree on 71-90 being free, so use only those | read from the dispatcher; the last 3 slots untested |

## Monster AI table (build 93847)

| RVA | Meaning |
|---|---|
| `0x2396e90` | Monster AI table: 155 records of 32 bytes `{kind (u64), init fn, think fn, next}`, absolute 64-bit pointers (image base `0x140000000`). Indexed by the row of `monai.txt` (the monstats `AI` column names the row). Examples: Skeleton think `0x5b43a0`, Brute `0x5acc20`, Zombie `0x5ba780`, BloodHawk `0x5aca20`. Read from a memory-layout dump; pairs with 1.09d's AI table in [porting-classic-mods.md](porting-classic-mods.md). The generator `shared/classic_import/gen_109d_monster_ai.py` reads it |

## Function tables: bounds, free slots, readers (build 93847)

Every skill and missile function column is an index into one of these tables. The "free" slots hold null; a plugin writes its own function there (`PatchWriteU64`) and needs no code patch. Read from the dispatchers' bound immediates and the tables' contents; the sizes are the dispatchers' own, not a guess.

| Table | RVA | Slots | Bound (where read) | Free slots |
|---|---|---|---|---|
| skills srvstfunc | `0x238e710` | 91 by bound (`0x5a`), 94 by span | immediate in the dispatcher | 71-90 (use none above 90) |
| skills srvdofunc | `0x238ea00` | 191 | immediate `0xbe` in the skill dispatcher, and the dword `0x1d1945c` on the prg path | 172-190 |
| skills cltstfunc | `0x235f590` | 70 | dword `0x235f7c0` | 62-69 |
| skills cltdofunc | `0x235f7d0` | 130 | dword `0x235f7c4` | 110-129 |
| missiles srvdo | `0x2390e80` | 54 | none | 46-53 |
| missiles srvhit | `0x2391030` | 71 | dword `0x2391404` | 61-70 |
| missiles srvdmg | `0x2391270` | 31 | dword `0x2391408` | 18-30 (read by srvhit 1 `0x45bc40`) |
| missiles cltdo | `0x2358430` | 92 | none | 78-91 |
| missiles clthit | `0x2358710` | 81 | dword `0x2358a64` | 6-8, 11, 15, 17, 20-23, 27, 35, 45, 49, 58, 59, 66-80 |
| item property functions | `0x2386ab0` | 37 | dword `0x2386bd8` | 26-35 |
| aura event functions | `0x238e5c0` | 41 | `cmp eax,0x28` in the dispatcher `0x43823a` (lookup `0x438f70`) | not listed |
| item spells | `0x236fe30` | 20 | none; handler indexes are checked (check < 11, use < 16) | entries 16-19 empty |

Readers (who indexes the table, and with which field):

| Table | Reader | Field and bound |
|---|---|---|
| srvdofunc | `0x43acb0` (skill use) | skills +0x4e, bound 190; the item cast path uses `ItemEffect` (+0x20a) with **no bound** |
| srvdofunc | `0x56c3e0` (prg dispatcher) | `srvprgfunc1-3` (+0x50), bound 191 |
| srvdofunc | `0x435490`, `0x435520` | by number (bound 190), by record field +0x36 (bound 190) |
| srvstfunc | `0x43b3e0`, `0x43acb0`, `0x438670`, `0x433910` | skills +0x4c |
| cltdofunc | `0x216d20` | skills +0x14a, and `ItemCltEffect` (+0x20c); bound 130 |
| cltdofunc | `0x216380`, `0x216920` (prg) | `cltprgfunc1-3` (+0x14c); no bound |
| cltdofunc | `0x215180` | 0x44-byte record field +0x34; bound 130 |
| cltstfunc | `0x218030` | skills +0x148 |

Facts a plugin can rely on:

- **The prg columns index the do tables.** `srvprgfunc1-3` / `cltprgfunc1-3` pick entries of srvdofunc / cltdofunc, not of a separate table.
- **Some slots that look unused hold real functions**: srvdo 41 `0x56dd60` and 143 `0x56e240`, cltdo 15 and 83. srvdo 163 `0x520a00` and cltdo 22 `0x2aed10` are called from code only (no skill row names them); srvdo 171 is Charged Bolt Disk. Check a slot's contents before using it.
- **Six slots point into the D2RLoader thunk area** (`0x3e2b6xx`): srvst 64, srvdo 23 and 157, cltst 61, srvhit 49, cltdo 77.
- **A "router slot"** needs no code change: put one function in one free srvdofunc slot (for example 172) that looks the skill id up in the plugin's own table and calls its function. A hook for ids above 190 would need five code sites with three different bound styles, one of them unbounded.
- The missile collision `0x4639a0` builds the damage (`0x465420`) and applies it (`0x462e40`) only when the hit result has bit 2, and calls `[0x2391270 + n*8]` (srvdmg) after the srvhit function. The clthit dispatcher `0x1b8e60` skips empty slots.
- Not located: the srvstopfunc / cltstopfunc tables (`0x44d570` dispatches through an indirection).

## D2R skill and missile functions by slot (build 93847)

Signatures and slots only; what a mod does with them is not recorded here. Slot numbers are positions in the tables above. These rows are Ghidra reads of the functions.

| Slot | RVA | What it is |
|---|---|---|
| srvdo 2 | `0x430240` | applies a queued hit |
| srvst 32 | `0x5695d0` | generic melee start; calls ElementalDamage `0x437d00` through `0x567070` |
| srvst 68 | `0x569b20` | Cleave start |
| srvst 58 | `0x577c90` | Fire Claws start; its roll is `0x437000` |
| srvst 66 / cltst 56 | `0x42fa90` / `0x2b67e0` | |
| cltst 57 | `0x2b68c0` | |
| srvdo 32 | `0x55cc50` | Poison Dagger do |
| srvdo 22 / cltdo 25 | `0x553cf0` / `0x220140` | Nova |
| srvdo 84 / cltdo 46 | `0x57b880` / `0x223cb0` | Maggot Egg |
| srvdo 91 | `0x57c590` | Nest: `0x48e820`, `0x3636d0`, SpawnMonster `0x492cf0` |
| srvdo 119 | `0x575990` | pet summon: reads pettype (+0x112) and petmax (+0x114) |
| srvdo 122 | `0x576630` | Hunger: corpse from the skill target (`0x48fe20`) |
| srvdo 166 | `0x522e70` | |
| srvdo 56 | `0x55c080` | golem |
| srvdo 34 | `0x570a70` | one-charge hit |
| srvdo 38 / 39 | `0x56ef30` / `0x571860` | |
| srvdo 30 | `0x55c840` | curse (curse function `0x55a7e0`) |
| prg release | `0x56c3e0` / `0x56bfe0` | release dispatcher |
| Charge | srvst 31 `0x564dc0`, srvdo 67 `0x5622c0`, cltst 25 `0x22e1a0`, cltdo 37 `0x22d420` | srvdo 180 and srvst 72 empty |
| Leap Attack hit | `0x56b170` | |
| aura hit | `0x566bc0` | |
| Firestorm | `0x5764e0` -> `0x5769f0` | |
| DiabWall | `0x578bb0` | callback table `0x2381f30` (index 1 `0x3b75c0`, index 7 `0x3b7f70`) |
| missile sdo 40 / cdo 72 | `0x455450` / `0x1b4ea0` | Blessed Hammer slots |
| missile cdo 12 | `0x1b6b30` | screen shake |
| missile srvhit 12 | `0x45d5e0` | chain |
| missile srvhit 5 / clthit 4 | `0x45fd20` / `0x1ae5d0` | |
| missile clthit 12 | `0x1acda0` | |
| missile clthit 26 | `0x1bc380` | callback |
| missile srvhit 62 | - | empty |
| missile srvdmg 1 | `0x453490` | evaluates DmgCalc1 through `0x3b4a90` |
| missile srvdmg ringoffire | `0x4549f0` | |
| aura event 32 | `0x42eea0` | golem events `0x55b2d0`, `0x55b0c0`, `0x55b6a0`; Chilling Armor event 3 `0x552a50` |
| aura event register / cleanup | `0x438230` / `0x588670` | `0x438370` is the path |

Other D2R functions seen from these:

| RVA | What it is |
|---|---|
| `0x2f9b10`, `0x2fa430` | stat operation base |
| `0x584170` | open-wounds table |
| `0x44d660` | QueuedHit |
| `0x583580`, `0x583b30` | item-event functions 14 and 20 |
| `0x3885e0` | item at a body location |
| `0x432c40` | online cast limit |
| `0x5896e0`, `0x589820` | cast-as-event (target, point) |
| `0x470470`, `0x581970`, `0x581ae0` | item aura |
| `0x3e5e60` | cube output parser (words `qty pre suf nor hiq mag set rar uni crf tmp eth sock mod uns rem reg exc eli rep rch lvl`) |
| `0x5269c0` | cube executor: `reg` at `0x52748e` takes the input's quality (`0x36cf60`), unique / set row + 1 (`0x36ce70`) and item level (`0x36ccf0`) |
| `0x58c2f0` | expansion set maker |
| `0x375560` | socket count |
| `0x475140` | gem mods (socket insert `0x46eb00`) |
| `0x48fa40` | input removal (`game`, `item`) |
| `0x411340` | `cheat uniques` handler (table entry `0x238b600`) |
| `0x429d10` | mode change (jump table `0x42a2ca`) |
| `0x42de40`, `0x42d840`, `0x42d020` | queued-command mode entry, busy gate, StartMode |
| `0x4f8de0`, `0x4fdca0` | skill message handler, skill validation |
| `0x302380` | aura event fields: auraevent1-4 (u16 at +0xa4..+0xaa), auraeventfunc1-4 (+0xac..+0xb2) |
| skills record | auralencalc +0x80, summode +0x113, calc4 +0x19c (`0x306193`) |

## Maps, regions, portals and item spells (build 93847)

Read in Ghidra. A level's monsters come from a per-game region record; a level is opened by a portal or a warp.

| RVA | What it is |
|---|---|
| `0x4f40c0` | use-item handler; calls the check dispatcher `0x5817f0` and the use dispatcher `0x581680`, which look the spell entry up through `0x300ae0` |
| `0x236fe30` | item spell table: 20 entries; the entry holds handler indexes (check < 11, use < 16), so entry 16 runs nothing. The caller frees the item when the entry's flag is 0 |
| `0x5da800` | cube Red Portal `(game, player, key, level, max)`: needs town, finds a free spot (`0x517f90`), makes object 60 through the portal maker `0x432ce0` (last argument 1 lifts the town-portal level whitelist), then increments the per-game counter of `key` (`0x5d88b0`, game +0x1aac8) |
| `0x432ce0` | portal maker; spawns through `0x490410` in a room found by `0x38dfb0`, sets mode 1, adds event 1, then `0x435dd0` makes the linked return portal |
| `0x58f680` | portal operate (object operate function 15); needs a linked partner. Operate table `0x23a51c0` has 75 slots, slot 60 empty; dispatcher `0x592c40` |
| `0x488180` | warp `(game, player, level, 0)` |
| `0x484c90` | `(client, 0)` -> the client's player; game clients list at game +0x138, next at +0x628 |
| `0x325c50` | quest record; player data at +0x40 + difficulty * 8. Rite of Passage is quest 39, bit 0 = done |
| `0x2ef4d0`, `0x48faa0`, `0x2f0530` | object removal |
| `0x2efde0` | room neighbours. Room units start at +0xa8, next at unit +0x160; the game's monster lists are at game +0x2630 (128 lists by unit id & 0x7f, next at +0x158) |
| `0x508740` | level id -> region record, array at `*(game + 0x1d0)` |
| `0x5098b0` | builds all regions once per game (called from `0x508750`) |
| `0x509940` | group choice; component picks `0x4195e0` |
| `0x50acf0` | spawns a pack: MonDen is capped at 10000 and a pack spawns when `rand % 100000 <= MonDen` |
| `0x419d20` | pack kind: unique while packs so far < MonUMin / MonUMax, else champion if `rand % 100 > 35`, else normal |
| `0x419e80` | pack picker: weights each group by its rarity (group +2) against the sum (+0x11); swaps to monstats `spawn` (+0x54) only when isSpawn (+0x3e). MinGrp / MaxGrp at monstats +0x65 / +0x66, sparsePopulate +0x67 |
| `0x508f80` | monster level: MonLvl / MonLvlEx through `0x32c700`, plus the terror zone bump `0x35b340`. The region's own level field (+0x2dc / +0x2e0) is never read |
| `0x4926b0` | preset spawn `(game, room, preset)`; the only callee of the room preset loop `0x48f190`, reached from `0x48dc50` -> `0x50a050`. Preset record: id +4, x +8, unit type +0x20, y +0x24 |
| `0x494a60` | monster setup; called only from `0x493cc0` |
| `0x444680` | treasure class drop; drop request flags at +0xc0 (ethereal is 0x4). Quality roll `0x442d60`, item maker `0x43cd50`, socketable test `0x36b410`, set sockets `0x36e880`, monster TC drop `0x447b80`, TC by name `0x4404f0` |
| `0x443910` | unique roll; the dropped-uniques mask is at game +0x3638, one bit per row. A second forced drop of a unique comes out normal until its bit is cleared |
| `0x2f5b80` | `(item, 0, 0x40)` -> the item's magic stat list (entries `{layer, stat, value, extra}` at +0x30, count at +0x38). The stat-list setter `0x2f7c00` sets a value, it does not add |

Region record layout (the record at the level's slot of `0x508740`, build 93847):

| Offset | Field |
|---|---|
| +0x10 | group count |
| +0x11 | rarity sum |
| +0x12 | spawn count |
| +0x14 | groups, 0x34 bytes each: `{monstats id u16, rarity u8, picks u8, ..., components at +0x10}` |
| +0x2b8 | MonDen (u32) |
| +0x2bc, +0x2bd | MonUMin, MonUMax |
| +0x2c8 | packs made so far |
| +0x2e8 onward | terror zone fields |
