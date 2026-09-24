import json
import struct
import sys

SANITY = 0xFAB11BAF


def read_literals(path):
    """Returns ([(dataIndex, length, bytes)], version), ordered by table position."""
    gm = open(path, "rb").read()
    sanity, version = struct.unpack_from("<Ii", gm, 0)
    if sanity != SANITY:
        raise ValueError(f"{path}: invalid sanity ({sanity:#x})")

    slOff = struct.unpack_from("<I", gm, 8)[0]
    npairs = (slOff - 8) // 8
    pairs = [struct.unpack_from("<II", gm, 8 + i * 8) for i in range(npairs)]
    sldOff = pairs[1][0]

    nlit = pairs[0][1] // 8
    lits = []
    for i in range(nlit):
        length, di = struct.unpack_from("<II", gm, slOff + i * 8)
        lits.append((di, length, bytes(gm[sldOff + di: sldOff + di + length])))
    return lits, version


def validate_json(json_path, en_path):
    """
    Final test: reloads written JSON and verifies it against patched EN file.
    Returns (nb_ok, error_list).
    """
    data = json.load(open(json_path, encoding="utf-8"))
    en, _ = read_literals(en_path)
    errors = []
    ok = 0
    seen = set()
    for e in data["protected"]:
        i = e["index"]
        expected = bytes.fromhex(e["value_hex"])
        if i in seen:
            errors.append((i, "duplicate index in JSON"))
            continue
        seen.add(i)
        if i < 0 or i >= len(en):
            errors.append((i, f"index out of bounds (0..{len(en) - 1})"))
        elif en[i][2] != expected:
            errors.append((i, f"mismatched value in EN: {en[i][2]!r} != {expected!r}"))
        else:
            ok += 1
    return ok, errors


def load_or_exit(path, label):
    try:
        return read_literals(path)
    except FileNotFoundError:
        print(f"[!] File not found ({label}): {path}")
    except (ValueError, struct.error) as e:
        print(f"[!] Invalid file ({label}): {e}")
    sys.exit(1)


def main(cn_path, en_path, out_path="output.json"):
    cn, v_cn = load_or_exit(cn_path, "Original CN")
    en, v_en = load_or_exit(en_path, "Patched EN")
    print(f"Original CN : {len(cn)} literals (version {v_cn})")
    print(f"Patched EN   : {len(en)} literals (version {v_en})")

    if v_cn != v_en:
        print(f"[!] Warning: metadata version mismatch (CN {v_cn} / EN {v_en}).")

    # Positional comparison is only valid if tables are aligned.
    # The CN->EN patch must not alter the total number of literals.
    if len(cn) != len(en):
        print("[!] ERROR: literal count differs between CN and EN. Positions are "
              "not aligned, positional comparison would be invalid. Aborting.")
        sys.exit(2)

    entries = []
    changed = 0
    for i, (di_en, len_en, val_en) in enumerate(en):
        if val_en == cn[i][2]:
            e = {"index": i, "value_hex": val_en.hex()}
            try:
                e["value"] = val_en.decode("utf-8")
            except UnicodeDecodeError:
                pass
            entries.append(e)
        else:
            changed += 1

    out = {
        "meta": {
            "original": cn_path,
            "patched_en": en_path,
            "count_literals": len(en),
            "changed_by_en_patch": changed,
            "unchanged_protected": len(entries),
        },
        "protected": entries,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    empty = sum(1 for e in entries if e["value_hex"] == "")
    print(f"Modified by EN patch : {changed}")
    print(f"Unchanged (protected) : {len(entries)} (including {empty} empty strings)")
    print(f"Written to: {out_path}")

    # ---- FINAL TEST: Reloaded JSON must match EN file exactly ----
    ok, errors = validate_json(out_path, en_path)
    if errors:
        print(f"[!] VALIDATION FAILED: {len(errors)} invalid pairs out of {len(entries)}")
        for i, why in errors[:15]:
            print(f"    [{i}] {why}")
        sys.exit(4)
    print(f"VALIDATION OK: {ok}/{len(entries)} (position, value) pairs matched in {en_path}")


if __name__ == "__main__":
    OUT_PATH = "protected-identifiers.json"

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("Usage: python build_protection.py <original_cn.dat> <patched_en.dat>")
        sys.exit(1)
    
    main(args[0], args[1], OUT_PATH)
