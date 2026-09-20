import struct
import json
import sys
import os

# Dynamic language handling via CLI arguments (--lang=Spanish)
# Example: python patch_metadata_v2.py global-metadata.dat global-metadata-out.dat --lang=French
LANG_NAME = "French"
for arg in sys.argv:
    if arg.startswith("--lang="):
        LANG_NAME = arg.split("=")[1]

MOD = r"./PvZ_Fusion_Translator"
DIR_EN = os.path.join(MOD, "Localization", "English")
DIR_LANG = os.path.join(MOD, "Localization", LANG_NAME)


def LJ(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ---------------- DICTIONARY BUILDING EN -> CN -> LANG ----------------
def build_dict():
    en_to_lang = {}

    def add_pivot(cn_to_en_dict, cn_to_lang_dict):
        if not cn_to_en_dict or not cn_to_lang_dict:
            return
        # Invert CN -> EN to EN -> CN
        en_to_cn = {}
        for cn, en in cn_to_en_dict.items():
            if isinstance(cn, str) and isinstance(en, str) and en.strip():
                en_to_cn[en] = cn

        # Resolution EN -> CN -> LANG
        for en, cn in en_to_cn.items():
            lang = cn_to_lang_dict.get(cn)
            # Only add if translation exists and is different from English
            if isinstance(lang, str) and lang.strip() and lang != en:
                en_to_lang[en] = lang

    # 1. Generic strings
    ts_en = LJ(os.path.join(DIR_EN, "Strings", "translation_strings.json")) or {}
    ts_lang = LJ(os.path.join(DIR_LANG, "Strings", "translation_strings.json")) or {}
    add_pivot(ts_en, ts_lang)

    # 2. Tips
    for f in ("tips_fs", "tips_iz"):
        ent = LJ(os.path.join(DIR_EN, "Strings", f"{f}.json")) or {}
        langt = LJ(os.path.join(DIR_LANG, "Strings", f"{f}.json")) or {}
        add_pivot(ent, langt)

    # 3. Buffs / Modifiers (Reconstructing Name + Desc)
    cnb = LJ(os.path.join(MOD, "Dumps", "travel_buffs.json")) or {}
    enb = LJ(os.path.join(DIR_EN, "Strings", "travel_buffs.json")) or {}
    langb = LJ(os.path.join(DIR_LANG, "Strings", "travel_buffs.json")) or {}

    for cat in cnb:
        if not isinstance(cnb[cat], dict):
            continue
        for bid, cbuff in cnb[cat].items():
            ebuff = enb.get(cat, {}).get(bid)
            langbuff = langb.get(cat, {}).get(bid)
            if not isinstance(ebuff, dict) or not isinstance(langbuff, dict):
                continue

            # Process names
            en_name = ebuff.get("name")
            lang_name = langbuff.get("name")
            if en_name and lang_name and en_name != lang_name:
                en_to_lang[en_name] = lang_name

            # Process descriptions
            en_desc = ebuff.get("desc")
            lang_desc = langbuff.get("desc")
            if en_desc and lang_desc:
                en_full = (f"{en_name}: " if en_name else "") + en_desc
                lang_full = (f"{lang_name}: " if lang_name else "") + lang_desc
                if en_full != lang_full:
                    en_to_lang[en_full] = lang_full

    return en_to_lang


def main(inp, outp):
    print(f"Target language: {LANG_NAME} ({DIR_LANG})")
    gm = bytearray(open(inp, "rb").read())
    sanity, version = struct.unpack_from("<Ii", gm, 0)
    assert sanity == 0xFAB11BAF

    slOff = struct.unpack_from("<I", gm, 8)[0]
    npairs = (slOff - 8) // 8
    pairs = [list(struct.unpack_from("<II", gm, 8 + i * 8)) for i in range(npairs)]
    sldOff, sldSize = pairs[1]

    tr = build_dict()
    print("Master dict (EN -> LANG) entries:", len(tr))
    tr_b = {k.encode(): v.encode() for k, v in tr.items()}

    # Rebuilding stringLiteralData
    nlit = pairs[0][1] // 8
    new_blob = bytearray()
    remap = {}  # (orig_dataIndex, length) -> (new_dataIndex, new_length)
    done = 0

    for i in range(nlit):
        length, di = struct.unpack_from("<II", gm, slOff + i * 8)
        key = (di, length)

        if key in remap:
            ndi, nlen = remap[key]
        else:
            en_b = bytes(gm[sldOff + di: sldOff + di + length])
            lang_b = tr_b.get(en_b)
            out_b = lang_b if lang_b is not None else en_b

            ndi = len(new_blob)
            nlen = len(out_b)
            new_blob += out_b
            remap[key] = (ndi, nlen)

            if lang_b is not None:
                done += 1

        struct.pack_into("<II", gm, slOff + i * 8, nlen, ndi)

    # 4-byte alignment
    while len(new_blob) % 4:
        new_blob.append(0)
    new_size = len(new_blob)
    delta = new_size - sldSize

    # Update headers and section offsets
    pairs[1][1] = new_size
    for p in pairs:
        if p[0] > sldOff:
            p[0] += delta
    for i, p in enumerate(pairs):
        struct.pack_into("<II", gm, 8 + i * 8, p[0], p[1])

    # Rebuilding binary file
    head = bytes(gm[:sldOff])
    tail = bytes(gm[sldOff + sldSize:])
    out = head + bytes(new_blob) + tail

    with open(outp, "wb") as f:
        f.write(out)

    print(f"Translated {done} literals; sldData {sldSize} -> {new_size} (delta {delta:+}); "
          f"filesize {len(gm)} -> {len(out)}; wrote {outp}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("Usage: python patch_metadata_v2.py <in> <out> [--lang=LanguageName]")
        sys.exit(1)
    main(args[0], args[1])