# Charged and reusable items: what carries them

Which pieces of the runtime (D2R 3.3, image `0x6ab3782c` / build 93847, D2RLoader 1.3.1-beta, PluginSDK 0.4.0
headers) can carry a reusable item with rechargeable charges, such as a flask or a tome that is not used up. No design
is chosen here: this is the toolbox, with what is proven and what is not. Read with [engine-limits.md](engine-limits.md)
(item spells), [d2rloader-capabilities.md](d2rloader-capabilities.md) and [d2r-93847-addresses.md](d2r-93847-addresses.md).

**Evidence labels.** **[doc]** the PluginSDK README states it. **[hdr]** only a header shows it. **[RE]** static
Ghidra reading, not seen running. **[obs]** a run saw it on this image and loader. **[data]** stock table values.
Everything marked [RE] or unmarked-unverified needs the runtime checks at the end.

## Short answer

- The cheapest pattern is a **plugin item spell in a free `pSpell` slot (16-19)**. A check hook refuses the use when
  the item has no charges left, a use hook applies the effect and spends a charge, and the slot's flag is patched to 1
  so the item is not used up. A plugin has used a slot in 16-19 with check and use hooks on this image **[obs]**. The
  flag-1 part has static reading only **[RE]**.
- The **charge count** can live in three places: the native `quantity` (tome-style), the native
  `item_charged_skill` charges (stat 204), or a new itemstatcost stat. Each has a different limit on where the item can
  sit and what the client sees.
- **Belt use is native for potions.** A belt item that is not used up, and a charge count shown on a belt item, are
  both unverified. Equipped items have no SDK activation event.

## 1. Triggers: how a use starts

| Path | Containers | Support | Limits |
|---|---|---|---|
| Native right-click use (`useable=1` + `pSpell`) | Inventory; belt for `belt=1` types (potions are `belt=1`, tomes `belt=0`) **[data]** | Server use handler `0x4f40c0` -> check dispatcher `0x5817f0` -> use dispatcher `0x581680` **[RE]**; hooking both works **[obs]** | Runs on the server, so it works the same for a TCP/IP client. Slots 16-19 are free; 20 or more does nothing |
| Native belt hotkeys, belt click | Belt | Stock potion behaviour | Unverified for an item that is not used up, or for a custom spell in 16-19 |
| `ItemInteractionService` `Activate` | Inventory, Cube, personal stash and custom pages by default; Belt and SharedStash opt in through `containerMask`, if `supportedContainerMask` reports them **[doc]** `item_interactions.h` **[hdr]** | `Consume` stops the native action; the callback runs on the UI thread before D2R handles the item | Equipment, cursor, ground, trade and vendor are excluded **[doc]**; cursor paths are skipped (no event for an item put down from the cursor **[obs]**). Whether the field exists on loader 1.3.1-beta, and whether belt hotkeys emit `Activate`, are unknown. UI side: a TCP/IP client must message the host |
| `InputService` named action or key listener | Any (the plugin finds the item itself: `getEquippedItem`, `forEachInventoryItem`) | **[doc]** Actions show in the Controls menu; `Handled` consumes the key | Not during chat or text entry. Queue the work to the game thread; a TCP/IP client needs a host message |
| Native charged skill (`item_charged_skill`, stat 204) | Equipped weapons and armor | Stock: cast from the skill bar | Needs a body slot and a selectable skill row. Native recharge is by vendor repair |

## 2. Preventing consumption

- **Item spell flag.** Each entry of the table at `0x236fe30` is {check, use, flag} (12 bytes); flag 1 = not used up.
  The client writes `0x308e80`'s result into the use message and the server refuses unless both sides agree. Patch:
  `PatchWriteU32(0x236fe30 + 12*slot + 8, 0 -> 1)`. One process serves both sides in single player and the patch
  reaches both; a TCP/IP peer needs the same plugin (`Shared`). **[RE]**. A stock tome (`pSpell` 2, `stackable=1`,
  maxstack 20) is the native model of "not used up, quantity spent" **[data]**.
- **The flag is per spell, not per item.** Flipping entry 3 or 5 (timed or rejuvenation potion) would make every
  potion using that spell reusable. A dedicated slot 16-19 avoids that.
- **`ItemInteraction` `Consume`.** No native use happens at all; the plugin applies the effect itself **[doc]**.
- **Not `editItem`.** It edits only stored or cursor items; belt and equipment are rejected. Debits through
  `executeExistingItemTransaction` must leave a quantity of at least 1 and refuse belt and equipment moves **[doc]**.

## 3. Where the charge count can live

| Store | Save / width | Client sees it | Plugin can change it | Notes |
|---|---|---|---|---|
| Native `quantity` (stat 70) | Saved for stackable items; cap = `maxstack` and the `GameRuleService` maximum stack | The native "Quantity" tooltip line | `editItem` quantity for inventory, stash and cursor only **[doc]**; elsewhere through `editNativeItem` plus an item update packet | Belt items are `stackable=0` in stock; whether a stackable item can sit in the belt is unverified |
| `item_charged_skill` (204) | Save Bits 16 + Save Param Bits 16, descfunc 24 "(n/m Charges)" **[data]** | The native tooltip | No SDK field. `editNativeItem` (`NativeHooks`) plus the item update `0x535f60` **[RE]** | Native spend on cast and native recharge on repair. The current/max byte split is the classic layout: confirm on D2R |
| A new itemstatcost stat | Needs `Save Bits` or it is lost on reload; the stock maximum is 24 **[obs]** | Only if the stat is sent with the item and given a `descfunc`. The SDK tooltip event's client copy "reads no custom stats" **[obs]** | `editItem` and existing-item transactions cannot add properties **[obs]**; `executeTransaction` recreates the item with the property, but as a new item. Raw edits use `editNativeItem` | Most flexible (maximum charges, recharge progress). The save width is permanent once characters exist |
| Plugin memory or file | Per game, or your own format | Invisible unless mirrored into a stat | Free | Not on the item: wrong for owned, persistent equipment ([new-game-systems.md](new-game-systems.md), *Where the state lives*) |

`item_replenish_quantity` (stat 253, Save Bits 6, property `rep-quant`) is stock's quantity regeneration over time
**[data]**. Whether D2R applies it to a non-weapon misc item, or in the belt, is unverified.

## 4. Recharge events

| Source | Support | Thread / limit |
|---|---|---|
| Monster death with killer identity | `LifecycleService` `MonsterDeathEvent` **[doc]** | Server thread, after drops; observe only, then queue work. The killer may be a missile or a pet: map it back to the owner |
| Area, act or level change, game join, resurrection, quest | `GameplayEventKind` **[hdr]** `lifecycle_events.h` | UI thread, local player only. "In town" must be inferred from the level id. No waypoint-use event |
| Time | `ThreadService` one-shot game callbacks (re-queue for a tick) **[doc]** | Dropped on a session change. Or use the native `item_replenish_*` stats where they apply |
| Damage dealt, hits | No SDK event | Native stat callbacks and unit events through a hook (`NativeHooks`) |
| Vendor repair | Native for charged skills | Costs gold; no plugin hook needed |

## 5. Effects

- **Over time:** the timed potion, `pSpell` 3, handler `0x57ecb0`, with state `healthpot`. Its calc is the total over
  `len` for hitpoints, mana, manarecovery and hpregen; other stats are per frame ([engine-limits.md](engine-limits.md)).
  **[RE]** **[data]**
- **Instant:** rejuvenation, `pSpell` 5 (`hitpoints` 35/100 %) **[data]**. Antidote, `pSpell` 6, shows a state plus a
  `cstate1` removal (state `antidote`, clears `poison`) **[data]**.
- **Effect delegation:** a plugin spell in 16-19 could call D2R's handler 3 or 5 for the same item. A lead **[RE]**,
  not tried.
- **Timed buffs:** `0x433d20` creates a timed state stat list; `0x553e60` casts any Frozen Armor-style self buff
  ([d2r-93847-addresses.md](d2r-93847-addresses.md)) **[RE]**. A skill start that heals life or mana at once is a
  working pattern in a mod **[obs]**.
- **Scaling:** item calc formulas read player stats (for example `stat('maxhp'.accr)` over `len`). charstats
  `HealthPotionPercent` / `ManaPotionPercent` scale potions per class ([tables.md](tables.md)).

## 6. Tooltips

- **Native:** misc `spelldesc` / `spelldescstr` / `spelldesccalc` describe the effect (`spelldesc 2`, `ItemStats1q`
  for a stock rejuvenation potion) **[data]**. "Quantity" and charged-skill lines are native. A stat with Save/Send
  bits and a `descfunc` prints through the normal stat text (`descfunc` values outside 5-29 print nothing useful).
- **SDK:** `SharedEventService` tooltip listeners add a small UTF-8 block at Description, Attributes, ActionFooter or
  next to Quantity, Durability and others **[doc]**. On 1.3.1-beta colour codes print literally and the event's item
  is the client copy, so per-item custom stats must be fetched by `runtimeId` from the game side (single player or
  host only). `getItemTooltip` / `getItemDetails` are missing and crash if called ([d2rloader.md](d2rloader.md)) **[obs]**.

## Building blocks, cost and risk

| Block | Cost | Risk |
|---|---|---|
| A. Plugin spell in 16-19, flag 1, check refusal at 0 charges | S-M | The flag path has static reading only; belt behaviour unknown; two inline hooks other plugins may also own |
| B. Charges in `quantity` (tome model) | S | Inventory only for SDK edits; belt stacking unknown; quantity cap |
| C. Charges in `item_charged_skill` on equipment | M (needs a heal skill row and a body slot) | No SDK charge edit; a plugin recharge needs a raw edit and a client update |
| D. New charge stat (+ maximum / progress) | M | Permanent save width; client display needs Send bits and a `descfunc`; raw edits |
| E. `ItemInteraction` Consume or `InputService` hotkey -> plugin effect | M | UI thread; TCP/IP needs a host message; belt and the supported mask on 1.3.1-beta unknown; no equipment events |
| F. Recharge on monster death, level change or timer | S | Kill credit from pets and missiles; town is inferred |

## Runtime checks before building

1. Log `ItemInteractionService` `serviceSize` and `supportedContainerMask` on the loader. Is the belt bit present? Do
   belt hotkeys 1-4 (not only clicks) emit `Activate`?
2. Patch a slot 16-19 flag to 1. Right-click the item from the inventory, and from the belt by click and hotkey:
   confirm it stays, the server accepts the use, and the check hook's refusal at 0 charges keeps it and shows a message.
3. Confirm a stackable or quantity item can sit in the belt and auto-belts. Check `item_replenish_quantity` on a misc
   item in the inventory and in the belt.
4. Change a charge (quantity, `item_charged_skill`, or a new stat) on the server for an item in the belt or on the
   body, and confirm the client tooltip updates (item update `0x535f60`) and the value survives save and reload.
5. Check native spend and repair recharge of `item_charged_skill` on D2R, and its current/max byte layout.
6. Call handler 3 or 5 (or `0x433d20`) from the plugin spell, and confirm the heal, the state icon and class
   `HealthPotionPercent` scaling.
7. TCP/IP: run a host and a client together and use the item from the client, through the native path and through the
   SDK path with a host message.
8. Tooltip: does an SDK line or a stat `descfunc` show the live charge count on the client copy?
