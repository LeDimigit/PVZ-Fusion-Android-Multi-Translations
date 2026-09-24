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
TRANS = r"./Translations"
DIR_EN = os.path.join(MOD, "Localization", "English")
DIR_LANG = os.path.join(MOD, "Localization", LANG_NAME)
DIR_LANG2 = os.path.join(TRANS, LANG_NAME, "data.unity3d")
OUT = r"./work/data.unity3d.v2"

WITH_TEXTURES = "--textures" in sys.argv
SIZE_TAG = re.compile(r'</?size[^>]*>')
ALMANAC_SIZE = 12

# Regex placeholder syntax used by translation_regexs*.json templates: {0}, {1}, ...
PLACEHOLDER_RE = re.compile(r'\{(\d+)\}')


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

    # --- Interface & UI Translations (Direct EN -> Target) ---
    json_path = os.path.join(DIR_LANG2, "unity3d_strings.json")
    if os.path.isfile(json_path):
        ui_data = LJ(json_path) or {}
        for en_text, target_text in ui_data.items():
            add(en_text, target_text)

    return en_to_lang


# ---------------- 1b. REGEX TEMPLATE PIVOT (EN pattern -> CN pattern -> LANG template) ----------------
def escape_template_to_regex(template):
    """Turn a template like 'Level {0} Completed' into a matching regex with
    numbered capture groups, in the same order the placeholders appear.

    Everything except the {n} placeholders is escaped literally. Placeholders
    become non-greedy capture groups so multi-line / rich-text templates
    still match. DOTALL is used by the caller so '.' spans newlines.
    """
    if not isinstance(template, str) or not template.strip():
        return None, []

    order = []
    pattern_parts = []
    last_end = 0
    for m in PLACEHOLDER_RE.finditer(template):
        literal = template[last_end:m.start()]
        pattern_parts.append(re.escape(literal))
        pattern_parts.append(r'(.+?)')
        order.append(int(m.group(1)))
        last_end = m.end()
    pattern_parts.append(re.escape(template[last_end:]))

    if not order:
        # No placeholders: nothing to capture, exact-match candidate only.
        return None, []

    compiled = re.compile('^' + ''.join(pattern_parts) + '$', re.DOTALL)
    return compiled, order


def fill_template(template, groups_by_index):
    """Replace {0}, {1}, ... in template with the corresponding captured groups."""
    def _sub(m):
        idx = int(m.group(1))
        return groups_by_index.get(idx, m.group(0))
    return PLACEHOLDER_RE.sub(_sub, template)


def build_regex_pivot():
    """Build a list of (compiled_en_regex, placeholder_order, lang_template),
    sorted so the most specific (longest literal content) templates are tried
    first. Pivoting is done by matching the same CN pattern key between the
    English and target-language translation_regexs.json files.
    """
    en_regex_files = sorted(glob.glob(os.path.join(DIR_EN, "Strings", "translation_regexs.json")))
    lang_regex_files = sorted(glob.glob(os.path.join(DIR_LANG, "Strings", "translation_regexs.json")))

    cn_to_en = {}
    for path in en_regex_files:
        data = LJ(path) or {}
        for cn_pattern, en_template in data.items():
            if isinstance(cn_pattern, str) and isinstance(en_template, str):
                cn_to_en[cn_pattern] = en_template

    cn_to_lang = {}
    for path in lang_regex_files:
        data = LJ(path) or {}
        for cn_pattern, lang_template in data.items():
            if isinstance(cn_pattern, str) and isinstance(lang_template, str):
                cn_to_lang[cn_pattern] = lang_template
                
    # Direct EN -> LANG mappings (e.g. from unity3d_regexs.json)
    en_to_lang_direct = {}
    u3d_regex_path = os.path.join(DIR_LANG2, "unity3d_regexs.json")
    if os.path.isfile(u3d_regex_path):
        data = LJ(u3d_regex_path) or {}
        for en_template, lang_template in data.items():
            if isinstance(en_template, str) and isinstance(lang_template, str):
                en_to_lang_direct[en_template] = lang_template

    entries = []

    # 1. Pivot via CN keys
    for cn_pattern, en_template in cn_to_en.items():
        lang_template = cn_to_lang.get(cn_pattern)
        if not isinstance(lang_template, str) or not lang_template.strip() or lang_template == en_template:
            continue
        compiled, order = escape_template_to_regex(en_template)
        if compiled is None:
            continue
        literal_len = len(PLACEHOLDER_RE.sub('', en_template))
        entries.append((literal_len, compiled, order, lang_template))

    # 2. Direct EN -> LANG rules (unity3d_regexs.json)
    for en_template, lang_template in en_to_lang_direct.items():
        if not lang_template.strip() or lang_template == en_template:
            continue
        compiled, order = escape_template_to_regex(en_template)
        if compiled is None:
            continue
        literal_len = len(PLACEHOLDER_RE.sub('', en_template))
        entries.append((literal_len, compiled, order, lang_template))

    entries.sort(key=lambda e: e[0], reverse=True)
    return [(compiled, order, lang_template) for _, compiled, order, lang_template in entries]


def apply_regex_pivot(text, regex_pivot):
    """Try each compiled EN template regex against text; return the translated
    string on first match, else None. Any placeholder present in the LANG
    template but not captured (shouldn't normally happen) is left as-is.
    Leftover English inside a captured group is acceptable and not treated
    as an error.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    for compiled, order, lang_template in regex_pivot:
        m = compiled.match(text)
        if not m:
            continue
        groups_by_index = {idx: m.group(i + 1) for i, idx in enumerate(order)}
        result = fill_template(lang_template, groups_by_index)
        if result != text:
            return result
    return None


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
    """Updates mechanics (DetailStrings) by their title. If a title has no
    matching translation, the English text is kept as-is (counted in kept)."""
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
def translate_values(obj, d, regex_pivot, stat):
    if isinstance(obj, dict):
        return {k: translate_values(v, d, regex_pivot, stat) for k, v in obj.items()}
    if isinstance(obj, list):
        return [translate_values(x, d, regex_pivot, stat) for x in obj]
    if isinstance(obj, str):
        if obj in d:
            stat["exact"] += 1
            return d[obj]
        translated = apply_regex_pivot(obj, regex_pivot)
        if translated is not None:
            stat["regex"] += 1
            return translated
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


def find_length_prefixed_strings(data):
    """Scan a MonoBehaviour's raw byte buffer for length-prefixed UTF-8
    strings at 4-byte aligned offsets (Unity's standard string serialization).
    Returns a list of (offset, length, text) for strings that decode cleanly
    and are non-empty and ASCII/latin-range-plausible (contain at least one
    letter), so we don't waste time on incidental byte matches.
    """
    found = []
    n = len(data)
    i = 0
    while i + 4 <= n:
        if i % 4 == 0:
            length = struct.unpack_from('<i', data, i)[0]
            if 0 < length <= 4096 and i + 4 + length <= n:
                chunk = data[i + 4:i + 4 + length]
                try:
                    text = chunk.decode('utf-8')
                except UnicodeDecodeError:
                    text = None
                if text and any(c.isalpha() for c in text):
                    found.append((i, length, text))
        i += 4
    return found


def splice_regex_matches(data, regex_pivot):
    """Apply the regex-template pivot directly to a MonoBehaviour's raw
    buffer, for strings that are not covered by the exact dict_pats splice
    (e.g. dynamically formatted TMP text such as 'Level 5 Completed').
    Runs after the exact-match splice on the already-patched buffer.
    """
    candidates = find_length_prefixed_strings(data)
    matches = []
    for offset, length, text in candidates:
        translated = apply_regex_pivot(text, regex_pivot)
        if translated is not None and translated != text:
            matches.append((offset, length, translated.encode('utf-8')))
    if not matches:
        return data, 0
    matches.sort(key=lambda m: m[0], reverse=True)
    buf = bytearray(data)
    for offset, old_len, new_bytes in matches:
        old_end = offset + 4 + old_len + ((4 - (offset + 4 + old_len) % 4) % 4)
        new_pad = (4 - (offset + 4 + len(new_bytes)) % 4) % 4
        buf[offset:old_end] = struct.pack('<i', len(new_bytes)) + new_bytes + b"\x00" * new_pad
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

    regex_pivot = build_regex_pivot()
    print("Regex template pivot (EN -> LANG) entries:", len(regex_pivot))

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
    ta_stat = {"exact": 0, "regex": 0}
    ta_hit = 0
    ui_exact_objs = ui_exact_sites = 0
    ui_regex_objs = ui_regex_sites = 0
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
                # DICTIONARY-based processing (Pivot EN->CN->LANG), with a
                # regex-template fallback for dynamically formatted strings.
                try:
                    j = json.loads(s)
                except Exception:
                    continue
                st = {"exact": 0, "regex": 0}
                j2 = translate_values(j, master, regex_pivot, st)
                if st["exact"] or st["regex"]:
                    d.m_Script = json.dumps(j2, ensure_ascii=False)
                    d.save()
                    ta_hit += 1
                    ta_stat["exact"] += st["exact"]
                    ta_stat["regex"] += st["regex"]

        elif tn == "MonoBehaviour":
            data = o.get_raw_data()
            new_data, n_exact = splice_object(data, dict_pats)
            new_data, n_regex = splice_regex_matches(new_data, regex_pivot)
            if n_exact or n_regex:
                o.set_raw_data(new_data)
                if n_exact:
                    ui_exact_objs += 1
                    ui_exact_sites += n_exact
                if n_regex:
                    ui_regex_objs += 1
                    ui_regex_sites += n_regex

    print("Almanac merged:", alm)
    print(f"TextAsset translations: {ta_stat['exact']} exact + {ta_stat['regex']} regex-template values in {ta_hit} assets")
    print(f"MonoBehaviour splice (exact): objects={ui_exact_objs} sites={ui_exact_sites}")
    print(f"MonoBehaviour splice (regex-template): objects={ui_regex_objs} sites={ui_regex_sites}")
    if WITH_TEXTURES:
        print(f"Textures replaced: {tex_n}")

    out = env.file.save(packer="lz4")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(out)
    print(f"Wrote {OUT} ({len(out):,} bytes)")


if __name__ == "__main__":
    main()