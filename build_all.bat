@echo off
setlocal enabledelayedexpansion
:: Force UTF-8 encoding for accents and emojis
chcp 65001 > nul

:: ==================================================
:: Configuration & Private Key Settings
:: ==================================================
set "LOCALIZATION_DIR=PvZ_Fusion_Translator\Localization"

:: Keystore details for signing (Leave KS_PATH empty to use default debug key)
set "KS_PATH=path\to\your\keystore.jks"
set "KS_ALIAS=your_key_alias"
set "KS_PASS=your_keystore_password"
set "KEY_PASS=your_key_password"

:: Extract just the keystore file name (not the full path) for display
for %%F in ("%KS_PATH%") do set "KS_FILENAME=%%~nxF"

set "SIGN_MODE=DEBUG"

if not defined KS_PATH goto :key_not_found
if not exist "%KS_PATH%" goto :key_not_found
goto :ask_mode

:key_not_found

echo.
echo ⚠️ Key not found ^(KS_PATH empty or missing^): signing will use the debug key.
goto :mode_chosen

:ask_mode

choice /c 01 /n /m "Sign with key '%KS_FILENAME%' (0) or with the debug key (1)? "
if errorlevel 2 set "SIGN_MODE=DEBUG"
if errorlevel 1 if not errorlevel 2 set "SIGN_MODE=KEY"

:mode_chosen

:: Check if localization directory exists
if not exist "%LOCALIZATION_DIR%" (
    echo ❌ The directory "%LOCALIZATION_DIR%" does not exist!
    goto error
)

:: ==================================================
:: Build the list of available languages (skip English)
:: ==================================================
set "LANG_COUNT=0"
for /d %%D in ("%LOCALIZATION_DIR%\*") do (
    if /i not "%%~nxD"=="English" (
        set /a LANG_COUNT+=1
        set "LANG_!LANG_COUNT!=%%~nxD"
    )
)

if %LANG_COUNT%==0 (
    echo ❌ No language folder found in "%LOCALIZATION_DIR%" ^(other than English^)!
    goto error
)

:select_languages
echo.
echo ==================================================
echo 🌐 Language selection
echo ==================================================
echo   0. ALL languages
for /l %%i in (1,1,%LANG_COUNT%) do (
    echo   %%i. !LANG_%%i!
)
echo.
set "LANG_SELECTION="
set /p "LANG_SELECTION=Enter number(s) separated by commas or spaces ^(e.g. 1,3,5^), or 0 for all: "

if not defined LANG_SELECTION goto select_languages

set "LANG_SELECTION=%LANG_SELECTION:,= %"
set "SELECTED_LANGS="
set "ALL_SELECTED=0"
set "BAD_SELECTION=0"

for %%N in (%LANG_SELECTION%) do (
    if "%%N"=="0" (
        set "ALL_SELECTED=1"
    ) else (
        set "PICK=!LANG_%%N!"
        if not defined PICK (
            echo ⚠️ Invalid choice: %%N
            set "BAD_SELECTION=1"
        ) else (
            echo !SELECTED_LANGS! | find /i " !PICK! " > nul
            if errorlevel 1 set "SELECTED_LANGS=!SELECTED_LANGS! !PICK!"
        )
    )
)

if "%BAD_SELECTION%"=="1" goto select_languages

if "%ALL_SELECTED%"=="1" (
    set "SELECTED_LANGS="
    for /l %%i in (1,1,%LANG_COUNT%) do set "SELECTED_LANGS=!SELECTED_LANGS! !LANG_%%i!"
)

if not defined SELECTED_LANGS (
    echo ⚠️ No language selected.
    goto select_languages
)

echo.
echo ✅ Selected language^(s^):!SELECTED_LANGS!

:: Iterate through the selected languages
for %%L in (%SELECTED_LANGS%) do (
    call :process_language "%%L"
    if errorlevel 1 goto error
)

:: Global Python cache cleanup at the end
for /d /r %%P in (__pycache__) do (
    if exist "%%P" rmdir /s /q "%%P"
)

echo.
echo 🎉 ALL LANGUAGES HAVE BEEN PROCESSED SUCCESSFULLY!
echo.
pause
exit /b 0

:process_language
set "LANG=%~1"

:: Convert language variable to lowercase for the APK name
for /f "delims=" %%A in ('powershell -Command "'%LANG%'.ToLower()"') do set "LANG_LOWER=%%A"

echo.
echo ==================================================
echo 🌐 Processing language: %LANG%
echo ==================================================

echo.
echo ==================================================
echo ▶ Step 1: Patching data.unity3d (%LANG%)
echo ==================================================
python patch_data.unity3d.py --textures --lang=%LANG%
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo.
echo ==================================================
echo ▶ Step 2: Patching global-metadata.dat (%LANG%)
echo ==================================================
python patch_global-metadata.dat.py global-metadata.dat work/global-metadata.v2.dat --lang=%LANG%
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo.
echo ==================================================
echo ▶ Step 3: Assembling APK (%LANG%)
echo ==================================================
python build_apk.py --lang=%LANG%
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo.
echo ==================================================
echo ▶ Step 4: Signing APK (%LANG%)
echo ==================================================
:try_sign
if "%SIGN_MODE%"=="KEY" (
    java -jar uber-apk-signer.jar -a "pvzrh-%LANG_LOWER%.apk" --ks "%KS_PATH%" --ksAlias "%KS_ALIAS%" --ksPass "%KS_PASS%" --ksKeyPass "%KEY_PASS%" --skipZipAlign -o out/
    if errorlevel 1 (
        echo.
        echo ⚠️ Signing with your key failed ^(wrong password or another error^).
        choice /c 01 /n /m "Retry with a new password (0) or switch to the debug key for good (1)? "
        if errorlevel 2 (
            set "SIGN_MODE=DEBUG"
            goto try_sign
        )
        if errorlevel 1 if not errorlevel 2 (
            set /p "KS_PASS=New keystore password: "
            set /p "KEY_PASS=New key password: "
            goto try_sign
        )
    )
) else (
    echo ⚠️ Using the default debug key...
    java -jar uber-apk-signer.jar -a "pvzrh-%LANG_LOWER%.apk" --skipZipAlign -o out/
)
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo.
echo ==================================================
echo ▶ Step 5: Cleaning up build artifacts (%LANG%)
echo ==================================================
:: Remove unsigned APK from root directory
if exist "pvzrh-%LANG_LOWER%.apk" (
    del /f /q "pvzrh-%LANG_LOWER%.apk"
)

:: Remove working directory
if exist "work" (
    rmdir /s /q "work"
)

:: Remove Python cache folders
for /d /r %%P in (__pycache__) do (
    if exist "%%P" rmdir /s /q "%%P"
)

exit /b 0

:error
echo.
echo ❌ ERROR during the pipeline!
echo.
pause
exit /b %ERRORLEVEL%
