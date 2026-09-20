# PVZ-Fusion-Android-Multi-Translations

This is an unofficial Android build of *Plants vs. Zombies: Fusion*, available in the following languages: Filipino, French, German, Indonesian, Italian, Javanese, Polish, Portuguese, Spanish, and Vietnamese.

This repository intentionally contains no APKs, game binaries, extracted assets, signing keys, or bundled translation data. Supply legally obtained game files locally and clone the translation project separately.

## 🙏 Credits & Sources

This build stands entirely on the work of others. **Please visit and support them:**

| Role | Who | Link |
|---|---|---|
| **Original game** (*PvZ Fusion* / 植物大战僵尸融合版) | **LanPiaoPiao (蓝飘飘fly)** & team | https://space.bilibili.com/3546619314178489 |
| **Translations** | **PVZF‑Translation team** | https://github.com/Teyliu/PVZF-Translation · Discord: https://discord.gg/DPAC5ZVJ8T |
| **English APK** | **silvershadowkat** | https://github.com/silvershadowkat/pvzf-android-translation |
| **Python scripts** | **Heagon** | https://github.com/Heagon/pvz-fusion-english-android |
| Audio changing implementation | **TrevTV** | https://github.com/TrevTV/MelonLoader-AudioTools |
| Main‑menu music | **Rollerlhite** | https://www.youtube.com/watch?v=aBj1MfvnHPE |
| Game artist | **机鱼吐司 (Gfishtus)** | (see Discord) |
| Multi‑language PC package | **Blooms** | (see Discord) |

The translation for **strings, textures and fonts** come from the **PVZF‑Translation**
project. Their README explicitly asks that people credit them and download from
their **official GitHub repo** — so: **do not re‑host their PC translation, and if
you want the desktop version or the latest translation, get it from
https://github.com/Teyliu/PVZF-Translation and their Discord.**

## 🛠️ How it was built (reproduce)

The APK is produced by statically patching the [English APK](https://github.com/silvershadowkat/pvzf-android-translation) with the [translation
content](https://github.com/Teyliu/PVZF-Translation) — no runtime mod loader. 

### 📋 Prerequisites
Before running the scripts, make sure you have the following ready:
 * Python 3 with [UnityPy](https://github.com/K0lb3/UnityPy) installed (`pip install UnityPy`)
 * Java Runtime Environment (JRE) (required for APK signing)
 * [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer) (download the .jar file and place it in your working directory)
 * English APK: Download the base English APK from [silvershadowkat/pvzf-android-translation](https://github.com/silvershadowkat/pvzf-android-translation)
 * Translation Assets: Download or clone the `PvZ_Fusion_Translator` folder from [Teyliu/PVZF-Translation](https://github.com/Teyliu/PVZF-Translation)

### Pipeline:
1. Download the English APK and rename it to pvzrh.apk.
2. Copy it and rename the extension from .apk to .zip.
3. Extract `data.unity3d` (Unity IL2CPP asset bundle) from `pvzrh\assets\bin\Data\data.unity3d` and `global-metadata.dat` from `pvzrh\assets\bin\Data\Managed\Metadata\global-metadata.dat`.
4. Make sure your project directory structure matches the following:
```
PVZ-Fusion-Android-Multi-Translations/
├── PvZ_Fusion_Translator/
│   └── [subdirectories...]
├── build_apk.py
├── built_all.bat
├── data.unity3d
├── global-metadata.dat
├── patch_data.unity3d.py
├── patch_global-metadata.dat.py
├── pvzrh.apk
├── repack.py
└── uber-apk-signer.jar
```
5. Run `built_all.bat`
