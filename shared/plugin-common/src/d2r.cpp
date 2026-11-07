// Binds d2r.h's function table to the running image, only when it is the image rvas_93847.h describes.
#include "d2r.h"

#include "build_guard.h"

namespace d2r {

Api api {};
uint64_t imageBase = 0;

namespace {

template <typename Fn>
void BindOne(Fn& slot, uint64_t exeBase, uint64_t offset) noexcept {
	slot = reinterpret_cast<Fn>(exeBase + offset);
}

}  // namespace

auto Bind(uint64_t exeBase) noexcept -> bool {
	if (!build_guard::Matches(build_guard::ImageStamp(static_cast<uintptr_t>(exeBase)))) {
		return false;
	}
	imageBase = exeBase;
	BindOne(api.getSkillRecord, exeBase, rva::GetSkillRecord);
	BindOne(api.evalSkillCalc, exeBase, rva::EvalSkillCalc);
	BindOne(api.skillTargetXY, exeBase, rva::SkillTargetXY);
	BindOne(api.skillTargetUnit, exeBase, rva::SkillTargetUnit);
	BindOne(api.createMissile, exeBase, rva::CreateMissile);
	BindOne(api.missileRecord, exeBase, rva::MissileRecord);
	BindOne(api.missileCount, exeBase, rva::MissileCount);
	BindOne(api.unitSeed, exeBase, rva::UnitSeed);
	BindOne(api.setUnitSkillFlag, exeBase, rva::SetUnitSkillFlag);
	BindOne(api.applyMeleeHit, exeBase, rva::ApplyMeleeHit);
	BindOne(api.unitStat, exeBase, rva::UnitStat);
	BindOne(api.unitStatNoParam, exeBase, rva::UnitStatNoParam);
	BindOne(api.summonPet, exeBase, rva::SummonPet);
	BindOne(api.setPetLevel, exeBase, rva::SetPetLevel);
	BindOne(api.petSkillStats, exeBase, rva::PetSkillStats);
	BindOne(api.addPetToParty, exeBase, rva::AddPetToParty);
	BindOne(api.pickSkillMissile, exeBase, rva::PickSkillMissile);
	BindOne(api.unitDataFlag, exeBase, rva::UnitDataFlag);
	BindOne(api.clientSkillTargetXY, exeBase, rva::ClientSkillTargetXY);
	BindOne(api.clientCreateMissile, exeBase, rva::ClientCreateMissile);
	return true;
}

}  // namespace d2r
