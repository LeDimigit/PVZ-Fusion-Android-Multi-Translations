import io
import os
import re
import sys
import glob
import json
import math
import struct
import zipfile
import UnityPy
from PIL import Image

# ---------------- DYNAMIC CONFIGURATION ----------------
LANG_NAME = "French"
for arg in sys.argv:
    if arg.startswith("--lang="):
        LANG_NAME = arg.split("=")[1]

APK = r"./pvzrh.apk"
MOD = r"./PvZ_Fusion_Translator"
DIR_EN = os.path.join(MOD, "Localization", "English")
DIR_LANG = os.path.join(MOD, "Localization", LANG_NAME)
OUT = r"./work/data.unity3d.v2"

WITH_TEXTURES = "--textures" in sys.argv
SIZE_TAG = re.compile(r'</?size[^>]*>')
ALMANAC_SIZE = 12


def LJ(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def strip_size(text):
    return SIZE_TAG.sub("", text) if isinstance(text, str) else text


def size_wrap(text):
    if not isinstance(text, str) or not text.strip():
        return text
    return f"<size={ALMANAC_SIZE}>{strip_size(text)}</size>"


# ---------------- 1. MASTER DICTIONARY BUILDING (EN -> CN -> LANG) ----------------
def build_master():
    en_to_lang = {}
    
    def add(en, lang):
        if isinstance(en, str) and isinstance(lang, str) and lang.strip() and en != lang:
            en_to_lang[en] = lang

    def add_pivot(cn_to_en_dict, cn_to_lang_dict):
        if not cn_to_en_dict or not cn_to_lang_dict:
            return
        # Creating EN -> CN map
        en_to_cn = {}
        for cn, en in cn_to_en_dict.items():
            if isinstance(cn, str) and isinstance(en, str) and en.strip():
                en_to_cn[en] = cn

        # Resolution EN -> CN -> LANG
        for en, cn in en_to_cn.items():
            lang = cn_to_lang_dict.get(cn)
            # Only replace if translation exists, is not empty, and differs from English
            if isinstance(lang, str) and lang.strip() and lang != en:
                en_to_lang[en] = lang

    # Generic strings
    ts_en = LJ(os.path.join(DIR_EN, "Strings", "translation_strings.json")) or {}
    ts_lang = LJ(os.path.join(DIR_LANG, "Strings", "translation_strings.json")) or {}
    add_pivot(ts_en, ts_lang)

    # Tips
    for f in ("tips_fs", "tips_iz"):
        ent = LJ(os.path.join(DIR_EN, "Strings", f"{f}.json")) or {}
        langt = LJ(os.path.join(DIR_LANG, "Strings", f"{f}.json")) or {}
        add_pivot(ent, langt)
        
    # --- CHANGELOG (EN -> LANG) ---
    cl_en = os.path.join(DIR_EN, "Strings", "changelog.txt")
    cl_lang = os.path.join(DIR_LANG, "Strings", "changelog.txt")
    if os.path.exists(cl_en) and os.path.exists(cl_lang):
        with open(cl_en, encoding="utf-8") as f:
            en_cl = f.read()
        with open(cl_lang, encoding="utf-8") as f:
            lang_cl = f.read()
        add(en_cl, lang_cl)

    return en_to_lang


# ---------------- 2. STRUCTURE / ID MERGING (ALMANAC) ----------------
def merge_array(cn_text, lang_json, arr_key, id_key, fields):
    """Updates almanac data directly by ID (seedType/theZombieType)"""
    if not lang_json or arr_key not in lang_json:
        return cn_text, 0, 0

    data = json.loads(cn_text)
    by_id = {x[id_key]: x for x in lang_json[arr_key]}
    tr = kept = 0

    for e in data.get(arr_key, []):
        s = by_id.get(e.get(id_key))
        if s is None:
            kept += 1
            continue
        for f in fields:
            if f in s and isinstance(s[f], str) and s[f].strip():
                e[f] = size_wrap(s[f]) if f in ("introduce", "info") else strip_size(s[f])
        tr += 1

    return json.dumps(data, ensure_ascii=False), tr, kept


def merge_details(cn_text, lang_json):
    """Updates mechanics (DetailStrings) by their title"""
    if not lang_json:
        return cn_text, 0, 0

    data = json.loads(cn_text)
    details_map = {e["title"]: e.get("text", "") for e in lang_json.get("details", []) if "title" in e}
    tr = kept = 0

    for e in data.get("details", []):
        t = e.get("title")
        if t in details_map and details_map[t].strip():
            raw = details_map[t]
            vis = len(re.sub(r"<[^>]+>", "", raw)) or 1
            sz = min(130, round(2941 / math.sqrt(vis)))
            e["text"] = f"<size={sz}%>{strip_size(raw)}</size>"
            tr += 1
        else:
            kept += 1

    return json.dumps(data, ensure_ascii=False), tr, kept


# ---------------- DICTIONARY APPLICATION ----------------
def translate_values(obj, d, stat):
    if isinstance(obj, dict):
        return {k: translate_values(v, d, stat) for k, v in obj.items()}
    if isinstance(obj, list):
        return [translate_values(x, d, stat) for x in obj]
    if isinstance(obj, str) and obj in d:
        stat[0] += 1
        return d[obj]
    return obj


def splice_object(data, dict_pats):
    matches = []
    for pat, lang_b, en_len in dict_pats:
        start = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            start = i + 1
            if i % 4 != 0:
                continue
            pad = (4 - (i + 4 + en_len) % 4) % 4
            if data[i + 4 + en_len: i + 4 + en_len + pad] != b"\x00" * pad:
                continue
            matches.append((i, en_len, lang_b))
    if not matches:
        return data, 0
    matches.sort(key=lambda m: m[0], reverse=True)
    buf = bytearray(data)
    for i, en_len, lang_b in matches:
        old_end = i + 4 + en_len + ((4 - (i + 4 + en_len) % 4) % 4)
        new_pad = (4 - (i + 4 + len(lang_b)) % 4) % 4
        buf[i:old_end] = struct.pack('<i', len(lang_b)) + lang_b + b"\x00" * new_pad
    return bytes(buf), len(matches)


def build_tex_map():
    m = {}
    for p in glob.glob(os.path.join(DIR_LANG, "Textures", "**", "*.png"), recursive=True) + \
             glob.glob(os.path.join(DIR_LANG, "Sprites", "**", "*.png"), recursive=True):
        m[os.path.splitext(os.path.basename(p))[0]] = p
    return m


def main():
    print(f"Target language: {LANG_NAME} ({DIR_LANG})")
    master = build_master()
    print("Master dict (EN -> LANG) entries:", len(master))

    dict_pats = [(struct.pack('<i', len(k.encode())) + k.encode(), v.encode(), len(k.encode()))
                 for k, v in master.items()]

    # Load structured files (Almanac by ID/Structure)
    lawn_lang = LJ(os.path.join(DIR_LANG, "Almanac", "LawnStringsTranslate.json"))
    zomb_lang = LJ(os.path.join(DIR_LANG, "Almanac", "ZombieStringsTranslate.json"))
    det_lang = LJ(os.path.join(DIR_LANG, "Almanac", "DetailStringsTranslate.json"))

    tex_map = build_tex_map() if WITH_TEXTURES else {}
    tex_cache = {}

    with zipfile.ZipFile(APK) as z:
        raw = z.read("assets/bin/Data/data.unity3d")
    env = UnityPy.load(io.BytesIO(raw))

    alm = {}
    ta_val = [0]
    ta_hit = 0
    ui_objs = ui_sites = 0
    tex_n = 0

    for o in env.objects:
        tn = o.type.name

        if tn == "Texture2D" and WITH_TEXTURES:
            d = o.read()
            nm = str(d.m_Name)
            if nm in tex_map:
                if nm not in tex_cache:
                    tex_cache[nm] = Image.open(tex_map[nm]).convert("RGBA")
                img = tex_cache[nm]
                if (d.m_Width, d.m_Height) == img.size:
                    d.image = img
                    d.save()
                    tex_n += 1
            continue

        if tn == "TextAsset":
            d = o.read()
            name = str(d.m_Name)
            s = d.m_Script if isinstance(d.m_Script, str) else bytes(d.m_Script).decode("utf-8", "surrogateescape")

            # STRUCTURE-based processing (ID)
            if name == "LawnStrings":
                new, tr, kept = merge_array(s, lawn_lang, "plants", "seedType", ["name", "introduce", "info", "cost"])
                alm[name] = (tr, kept)
                d.m_Script = new
                d.save()
            elif name == "ZombieStrings":
                new, tr, kept = merge_array(s, zomb_lang, "zombies", "theZombieType", ["name", "introduce", "info"])
                alm[name] = (tr, kept)
                d.m_Script = new
                d.save()
            elif name == "DetailStrings":
                new, tr, kept = merge_details(s, det_lang)
                alm[name] = (tr, kept)
                d.m_Script = new
                d.save()
            else:
                # DICTIONARY-based processing (Pivot EN->CN->LANG)
                try:
                    j = json.loads(s)
                except Exception:
                    continue
                st = [0]
                j2 = translate_values(j, master, st)
                if st[0]:
                    d.m_Script = json.dumps(j2, ensure_ascii=False)
                    d.save()
                    ta_hit += 1
                    ta_val[0] += st[0]

        elif tn == "MonoBehaviour":
            data = o.get_raw_data()
            new, n = splice_object(data, dict_pats)
            if n:
                o.set_raw_data(new)
                ui_objs += 1
                ui_sites += n

    print("Almanac merged:", alm)
    print(f"TextAsset value-translations: {ta_val[0]} values in {ta_hit} assets")
    print(f"MonoBehaviour splice: objects={ui_objs} sites={ui_sites}")
    if WITH_TEXTURES:
        print(f"Textures replaced: {tex_n}")

    out = env.file.save(packer="lz4")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(out)
    print(f"Wrote {OUT} ({len(out):,} bytes)")


if __name__ == "__main__":
    main()