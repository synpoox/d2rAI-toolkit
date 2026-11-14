// Resolves the shared signature entries on the running image and binds d2r.h's function table from them.
#include "d2r.h"

#include "build_guard.h"
#include "log.h"

#include <cstdio>
#include <iterator>

namespace d2r {

Api api {};
uint64_t imageBase = 0;

namespace {

template <typename Fn>
void BindOne(Fn& slot, const sigscan::Entry& entry) noexcept {
	slot = Engine<Fn>(entry);
}

// One log line: how the entries resolved, and the first ones that did not.
void LogEntries(uint32_t stamp) noexcept {
	size_t ok = 0, cached = 0;
	char failed[700] = "";
	size_t used = 0;
	for (const sigscan::Entry* e : sig::Shared) {
		ok += e->state == sigscan::State::Ok ? 1 : 0;
		cached += e->cached ? 1 : 0;
		if (e->state != sigscan::State::Ok && used + 1 < sizeof(failed)) {
			const int n = std::snprintf(failed + used, sizeof(failed) - used, "%s%s %s", used == 0 ? "" : ", ", e->name,
			                            sigscan::StateText(e->state));
			used = n < 0 ? sizeof(failed) : used + static_cast<size_t>(n);
		}
	}
	const size_t all = std::size(sig::Shared);
	if (ok == all) {
		plog::Info("engine addresses: %zu/%zu on image 0x%08x (%zu from the build cache)", ok, all, stamp, cached);
	} else {
		plog::Warn("engine addresses: %zu/%zu on image 0x%08x (%zu from the build cache); parts using the others stay "
		           "off: %s", ok, all, stamp, cached, failed);
	}
}

}  // namespace

auto Bind(uint64_t exeBase) noexcept -> bool {
	imageBase = 0;
	const uint32_t stamp = build_guard::ImageStamp(static_cast<uintptr_t>(exeBase));
	sigscan::Resolve(sig::Shared, std::size(sig::Shared), stamp != 0 ? exeBase : 0, sig::Caches, std::size(sig::Caches));
	BindOne(api.getSkillRecord, sig::GetSkillRecord);
	BindOne(api.evalSkillCalc, sig::EvalSkillCalc);
	BindOne(api.skillTargetXY, sig::SkillTargetXY);
	BindOne(api.skillTargetUnit, sig::SkillTargetUnit);
	BindOne(api.createMissile, sig::CreateMissile);
	BindOne(api.missileRecord, sig::MissileRecord);
	BindOne(api.missileCount, sig::MissileCount);
	BindOne(api.unitSeed, sig::UnitSeed);
	BindOne(api.setUnitSkillFlag, sig::SetUnitSkillFlag);
	BindOne(api.applyMeleeHit, sig::ApplyMeleeHit);
	BindOne(api.unitStat, sig::UnitStat);
	BindOne(api.unitStatNoParam, sig::UnitStatNoParam);
	BindOne(api.summonPet, sig::SummonPet);
	BindOne(api.setPetLevel, sig::SetPetLevel);
	BindOne(api.petSkillStats, sig::PetSkillStats);
	BindOne(api.addPetToParty, sig::AddPetToParty);
	BindOne(api.pickSkillMissile, sig::PickSkillMissile);
	BindOne(api.unitDataFlag, sig::UnitDataFlag);
	BindOne(api.clientSkillTargetXY, sig::ClientSkillTargetXY);
	BindOne(api.clientCreateMissile, sig::ClientCreateMissile);
	if (stamp == 0) {
		return false;
	}
	LogEntries(stamp);
	if (!build_guard::Matches(stamp)) {
		return false;
	}
	imageBase = exeBase;
	return true;
}

}  // namespace d2r
