// Build 93847: the engine's memory pools (TLSF allocators).
// Grow a pool with tlsf_add_pool under the pool's lock; the sizes D2R gives them are in the comments.
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Engine memory pools -------------------------------------------------------------------------------------------
inline constexpr uint64_t EngineAllocator = 0x12063c0;  // () -> the allocator; vtable +0x20 frees (Leap Attack's cleanup)
// TlsfAlloctor objects (vtable 0x1d6d770): +0x20 the tlsf control, +0x28 its lock (0x14122ad60 locks, 0x14122ad90
// unlocks). 0x1215650 is tlsf block_insert(control, block); tlsf_add_pool is inlined in 0x1215a30.
// Entity System Pool: every HD scene entity (singleton getter 0x913f60); 0xd714e0 gives it 70 MiB (0x4600000). A map
// preset over about 34k entities runs it dry and the entity vector grow (0x6d17d0) memsets a null.
inline constexpr uint64_t EntityPool = 0x2677438;
// Renderer Pool: 0xf6efe0 gives it 12 MiB (0xc00000); allocations go through 0xf6f060. A full-density map ran it dry:
// 0xdafe30 (called from 0xeeb4d0) wrote through the null it returned.
inline constexpr uint64_t RendererPool = 0x2810ff0;
// JSON Pool: 0xa0a230 gives it 40 MiB (0x2800000) for parsed JSON; a 46 MB generated preset ran it dry (null write in
// the memcpy at 0x12d36f3). ObjectPool: 0xa20bb0 gives it 50 MiB (0x3200000).
inline constexpr uint64_t JsonPool = 0x27d1770;
inline constexpr uint64_t ObjectPool = 0x27d7848;
// Jobs: the job system (getter 0x9e8e70, static 0x34c3b40) holds a 10 MiB (0xa00000) TlsfAllocator at +0x1a8 (vtable
// 0x1d95618, set up by 0x9e91e0). Same +0x20 control, but +0x28 is a spinlock: 0x9e8c30 swaps in the lock's own address,
// spins while it is not 0 and stores 0 to release. A full-density map ran it dry: 0xd9e740 wrote through the null
// 0x9e8ca0 returned.
inline constexpr uint64_t JobsPool = 0x34c3ce8;
// Texture Cache TextureData Pool: 0xe8b100 gives it 24 MiB (0x1800000); a TlsfAlloctor like the Entity System Pool.
inline constexpr uint64_t TexturePool = 0x27ff098;
inline constexpr uint64_t EntityPoolLock = 0x122ad60;    // (lock*) -> void
inline constexpr uint64_t EntityPoolUnlock = 0x122ad90;  // (lock*) -> void
inline constexpr uint64_t TlsfBlockInsert = 0x1215650;   // (control, block) -> void

}  // namespace d2r::rva
