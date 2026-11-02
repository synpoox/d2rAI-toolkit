# Runeword stat list (build 93847)

A completed runeword keeps its properties in one native stat list, and it can be edited in place from a plugin through `editNativeItem`. Rune socket bonuses are separate and stay.

- List: `0x2F5B80(item, 171, 0x40)` (state 171 = runeword), null if none. `+0x30` entries, `+0x38` count, `+0x40` capacity.
- Entry: 16 bytes `{ int layer, stat, value, extra }`, sorted by stat, native units.
- Set `0x2F7C00(dataFlag, list, stat, value, layer)`, value 0 removes the entry. Add `0x2F3330`, same arguments. `dataFlag` = `0x34A0E0(item)`.
- Save writer `0x37E438` and client packet writer `0x41AB60` read the live list, so edits survive reload and a new stat needs Save Bits.
- The client copy stays stale until the item is lifted and put back. `executeLocalPlayerMove` PageToCursor then CursorToPage does it on a custom page.
- `0x372260(item)` returns the Runes row pointer. It works right after socketing, when `ItemInfo.prefixIds[0]` is still 0.
- `socketedItemCount` reads 0 for a reloaded runeword.

## Item name builder (build 93847)

`0x1e1d80 (item, char out[0x400])`, in `D2Client/UI/inv.cpp`, builds an item's displayed name. For a runeword (flag `0x4000000`) the result is `<base>\n<color escape>4<runeword name>`, and the tooltip's name lines come from it.

Hook at `0x1e1d89`, not the entry: the first 14 bytes hold a relative `JZ` (null check). At `0x1e1d89` the arguments and stack still match the entry, and the bytes `55 56 41 54 48 8d ac 24 00 ea ff ff b8 00 17 00 00` (17) are position independent. Tested: appending to `out` after the original changes the gold name line in the tooltip.