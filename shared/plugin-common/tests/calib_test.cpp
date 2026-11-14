// calib: the sampling rule (exactly one match, width, alignment, informative rows, lookups, bits) and the build
// cache decision, on synthetic records.
#include "calib.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

int g_failures = 0;

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

using calib::Cell;
using calib::Kind;
using calib::Status;

constexpr uint32_t Known = 0x11111111, Unknown = 0x22222222;
constexpr size_t Rows = 40, Size = 0x40;

void Put(std::vector<uint8_t>& recs, size_t row, size_t at, int64_t v, int width) {
	std::memcpy(recs.data() + row * Size + at, &v, static_cast<size_t>(width));
}

void Rules() {
	std::string body = "id\ta\tz\ts\tf\n";
	for (size_t i = 0; i < Rows; ++i) {
		body += "r" + std::to_string(i) + "\t" + std::to_string(i * 7 + 3) + "\t0\t" + (i % 3 == 0 ? "" : "n" + std::to_string(i % 4)) +
		        "\t" + std::to_string(i % 2) + "\n";
	}
	calib::Txt txt;
	Check(txt.Parse(body) && txt.rows.size() == Rows && txt.Column("a") == 1, "parse: header and rows");
	calib::Txt names;
	names.Parse("name\r\nn0\r\nn1\r\nExpansion\r\nn2\r\nn3\r\n");
	Check(names.rows.size() == 4 && names.Cell(2, 0) == "n2", "an Expansion row is no record (D2R skips it), CRLF lines");

	const calib::CacheRow cache[] = {{Known, 0x10}};
	const Cell a[] = {{"a", 0, 0}};
	const calib::Field fa {"a", Kind::Signed, 2, a, 1, nullptr, cache, 1};

	std::vector<uint8_t> recs(Rows * Size, 0);
	for (size_t i = 0; i < Rows; ++i) Put(recs, i, 0x10, static_cast<int64_t>(i * 7 + 3), 2);
	calib::Result r = calib::Sample(fa, txt, nullptr, recs.data(), Rows, Size);
	char why[200];
	Check(r.status == Status::Found && r.offset == 0x10, "the column is found where it sits");
	Check(calib::Decide(fa, r, Known, why, sizeof(why)) == 0x10, "found and equal to the build cache: used");
	Check(calib::Decide(fa, r, Unknown, why, sizeof(why)) == 0x10, "found on a build with no cache row: used");

	std::vector<uint8_t> shifted(Rows * Size, 0);
	for (size_t i = 0; i < Rows; ++i) Put(shifted, i, 0x14, static_cast<int64_t>(i * 7 + 3), 2);
	r = calib::Sample(fa, txt, nullptr, shifted.data(), Rows, Size);
	Check(r.status == Status::Found && r.offset == 0x14, "a shifted column is found at its new offset");
	Check(calib::Decide(fa, r, Unknown, why, sizeof(why)) == 0x14, "shifted, new build: the new offset is used");
	Check(calib::Decide(fa, r, Known, why, sizeof(why)) == -1, "shifted against the build cache: off");

	std::vector<uint8_t> twice = recs;
	for (size_t i = 0; i < Rows; ++i) Put(twice, i, 0x20, static_cast<int64_t>(i * 7 + 3), 2);
	r = calib::Sample(fa, txt, nullptr, twice.data(), Rows, Size);
	Check(r.status == Status::Ambiguous && r.offset == 0x10 && r.other == 0x20, "the column at two offsets: ambiguous");
	Check(calib::Decide(fa, r, Known, why, sizeof(why)) == -1, "ambiguous: off, even with a cache row");

	std::vector<uint8_t> odd(Rows * Size, 0);
	for (size_t i = 0; i < Rows; ++i) Put(odd, i, 0x11, static_cast<int64_t>(i * 7 + 3), 2);
	r = calib::Sample(fa, txt, nullptr, odd.data(), Rows, Size);
	Check(r.status == Status::NotFound, "an int16 at an odd offset is no match (alignment)");
	Check(calib::Decide(fa, r, Known, why, sizeof(why)) == -1, "not found: off, even with a cache row");

	const calib::Field narrow {"a8", Kind::Unsigned, 1, a, 1, nullptr, cache, 1};
	r = calib::Sample(narrow, txt, nullptr, recs.data(), Rows, Size);
	Check(r.status == Status::DoesNotFit, "values above 255 in a uint8 field: does not fit");

	const Cell z[] = {{"z", 0, 0}};
	const calib::Field fz {"z", Kind::Signed, 2, z, 1, nullptr, cache, 1};
	r = calib::Sample(fz, txt, nullptr, recs.data(), Rows, Size);
	Check(r.status == Status::TooFewSamples, "an all-zero column is never sampled (it matches any zero bytes)");
	Check(calib::Decide(fz, r, Known, why, sizeof(why)) == 0x10, "not sampled, known build: the cache row");
	Check(calib::Decide(fz, r, Unknown, why, sizeof(why)) == -1, "not sampled, new build: off");

	r = calib::Sample(fa, txt, nullptr, recs.data(), Rows - 1, Size);
	Check(r.status == Status::RowsDiffer, "a txt with another row count than the table: not sampled");

	const Cell s[] = {{"s", 0, 0}};
	const calib::Field fs {"s", Kind::Signed, 2, s, 1, "name", cache, 1};
	std::vector<uint8_t> named(Rows * Size, 0xff);  // the empty cells (no sample) hold -1
	for (size_t i = 0; i < Rows; ++i) if (i % 3 != 0) Put(named, i, 0x08, static_cast<int64_t>(i % 4), 2);
	r = calib::Sample(fs, txt, &names, named.data(), Rows, Size);
	Check(r.status == Status::Found && r.offset == 0x08, "a name column through its lookup table: the row numbers");
	Check(calib::Sample(fs, txt, nullptr, named.data(), Rows, Size).status == Status::NoColumn,
	      "a lookup field without its lookup txt: not sampled");

	const Cell f[] = {{"f", 0, 5}};
	const calib::Field ff {"f", Kind::Bit, 4, f, 1, nullptr, cache, 1};
	std::vector<uint8_t> bits(Rows * Size, 0);
	for (size_t i = 0; i < Rows; ++i) Put(bits, i, 0x0c, (i % 2 != 0 ? 0x20 : 0) | 0x101, 4);
	r = calib::Sample(ff, txt, nullptr, bits.data(), Rows, Size);
	Check(r.status == Status::Found && r.offset == 0x0c, "a flag bit: its word is found, the other bits ignored");
}

}  // namespace

int main() {
	Rules();
	std::printf("%s\n", g_failures == 0 ? "all passed" : "FAILED");
	return g_failures == 0 ? 0 : 1;
}
