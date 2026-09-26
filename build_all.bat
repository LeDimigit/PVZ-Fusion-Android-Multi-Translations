@echo off
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

:: Check if localization directory exists
if not exist "%LOCALIZATION_DIR%" (
    echo ❌ The directory "%LOCALIZATION_DIR%" does not exist!
    goto error
)

:: Iterate through each subfolder in the Localization directory
for /d %%D in ("%LOCALIZATION_DIR%\*") do (
    set "LANG_NAME=%%~nxD"
    
    :: Skip the English folder
    if /i not "%%~nxD"=="English" (
        call :process_language "%%~nxD"
        if errorlevel 1 goto error
    )
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
if defined KS_PATH if exist "%KS_PATH%" (
    java -jar uber-apk-signer.jar -a "pvzrh-%LANG_LOWER%.apk" --ks "%KS_PATH%" --ksAlias "%KS_ALIAS%" --ksPass "%KS_PASS%" --ksKeyPass "%KEY_PASS%" --skipZipAlign -o out/
) else (
    echo ⚠️ Private key not found or not specified. Using default debug key...
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
