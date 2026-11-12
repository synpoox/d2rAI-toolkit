# Classic 1.09d engine: skills, missiles and monster AI against D2R

How Lord of Destruction 1.09d binds game code to table rows, and how D2R 3.3 build 93847 does it. For a port that
reproduces 1.09d rules in D2R. Rule differences are in [classic-109d-vs-d2r.md](classic-109d-vs-d2r.md), table
differences in [classic-109d-tables.md](classic-109d-tables.md), the stock files in
[classic-reference-installs.md](classic-reference-installs.md). Porting steps: [porting-classic-mods.md](porting-classic-mods.md).

Evidence: Ghidra on the stock 1.09d DLLs (hashes in [classic-reference-installs.md](classic-reference-installs.md)) and
on a memory dump of D2R build 93847 (PE timestamp `0x6ab3782c`, D2RLoader 1.3.1; see [engine-re.md](engine-re.md)).
Nothing here was run in game. 1.09d addresses are virtual addresses at the DLLs' image bases (`D2Game.dll`
`0x6fc30000`, `D2Client.dll` `0x6faa0000`, `D2Common.dll` `0x6fd40000`), except in the Monster AI section, which uses
RVAs; D2R addresses are RVAs of build 93847.

## Skills and missiles

### 1.09d binds code to rows, not to columns

1.09d `skills.txt` and `missiles.txt` have **no function columns** (`srvstfunc`, `srvdofunc`, `cltstfunc`,
`cltdofunc`, `srvprgfunc*`, `cltprgfunc*`, `pSrvDoFunc` and so on). The DLLs hold per-row charts. A table import
therefore has no 1.09d value for D2R's function columns; it needs a map from each row to the D2R function index that
does what the 1.09d chart entry does.

Skill rows 0-318 and missile rows 0-643 are the same rows on both builds; only names changed (for example a skill
renamed from Sword Mastery to Blade Mastery, the two sentries gained a `mon ` prefix, 46 missile names respelled).

| Side | Chart | 1.09d address | Record |
|---|---|---|---|
| server | skill dispatcher `(game, unit, skill, 0 start / 1 use)` | `0x6fced3a0` | skills 0-5 through the common chart, the rest through the range table |
| server | common chart | `0x6fd1f038` | 6 x {start, use} |
| server | class range table | `0x6fd03e60` | 10 x {first, count} (below) |
| server | class dispatchers | `0x6fd1f068` | 10 pairs {start, use}, same order |
| server | class charts | Amazon `0x6fd1cee0`, Sorceress `0x6fd1f3c8`, Necromancer `0x6fd1ece0`, Paladin `0x6fd1f668`, Barbarian `0x6fd1d530`, Druid `0x6fd1d7f8`, Assassin `0x6fd1d210`, expansion monsters `0x6fd1db70` | 12 bytes {start, use, missile (`0xffff` none)} |
| server | monster chart | `0x6fd1e990` | 8 bytes {start, use} |
| server | item skills | `0x6fd1e718` (count at `0x6fd1e738`) | {skill id, use} |
| client | skill dispatchers | start `0x6fab9c30`, do `0x6fab9ae0` | common chart `0x6fb6c8a0`, range table `0x6fb6c8d0`, class pairs `0x6fb77220` |
| client | class charts | Amazon `0x6fb6c9f8`, Assassin `0x6fb6cc50`, Barbarian `0x6fb6cec8`, Druid `0x6fb6d120`, expansion monsters `0x6fb6d3d0`, monsters `0x6fb6d898`, Necromancer `0x6fb6dd60`, Paladin `0x6fb6dfb8`, Sorceress `0x6fb6e210` | 20 bytes {overlay, sound, start, missile, do}; no item chart |
| server | missile chart | `0x6fd00f08` (mode `0x6fc595d0`, hit `0x6fc59230`) | 12 bytes {do, hit, param} x 644 |
| client | missile chart | `0x6fb92500` (users `0x6fb3d4e0`, `0x6fb3d780`) | 20 bytes {do, hit, +8, overlay, +0x10} x 644 |

### Class row ranges

The range table at `0x6fd03e60` (first row, count):

| Block | First skill row | Count |
|---|---|---|
| Common (generic skills, through the common chart) | 0 | 6 |
| Amazon | 6 | 30 |
| Sorceress | 36 | 30 |
| Necromancer | 66 | 30 |
| Paladin | 96 | 30 |
| Barbarian | 126 | 30 |
| Monsters | 156 | 61 |
| Item skills | 217 | 4 |
| Druid | 221 | 30 |
| Assassin | 251 | 30 |
| Expansion monsters | 281 | 38 |

### D2R's function tables (build 93847)

| Column | Table RVA | Slots | How found |
|---|---|---|---|
| skills `srvstfunc` | `0x238e710` | 94 | start dispatcher `0x43b3e0` |
| skills `srvdofunc` | `0x238ea00` | 191 (172-190 empty) | use dispatcher `0x43acb0` |
| skills `cltstfunc` | `0x235f590` | 70, bound at `0x235f7c0` | `0x218030` reads skill +0x148 |
| skills `cltdofunc` | `0x235f7d0` | 130 (110-129 empty) | table walk |
| skills `srvprgfunc1-3` | the `srvdofunc` table | | values 36-41 and 143 are `srvdofunc` indices |
| skills `cltprgfunc1-3` | the `cltdofunc` table | | values 9-15, 83, 84, 91-93 |
| missiles `pSrvDoFunc` | `0x2390e80` | 54 | `0x466ce0` reads missile +0x2c |
| missiles `pSrvHitFunc` | `0x2391030` | 71 (61-70 empty) | table walk |
| missiles `pCltDoFunc` | `0x2358430` | 92 | table walk |
| missiles `pCltHitFunc` | `0x2358710`, bound at `0x2358a64` | | `0x1b8e60` reads missile +0x2a |

### Slots the loader redirects (thunked)

Some slots point into a thunk area, likely D2RLoader's, not checked in a live process (`0x3e2b6xx`, jumping through pointers outside the image, for example
`0x3e2add0`): `srvstfunc` 64, `srvdofunc` 23 (Blaze) and 157, `cltstfunc` 61, `pSrvHitFunc` 49, `pCltDoFunc` 77. The
running code of these slots is not in a dump, so read it in a live process before calling it the same as 1.09d.
Four other D2R slots are plain thunks to the real function (`0x4550e0` to `0x463100`, `0x2b39f0` to `0x2b3c20`,
`0x568910` to `0x568920`, `0x568f30` to `0x568f40`); follow them.

### D2R reads from columns what 1.09d hard-codes

1.09d has one function per skill with the skill id inside; D2R has one generic function per behaviour, driven by
`skills.txt`. A port that calls a D2R function "the same" still has to write 1.09d's hard-coded numbers into the
columns. Pairs read by hand:

| Behaviour | 1.09d | D2R | Verdict |
|---|---|---|---|
| Charged Bolt (server) | `0x6fcf06d0` | `srvdofunc` 17 `0x5533d0` | same steps: n bolts toward random points (`0x6fcede40` / `0x432b70`), one missile each (`0x6fc52a00` / `0x5371a0`). 1.09d passes its own skill id and a fixed missile; D2R takes the count from `calc1` (skill record +0x190) and the missile from `srvmissile`. The sentry version `0x6fce1a10` is the same pattern |
| Telekinesis (server) | `0x6fcf0d80` | `srvdofunc` 21 `0x554880` | different. Monster and player steps match (hostility `0x6fcad8e0` / `0x492790`, towns, knockback roll, damage). The item branch differs: 1.09d refuses 6 item types, D2R makes one check (`0x33f170`) then picks up (`0x471950`) or sends message 0x14. `LineOfSight` is 0 for Telekinesis on both builds and neither function tests it |
| Paladin auras | per-aura functions (Thorns `0x6fcf2f70`, Blessed Aim `0x6fcf1ff0`, area effect `0x6fceeb30`; Blessed Aim adds a stat callback `0x6fcf1f70`) | `srvdofunc` 65 `0x563d90` for all | structure differs; effect not proven to differ |
| Assassin martial arts | one function each, `0x6fcd9390`-`0x6fcdabb0` | `srvdofunc` 34/35 plus the prg columns | generic in D2R |
| Fire Wall / Blaze missile (server do) | `0x6fc54ca0` | `pSrvDoFunc` 5 `0x458160` | same frame loop; D2R reads the frame bytes from the missile record (+0x1a9 / +0x1aa). Overlapping Fire Wall/Blaze stacking is therefore in the shared damage path, not in the missile functions |
| Power Strike, Impale use | the Kick use function `0x6fcebec0` | `srvdofunc` 2 `0x430240` | both builds use the generic melee function |
| Blaze (server) | `0x6fcf07b0` | `srvdofunc` 23, loader thunk | unreadable on the D2R side |

### How the rest was compared, and what it proves

413 functions of 1.09d `D2Game`, 316 of `D2Client` and 526 D2R functions (plus 4 thunk targets) were decompiled. A
helper map paired 239 callee pairs (a 1.09d helper and a D2R helper that keep appearing together), and each function
pair got a score (the share of mapped helpers both call). Pairs now known to be the same helper (use them as anchors):

| Helper | 1.09d | D2R |
|---|---|---|
| create missile | `0x6fc52a00` | `0x5371a0` |
| skill target point | `0x6fcede40` | `0x432b70` |
| skill formula | ordinal 10996 | `0x3b5160` |
| skill record | ordinal 10997 | `0x97790` |
| skill target unit | `0x6fcacde0` | `0x48fe20` |
| missile owner | `0x6fcac060` | `0x490300` |
| set stat | ordinal 10517 | `0x2f7d10` |
| client create missile | `0x6fb3daf0` | `0x1b7760` |
| client target point | `0x6fab90d0` | `0x214c80` |

Result, per skill (319) and missile (644), after the source's re-read of the first-pass unresolved skills: skills 115
same (39 of them with no function on either build), 156 different, 48 not settled; missiles 525 same, 11 different,
108 unresolved. "Different" is structural (code on one
build only, a loader thunk, or read by hand) and means "check", not a proven change of effect. **A low score does not
show a difference**: a score under 0.4 was checked on three pairs and two did the same thing with the missile taken
from `cltmissile` instead of a constant. "Unresolved" pairs were not read. A skill counts as "same" only when every one of its pairs was read by hand.

Every skill and missile pair, with both names, addresses, D2R index and verdict, is in
`shared/classic_import/data/109d-skill-functions.tsv`; this file does not repeat the per-skill list. That TSV is still
the first pass (111 same, 60 different, 148 unresolved); the re-read verdicts above are not in it yet, and a follow-up
issue will refresh it. Until then, treat its `unresolved` rows as possibly `differs` or `same`.

Not compared: `auraeventfunc`, `srvstopfunc` / `cltstopfunc` (Whirlwind only), `pSrvDmgFunc`, item spells. A "code on
one build only" verdict usually means D2R added a generic start or client function (Throw's `srvstfunc` 65, Bone
Wall's `cltstfunc` 22) or drives from data a client effect 1.09d coded.

### Found in the re-read

- **Charge-up skills (Assassin).** 1.09d reads Tiger Strike's record for all six: Param3 = 225 (duration of all
  progressive skills) and Param4 = 50 (to-hit per charge). D2R `0x56dae0` reads each skill's own `auralencalc` and
  `aurastatcalc2`, so an import must write 225 and 50 into all six.
- **"Use function already ran" flag (0x40).** 1.09d runs the use function again while it is clear, so skills 259, 269
  and 274 hit twice per use with any weapons. D2R `0x570650` leaves it clear only with two claws (type 0x2d) and
  otherwise hits once.
- **State 0xc timer.** 6 in 1.09d (`0x6fac46e0`), 7 in D2R (`0x220be0`).
- **Recurring D2R-only steps.** `0x553e60` and `0x575de0` add owner and skill tagging stats (0x15e, 0x15f, 0xca) and a
  skill-count gate; `0x2b05d0` clamps the curse radius (offset -3, minimum 2).

## Monster AI

- **1.09d `D2Game.dll`:** the AI table is at RVA `0xebac8`, 266 records of 16 bytes `{kind, init fn, think fn, next}`,
  absolute 32-bit pointers. A special-state table sits at `0xecb68`. The reader is `0xa38e0` (sets the think function;
  falls back to `0x9a0d0` / `0x9a3ad0` when the entry is empty; `0x9a3ad0` is as recorded, lies outside the DLL's image range, and is unchecked). The assert files are `AiThink.cpp`, `AiGeneral.cpp`,
  `AiTatics.cpp`, `AiUtil.cpp`, `AiBaal.cpp`.
- **1.09d has no `AI` column; the `BaseId` column picks the AI.** The monstats loader (D2Common `0x1ad40`) reads
  `BaseId` as an int into record `+0x168`, which indexes the table above. `BaseId` takes exactly 266 values (0-265),
  the table length. It is **not** a monstats row number, so a converter must not recode it as one; keep D2R's `AI`
  column for the row, or derive it through the pairing below.
- **D2R build 93847:** the AI table is at RVA `0x2396e90`, 155 records of 32 bytes, same fields, indexed by the
  `monai.txt` row ([d2r-93847-addresses.md](d2r-93847-addresses.md)); special-state table `0x23981f0`. The index is the
  `AI` column, a `u16` at monstats record `+0x52`, bound `0x9a`, read by `0x4a36c0` (record lookup). The AI tick
  `0x4a2a00` switches on the record's kind, then calls the think function.
- **The monstats rows of the two builds line up one to one** (the Expansion separator row sits at the same position in
  both), so a 1.09d monster's D2R `AI` is the `AI` of the same row. Every `BaseId` maps to exactly one D2R `AI` row.
  D2R AI rows no 1.09d monster uses: `None` and the later ones (`ClawViperEx`, `ShadowMasterNoInit`, the four Uber
  AIs, `GenericPet`, the six Colossal AIs). `shared/classic_import/data/109d-monster-ai.tsv` holds the pairing and both
  think functions; regenerate it with `shared/classic_import/gen_109d_monster_ai.py`.
- **`AIParam` slots moved in 1.10.** 1.09d reads `AIParam1-4` (bytes at monstats record `+0x1e4..0x1e7`, the same for
  every difficulty); D2R reads `aipN` (shorts at `+0x90 + 6*(n-1) + 2*difficulty`). The same decision uses a
  different slot, so a plain copy of `AIParamN` into `aipN` is wrong (a Skeleton gets a 15 % attack chance instead of
  75 %):

  | AI | 1.09d think | 1.09d reads | D2R think | D2R reads |
  |---|---|---|---|---|
  | Skeleton | `0x93620` | P1 approach %, P2 attack %, P3 idle frames, P4 attack 1 vs 2 | `0x5b43a0` | aip1 approach, aip3 attack %, aip2 idle, aip4 attack 1 vs 2 |
  | Zombie | `0x96ec0` | P3 for attack 1 vs 2 | `0x5ba780` | aip4 for attack 1 vs 2 |
  | Brute | `0x8e9c0` | P1, P2 | `0x5acc20` | aip3, aip4 |
  | BloodHawk | `0x95810` | none (69 %, 10 %, +-50 hard-coded) | `0x5aca20` | aip1, aip2, aip5 |
  | Bighead | `0x95930` | 60 % hard-coded | `0x5ac6e0` | aip2-aip4 |

  For 83 of the 142 D2R AI rows that 1.09d monsters use, D2R's own `aip` values differ from 1.09d's `AIParam` values in
  the same slots (a table comparison, not a code read; it marks where slots may have moved). Each AI needs its slot map
  read from both think functions. `aiparms.txt` is the same file in 1.09d and 1.13c and does not describe the code; it
  is not evidence.
- **Pairs read:** Idle (same, 200 frames; 1.09d `0x0` / `0x8e250` / `0x9a0d0`, D2R `0x4a3680`), Skeleton (same logic,
  slots moved), Brute (same logic, slots moved), Bighead (same tree, D2R reads parameters where 1.09d hard-codes
  60 %), Zombie (different: slots, and the out-of-range branch), BloodHawk (different: constants became parameters).
  Not judged: Fallen (`0x962d0` / `0x5ae650`; D2R's flee chance is 1/20 and 1.09d's RNG call lost its argument in the
  decompile).
- D2R folds identical think functions (Goatman and Swarm share `0x5b0490`). In 1.09d the necromancer's skeleton and
  mage (`BaseId` 164, 165) use the Skeleton and SkeletonMage think functions; in D2R they use `NecroPet` `0x5c1400`.
- Not worked out: the `kind` numbers differ between builds (SandMaggot is 4 in 1.09d and 5 in D2R; the kind switches
  are at 1.09d `0xa3b40` and D2R `0x4a2a00`); the shared helpers (approach, attack, idle, circle: 1.09d
  `0x8d410` / `0x8d0f0` / `0x8d2b0` against D2R `0x4a8740` / `0x4a78e0` / `0x4a6d10`, and D2R's approach takes an extra
  argument). 1.09d decompiles often lose arguments (`unaff_*` registers, the RNG ordinal with no visible range), so
  those pairs need the disassembly. The other 160 pairs were not read; a constant-fingerprint triage was not good
  enough to call any pair "same".
