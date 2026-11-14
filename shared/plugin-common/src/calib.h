// Record offsets found at table load (calibration) instead of fixed per build: README.md, "Record offsets by
// calibration". A field is a group of txt columns; Sample() finds the one byte offset in the compiled records where
// every row holds exactly the txt values, Decide() checks it against the build cache.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace calib {

// A txt table as D2R reads it: tab separated, the first line names the columns, every later line is one row, in order.
struct Txt {
	std::string text;
	std::vector<std::string_view> header;
	std::vector<std::vector<std::string_view>> rows;

	auto Parse(std::string body) noexcept -> bool;  // false when there is no header line
	auto Column(std::string_view name) const noexcept -> int;  // -1 when absent
	auto Cell(size_t row, int column) const noexcept -> std::string_view;  // "" out of range
};
auto LoadTxt(const wchar_t* path, Txt* txt) noexcept -> bool;

enum class Kind : uint8_t { Signed, Unsigned, Bit };

// One sampled column: where its value sits from the field's start, and for Kind::Bit which bit of the flag word.
struct Cell {
	const char* column;
	uint16_t at;
	uint8_t bit;
};

// A field's verified offset on one build (PE TimeDateStamp).
struct CacheRow {
	uint32_t stamp;
	int offset;
};

// A record field found by sampling: the byte offset in the record where every row holds exactly the txt values.
struct Field {
	const char* name;
	Kind kind;
	uint8_t width;  // bytes of one cell; Kind::Bit: of the flag word holding the bits
	const Cell* cells;
	size_t cellCount;
	const char* lookupKey;  // non-null: a cell names a row of the lookup txt by this column, and the value is its row
	const CacheRow* cache;
	size_t cacheCount;
};

enum class Status : uint8_t {
	Found,
	NotFound,       // no offset holds the values: off
	Ambiguous,      // more than one offset holds them: off
	DoesNotFit,     // a txt value does not fit the field's width: off
	TooFewSamples,  // the column is too uniform to tell a real match from a coincidence: not sampled
	NoColumn,       // the txt lacks a column (or the lookup txt its key): not sampled
	RowsDiffer,     // the txt is not the table the game loaded (row count): not sampled
	NoTable,        // no records or no txt: not sampled
};

// The sampling rule. Only rows with a value count (an empty cell or an unknown lookup name is no sample), and a row
// is informative when one of its cells differs from that column's most common value. A field needs this many
// informative rows: another offset can then only match by holding the same column, which the exactly-one rule catches.
inline constexpr size_t MinInformative = 16;

struct Result {
	Status status = Status::NoTable;
	int offset = -1;  // Found: the offset; Ambiguous: the first match
	int other = -1;   // Ambiguous: the second match
	size_t samples = 0;
	size_t informative = 0;
};

// Matches `field` against `count` records of `rowSize` bytes. A candidate offset is a multiple of the width (the
// compiled records keep their fields aligned) and must hold every sample of every row; exactly one may.
auto Sample(const Field& field, const Txt& txt, const Txt* lookup, const uint8_t* records, size_t count,
            size_t rowSize) noexcept -> Result;

// The offset to use: the found one unless the build's cache row says otherwise; when the table could not be sampled,
// the build's cache row; else -1 (the parts reading it stay off). `why` gets one line for the log.
auto Decide(const Field& field, const Result& result, uint32_t stamp, char* why, size_t size) noexcept -> int;

// The field's cache row for `stamp`, or -1.
auto Cached(const Field& field, uint32_t stamp) noexcept -> int;

auto StatusText(Status status) noexcept -> const char*;

}  // namespace calib
