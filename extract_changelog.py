import os
import UnityPy

bundle_path = r"./data.unity3d"
output_changelog_path = (r"./PvZ_Fusion_Translator/Localization/English/Strings/changelog.txt")

env = UnityPy.load(bundle_path)

found = False
for obj in env.objects:
    if obj.path_id == 188915:
        raw_bytes = obj.get_raw_data()
        text = raw_bytes.decode("utf-8", errors="ignore")

        start_idx = text.find("<align=center>")
        if start_idx != -1:
            extracted_text = text[start_idx:].split("\x00")[0].strip()

            os.makedirs(os.path.dirname(output_changelog_path), exist_ok=True)

            with open(output_changelog_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(extracted_text)

            print(f"Changelog (PathID 188915) extracted and saved to:\n{output_changelog_path}")
            found = True
            break

if not found:
    print("Object 188915 not found.")