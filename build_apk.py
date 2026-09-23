import hashlib
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from repack import repack_apk

LANG_NAME = "French"
for arg in sys.argv:
    if arg.startswith("--lang="):
        LANG_NAME = arg.split("=")[1]

# edit these paths for your setup
APK = r"./pvzrh.apk"                 # English APK
BUNDLE = r"./work/data.unity3d.v2"         # from patch_bundle_v2.py
META = r"./work/global-metadata.v2.dat"    # from patch_metadata_v2.py

# Dynamically generate the APK name based on the language (e.g., ./pvzrh-french.apk)
OUT_APK = f"./pvzrh-{LANG_NAME.lower()}.apk"

BOOT_ENTRY = "assets/bin/Data/boot.config"
BUNDLE_ENTRY = "assets/bin/Data/data.unity3d"
META_ENTRY = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
APPGUID_ENTRY = "assets/bin/Data/unity_app_guid"   # THE il2cpp extraction-cache key


def md5_to_uuid(h):
    """32-hex md5 -> 36-char UUID (8-4-4-4-12), same shape/length as unity_app_guid."""
    return "%s-%s-%s-%s-%s" % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


def bump_build_guid(boot_bytes, guid):
    """Return boot.config bytes with build-guid set to `guid` (32 hex chars)."""
    text = boot_bytes.decode("utf-8")
    if re.search(r"^build-guid=", text, re.M):
        text = re.sub(r"build-guid=[0-9a-fA-F]+", "build-guid=" + guid, text)
    else:
        text = text.rstrip("\n") + "\nbuild-guid=" + guid + "\n"
    return text.encode("utf-8")


def main(out_apk=None):
    out_apk = OUT_APK
    bundle = open(BUNDLE, "rb").read()
    meta = open(META, "rb").read()

    h = hashlib.md5(meta).hexdigest()
    app_guid = md5_to_uuid(h)                       # the value that forces re-extract
    with zipfile.ZipFile(APK) as z:
        orig_boot = z.read(BOOT_ENTRY)
        old_app_guid = z.read(APPGUID_ENTRY).decode("utf-8", "replace")
    boot = bump_build_guid(orig_boot, h)

    replaced = repack_apk(APK, out_apk, {
        BUNDLE_ENTRY: bundle,
        META_ENTRY: meta,
        BOOT_ENTRY: boot,
        APPGUID_ENTRY: app_guid.encode("utf-8"),    # 36 bytes, same length as orig
    })

    print("unity_app_guid: %s -> %s" % (old_app_guid, app_guid))
    print("build-guid    -> %s" % h)
    print("replaced entries:", replaced)
    print("wrote %s (%s bytes)" % (out_apk, "{:,}".format(os.path.getsize(out_apk))))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
