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

## ​🚀 Installation
​1. Go to the Latest Release.
​2. Go below to the Assets section (you might need to click the arrow next to "Assets" to expand it).
​3. Click on the file name corresponding to the language you want to download.
​4. Open the downloaded file on your Android device and press Install.

​## 🔄 Updating from another version

​If you are updating from the original Chinese or the English translation APK, follow these steps to keep your progress:
​1. Backup your save files:
* Navigate to `Android/data/com.LanPiaPiao.PlantsVsZombiesRH/files` (To access this directory on Android, connect your phone to a PC, or use a file manager like **RS File Manager**, **Files** (by Marc apps & software), or **ZArchiver** combined with Shizuku).
​* Copy all contents to a backup folder, excluding the `il2cpp` folder.
​2. Uninstall your current version of the game.
​3. Install this translated version and launch it once to generate the app folders.
​4. Close the game, then restore your backup by copying your saved files back into `Android/data/com.LanPiaPiao.PlantsVsZombiesRH/files`.
