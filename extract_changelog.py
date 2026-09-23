import os
import UnityPy

bundle_path = r"./data.unity3d"
output_changelog_path = r"./PvZ_Fusion_Translator/Localization/English/Strings/changelog.txt"

env = UnityPy.load(bundle_path)

found = False

for obj in env.objects:
    if obj.type.name == "MonoBehaviour":
        try:
            raw_bytes = obj.get_raw_data()
            text = raw_bytes.decode("utf-8", errors="ignore")

            # Locate the target text
            if "<align=center><size=20>Disclaimer</size></align>" in text:
                start_idx = text.find("<align=center><size=20>Disclaimer</size></align>")
                extracted_text = text[start_idx:].split("\x00")[0].strip()

                # Ensure the string is not empty (length > 0)
                if len(extracted_text) > 0:
                    os.makedirs(os.path.dirname(output_changelog_path), exist_ok=True)

                    with open(output_changelog_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(extracted_text)

                    print(f"Changelog extracted from PathID {obj.path_id} ({len(extracted_text)} characters) and saved to:\n{output_changelog_path}")
                    found = True
                    break  # Stop searching once valid content is found and saved
        except Exception:
            pass

if not found:
    print("No MonoBehaviour containing a valid changelog was found.")