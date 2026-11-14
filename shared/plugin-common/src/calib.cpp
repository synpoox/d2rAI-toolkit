// calib.h: the txt reader, the sampling rule and the build-cache decision.
#include "calib.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace calib {

namespace {

constexpr int64_t NoSample = INT64_MIN;

auto ParseInt(std::string_view s, int64_t* out) noexcept -> bool {
	if (s.empty() || s.size() > 20) {
		return false;
	}
	char buf[24];
	std::memcpy(buf, s.data(), s.size());
	buf[s.size()] = '\0';
	char* end = nullptr;
	const long long v = std::strtoll(buf, &end, 10);
	if (end == buf || *end != '\0') {
		return false;
	}
	*out = v;
	return true;
}

auto Fits(Kind kind, uint8_t width, int64_t v) noexcept -> bool {
	const int bits = width * 8;
	if (kind == Kind::Bit) {
		return v == 0 || v == 1;
	}
	if (kind == Kind::Unsigned) {
		return v >= 0 && (bits >= 63 || v < (int64_t {1} << bits));
	}
	return bits >= 63 || (v >= -(int64_t {1} << (bits - 1)) && v < (int64_t {1} << (bits - 1)));
}

auto Read(const uint8_t* p, Kind kind, uint8_t width) noexcept -> int64_t {
	uint64_t u = 0;
	std::memcpy(&u, p, width);  // little endian
	if (kind == Kind::Signed && width < 8 && (u >> (width * 8 - 1)) != 0) {
		u |= ~uint64_t {0} << (width * 8);
	}
	return static_cast<int64_t>(u);
}

}  // namespace

auto Txt::Parse(std::string body) noexcept -> bool {
	try {
		text = std::move(body);
		header.clear();
		rows.clear();
		std::string_view all(text);
		bool first = true;
		while (!all.empty()) {
			const size_t nl = all.find('\n');
			std::string_view line = all.substr(0, nl);
			all = nl == std::string_view::npos ? std::string_view {} : all.substr(nl + 1);
			if (!line.empty() && line.back() == '\r') {
				line.remove_suffix(1);
			}
			if (line.empty()) {
				continue;
			}
			std::vector<std::string_view> cells;
			for (;;) {
				const size_t tab = line.find('\t');
				cells.push_back(line.substr(0, tab));
				if (tab == std::string_view::npos) {
					break;
				}
				line.remove_prefix(tab + 1);
			}
			if (first) {
				header = std::move(cells);
				first = false;
			} else if (cells[0] != "Expansion") {  // D2R skips its Expansion marker rows: they compile to no record
				rows.push_back(std::move(cells));
			}
		}
		return !header.empty();
	} catch (...) {
		header.clear();
		rows.clear();
		return false;
	}
}

auto Txt::Column(std::string_view name) const noexcept -> int {
	for (size_t i = 0; i < header.size(); ++i) {
		if (header[i] == name) {
			return static_cast<int>(i);
		}
	}
	return -1;
}

auto Txt::Cell(size_t row, int column) const noexcept -> std::string_view {
	if (row >= rows.size() || column < 0 || static_cast<size_t>(column) >= rows[row].size()) {
		return {};
	}
	return rows[row][static_cast<size_t>(column)];
}

auto LoadTxt(const wchar_t* path, Txt* txt) noexcept -> bool {
	FILE* f = nullptr;
	if (path == nullptr || _wfopen_s(&f, path, L"rb") != 0 || f == nullptr) {
		return false;
	}
	std::string body;
	bool ok = true;
	try {
		char buf[65536];
		size_t n = 0;
		while ((n = std::fread(buf, 1, sizeof(buf), f)) > 0) {
			body.append(buf, n);
		}
	} catch (...) {
		ok = false;
	}
	std::fclose(f);
	return ok && txt->Parse(std::move(body));
}

auto Sample(const Field& field, const Txt& txt, const Txt* lookup, const uint8_t* records, size_t count,
            size_t rowSize) noexcept -> Result {
	Result r;
	if (records == nullptr || count == 0 || txt.header.empty() || field.cellCount == 0 || field.width == 0) {
		return r;  // NoTable
	}
	if (count != txt.rows.size()) {
		r.status = Status::RowsDiffer;
		return r;
	}
	const size_t cells = field.cellCount;
	int key = -1;
	if (field.lookupKey != nullptr) {
		key = lookup != nullptr ? lookup->Column(field.lookupKey) : -1;
		if (key < 0) {
			r.status = Status::NoColumn;
			return r;
		}
	}
	size_t span = 0;
	std::vector<int> columns(cells);
	for (size_t c = 0; c < cells; ++c) {
		columns[c] = txt.Column(field.cells[c].column);
		if (columns[c] < 0) {
			r.status = Status::NoColumn;
			return r;
		}
		span = span > field.cells[c].at + field.width ? span : field.cells[c].at + field.width;
	}
	if (span > rowSize) {
		r.status = Status::NotFound;
		return r;
	}
	// The expected value of every cell of every row (NoSample: an empty cell, an unknown name, not a number)
	std::vector<int64_t> want;
	try {
		want.assign(count * cells, NoSample);
	} catch (...) {
		return r;
	}
	for (size_t row = 0; row < count; ++row) {
		for (size_t c = 0; c < cells; ++c) {
			const std::string_view s = txt.Cell(row, columns[c]);
			int64_t v = NoSample;
			if (s.empty()) {
				continue;
			}
			if (key >= 0) {
				for (size_t i = 0; i < lookup->rows.size(); ++i) {
					if (lookup->Cell(i, key) == s) {
						v = static_cast<int64_t>(i);
						break;
					}
				}
			} else if (!ParseInt(s, &v)) {
				v = NoSample;
			}
			if (v == NoSample) {
				continue;
			}
			if (!Fits(field.kind, field.width, v)) {
				r.status = Status::DoesNotFit;
				return r;
			}
			want[row * cells + c] = v;
		}
	}
	// Informative rows: a cell other than its column's most common value
	std::vector<int64_t> mode(cells, NoSample);
	for (size_t c = 0; c < cells; ++c) {
		size_t best = 0;
		for (size_t row = 0; row < count; ++row) {
			const int64_t v = want[row * cells + c];
			if (v == NoSample || v == mode[c]) {
				continue;
			}
			size_t n = 0;
			for (size_t k = 0; k < count; ++k) {
				n += want[k * cells + c] == v ? 1 : 0;
			}
			if (n > best) {
				best = n;
				mode[c] = v;
			}
		}
	}
	for (size_t row = 0; row < count; ++row) {
		bool any = false, differs = false;
		for (size_t c = 0; c < cells; ++c) {
			const int64_t v = want[row * cells + c];
			any = any || v != NoSample;
			differs = differs || (v != NoSample && v != mode[c]);
		}
		r.samples += any ? 1 : 0;
		r.informative += differs ? 1 : 0;
	}
	if (r.informative < MinInformative) {
		r.status = Status::TooFewSamples;
		return r;
	}
	int matches = 0;
	for (size_t at = 0; at + span <= rowSize; at += field.width) {
		bool ok = true;
		for (size_t row = 0; row < count && ok; ++row) {
			const uint8_t* rec = records + row * rowSize + at;
			for (size_t c = 0; c < cells && ok; ++c) {
				const int64_t v = want[row * cells + c];
				if (v == NoSample) {
					continue;
				}
				const int64_t got = Read(rec + field.cells[c].at, field.kind == Kind::Bit ? Kind::Unsigned : field.kind,
				                         field.width);
				ok = field.kind == Kind::Bit ? ((got >> field.cells[c].bit) & 1) == v : got == v;
			}
		}
		if (ok) {
			if (matches == 0) {
				r.offset = static_cast<int>(at);
			} else if (matches == 1) {
				r.other = static_cast<int>(at);
			}
			++matches;
		}
	}
	r.status = matches == 1 ? Status::Found : (matches == 0 ? Status::NotFound : Status::Ambiguous);
	if (matches == 0) {
		r.offset = -1;
	}
	return r;
}

auto Cached(const Field& field, uint32_t stamp) noexcept -> int {
	for (size_t i = 0; i < field.cacheCount; ++i) {
		if (field.cache[i].stamp == stamp) {
			return field.cache[i].offset;
		}
	}
	return -1;
}

auto Decide(const Field& field, const Result& result, uint32_t stamp, char* why, size_t size) noexcept -> int {
	const int cached = Cached(field, stamp);
	switch (result.status) {
	case Status::Found:
		if (cached >= 0 && cached != result.offset) {
			std::snprintf(why, size, "found at 0x%x but the build cache says 0x%x: off", result.offset, cached);
			return -1;
		}
		std::snprintf(why, size, "found at 0x%x (%zu rows, %zu informative)%s", result.offset, result.samples,
		              result.informative, cached >= 0 ? ", equals the build cache" : ", no cache row for this build");
		return result.offset;
	case Status::Ambiguous:
		std::snprintf(why, size, "ambiguous: found at 0x%x and 0x%x: off", result.offset, result.other);
		return -1;
	case Status::NotFound:
	case Status::DoesNotFit:
		std::snprintf(why, size, "%s: off", StatusText(result.status));
		return -1;
	default:
		if (cached >= 0) {
			std::snprintf(why, size, "not sampled (%s): the build cache's 0x%x", StatusText(result.status), cached);
			return cached;
		}
		std::snprintf(why, size, "not sampled (%s) and no cache row for this build: off", StatusText(result.status));
		return -1;
	}
}

auto StatusText(Status status) noexcept -> const char* {
	switch (status) {
	case Status::Found: return "found";
	case Status::NotFound: return "no offset holds the txt values";
	case Status::Ambiguous: return "ambiguous";
	case Status::DoesNotFit: return "a txt value does not fit the width";
	case Status::TooFewSamples: return "too few informative rows";
	case Status::NoColumn: return "a column is missing";
	case Status::RowsDiffer: return "the txt is not the loaded table";
	case Status::NoTable: return "no table";
	}
	return "?";
}

}  // namespace calib
