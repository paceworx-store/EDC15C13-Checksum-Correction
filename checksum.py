import struct
import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
#  EDC15C13 Checksum Corrector
#  ─────────────────────────────────────────────────────────────────────────────
#  Usage:  python checksum.py <ORIGINAL_FILE> <MODIFIED_FILE>
#
#  The EDC15C13 stores two 16-bit checksum words at the END of its checksum
#  block (0x4D000 – 0x7E000):
#
#    CS1  @ 0x5FFFC  (2 bytes, little-endian)
#    CS2  @ 0x5FFFE  (2 bytes, little-endian)
#
#  Invariants the ECU checks:
#    (A) wordsum(block) == CS1            — block sum including CS1 and CS2
#    (B) wordsum(block excl CS words) + CS2 == 0   — CS2 is the complement
#
#  Fix strategy:
#    1. Keep CS1 identical to the original (it is the "known-good" target).
#    2. Recompute CS2 = -(wordsum of modified block, excluding both CS words).
#    Both invariants are then satisfied for the patched data.
# ─────────────────────────────────────────────────────────────────────────────

BLOCK_START = 0x4D000
BLOCK_END   = 0x7E000
CS1_OFFSET  = 0x5FFFC   # 2 bytes, LE
CS2_OFFSET  = 0x5FFFE   # 2 bytes, LE


def word_sum(data: bytearray, start: int, end: int) -> int:
    """Sum every 16-bit little-endian word in data[start:end], result mod 65536."""
    total = 0
    for i in range(start, end - 1, 2):
        total += struct.unpack_from('<H', data, i)[0]
    return total & 0xFFFF


def read_cs(data: bytearray, offset: int) -> int:
    return struct.unpack_from('<H', data, offset)[0]


def write_cs(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into('<H', data, offset, value & 0xFFFF)


def sum_excl_cs(data: bytearray) -> int:
    """Wordsum of the checksum block, excluding both CS words."""
    part1 = word_sum(data, BLOCK_START, CS1_OFFSET)          # before CS1
    part2 = word_sum(data, CS2_OFFSET + 2, BLOCK_END)        # after CS2
    return (part1 + part2) & 0xFFFF


def verify_file(label: str, data: bytearray) -> None:
    cs1 = read_cs(data, CS1_OFFSET)
    cs2 = read_cs(data, CS2_OFFSET)
    full_sum  = word_sum(data, BLOCK_START, BLOCK_END)
    excl_sum  = sum_excl_cs(data)
    inv_a = full_sum == cs1
    inv_b = (excl_sum + cs2) & 0xFFFF == 0
    status = "✅ VALID" if (inv_a and inv_b) else "❌ INVALID"
    print(f"  [{label}] CS1={hex(cs1)}  CS2={hex(cs2)}")
    print(f"           block_sum={hex(full_sum)}  excl_sum={hex(excl_sum)}")
    print(f"           Invariant A (sum==CS1): {'✅' if inv_a else '❌'}  "
          f"Invariant B (excl+CS2==0): {'✅' if inv_b else '❌'}  → {status}")


def run():
    if len(sys.argv) != 3:
        print("❌  Usage: python checksum.py <ORIGINAL_FILE> <MODIFIED_FILE>")
        sys.exit(1)

    path_ori = sys.argv[1]
    path_mod = sys.argv[2]

    for p in (path_ori, path_mod):
        if not os.path.exists(p):
            print(f"❌  File not found: {p}")
            sys.exit(1)

    with open(path_ori, 'rb') as f:
        ori = bytearray(f.read())
    with open(path_mod, 'rb') as f:
        mod = bytearray(f.read())

    if len(ori) != len(mod):
        print(f"⚠️   File sizes differ: ORI={len(ori)} bytes, MOD={len(mod)} bytes")

    # ── Show which bytes changed ──────────────────────────────────────────────
    diffs = [i for i in range(min(len(ori), len(mod))) if ori[i] != mod[i]]
    if not diffs:
        print("💤  Files are identical — nothing to do.")
        sys.exit(0)

    # Group consecutive diffs into ranges
    ranges = []
    s = diffs[0]
    p = diffs[0]
    for d in diffs[1:]:
        if d > p + 1:
            ranges.append((s, p))
            s = d
        p = d
    ranges.append((s, p))

    print("=" * 60)
    print("  EDC15C13 Checksum Corrector")
    print("=" * 60)
    print(f"\n📍  {len(diffs)} byte(s) differ across {len(ranges)} region(s):")
    for rs, re in ranges:
        in_cs = (CS1_OFFSET <= rs <= CS2_OFFSET + 1) or (CS1_OFFSET <= re <= CS2_OFFSET + 1)
        tag = "  ← checksum area" if in_cs else ""
        print(f"     {hex(rs)} – {hex(re)}  ({re - rs + 1} byte(s)){tag}")

    # ── Current state ─────────────────────────────────────────────────────────
    print(f"\n🔍  Checksum block: {hex(BLOCK_START)} – {hex(BLOCK_END)}")
    print(f"    CS1 @ {hex(CS1_OFFSET)},  CS2 @ {hex(CS2_OFFSET)}\n")
    print("Before fix:")
    verify_file("ORI", ori)
    verify_file("MOD", mod)

    # ── Compute corrected checksums ───────────────────────────────────────────
    ori_cs1 = read_cs(ori, CS1_OFFSET)   # keep CS1 identical to original
    mod_excl = sum_excl_cs(mod)
    new_cs2  = (-mod_excl) & 0xFFFF

    output = bytearray(mod)
    write_cs(output, CS1_OFFSET, ori_cs1)   # restore original CS1
    write_cs(output, CS2_OFFSET, new_cs2)   # write corrected CS2

    # ── Verify output ─────────────────────────────────────────────────────────
    print("\nAfter fix:")
    verify_file("FIXED", output)

    # ── Save ──────────────────────────────────────────────────────────────────
    out_name = "FIXED_" + os.path.basename(path_mod)
    out_path = os.path.join(os.getcwd(), out_name)
    with open(out_path, 'wb') as f:
        f.write(output)

    print(f"\n🚀  Saved: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    run()
