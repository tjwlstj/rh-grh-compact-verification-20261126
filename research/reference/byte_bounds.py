"""Find exact shared byte prefix and suffix for two read-only, named kernel exports."""
import json
import sys
from pathlib import Path

BLOCK = 1 << 20


def common_part(left, right, from_end):
    matched = 0
    with left.open("rb") as a, right.open("rb") as b:
        lengths = (left.stat().st_size, right.stat().st_size)
        limit = min(lengths)
        while matched < limit:
            size = min(BLOCK, limit - matched)
            if from_end:
                a.seek(lengths[0] - matched - size)
                b.seek(lengths[1] - matched - size)
            x, y = a.read(size), b.read(size)
            if x == y:
                matched += size
                continue
            if from_end:
                x, y = reversed(x), reversed(y)
            return matched + next(i for i, (v, w) in enumerate(zip(x, y)) if v != w)
        return limit


def differing_record(path, offset):
    with path.open("rb") as f:
        before = min(offset, 1 << 16)
        f.seek(offset - before)
        prefix = f.read(before).rsplit(b"\n", 1)[-1]
        trailer = f.readline(1 << 16)
    if len(prefix) == (1 << 16) or not trailer.endswith(b"\n"):
        raise ValueError("Record exceeds the inspection window")
    return json.loads(prefix + trailer)


def main(left, right):
    first = common_part(left, right, False)
    last = common_part(left, right, True)
    out = {"sharedPrefixBytes": first, "sharedSuffixBytes": last,
           "firstUnequalRecordLocal": differing_record(left, first),
           "firstUnequalRecordReference": differing_record(right, first)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
