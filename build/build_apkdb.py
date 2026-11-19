# -*- coding: utf-8 -*-
"""Assemble APKDB v2.1.5 (2026-11-19) by in-place replacing bundled tools."""
import os, re, shutil, subprocess, sys, zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'apkdb_extract', 'APKDB_X')
BUILD = os.path.join(BASE, 'build')
PAYLOAD = os.path.join(BUILD, 'APKDB_X')
DL = os.path.join(BASE, 'downloads')
STAGE = os.path.join(BASE, 'stage')
SEVEN = r'C:\Program Files\7-Zip\7z.exe'

log = []
def say(msg):
    log.append(msg)
    print(msg)

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def copy_file(src, dst):
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)

def copy_tree(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)

def read_text(path, encodings=('gbk', 'utf-8-sig', 'utf-8')):
    raw = open(path, 'rb').read()
    for enc in encodings:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('latin1'), 'latin1'

def write_text(path, text, enc):
    import ctypes
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x80)
    except Exception:
        pass
    data = text.encode(enc if enc != 'utf-8-sig' else 'utf-8')
    if enc == 'utf-8-sig':
        data = b'\xef\xbb\xbf' + data
    try:
        with open(path, 'r+b') as f:
            f.seek(0)
            f.write(data)
            f.truncate()
    except FileNotFoundError:
        open(path, 'wb').write(data)

def patch_file(path, replacements, required=True):
    text, enc = read_text(path)
    for old, new in replacements:
        if old not in text:
            if required:
                raise SystemExit('PATCH MISS in %s: %r' % (path, old[:80]))
            continue
        text = text.replace(old, new)
    write_text(path, text, enc)

def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True)
    if p.returncode != 0:
        say('CMD FAILED (%s): %s' % (p.returncode, cmd))
        say(p.stdout.decode('utf-8', 'replace')[-3000:])
        say(p.stderr.decode('utf-8', 'replace')[-3000:])
    return p

# ---------------------------------------------------------------- payload
if os.path.isdir(BUILD):
    shutil.rmtree(BUILD, ignore_errors=True)
ensure_dir(BUILD)
copy_tree(SRC, PAYLOAD)
say('[1] payload copied: %d files' % sum(len(f) for _, _, f in os.walk(PAYLOAD)))

# ---------------------------------------------------------------- apktool 3.0.3
for jar in ('apktool250.jar', 'apktool251.jar', 'apktoolsk.jar'):
    copy_file(os.path.join(DL, 'apktool_3.0.3.jar'), os.path.join(PAYLOAD, 'apktool', jar))
for jar in ('apktool200.jar', 'apktool203.jar', 'apktool240.jar', 'apktool241.jar'):
    p = os.path.join(PAYLOAD, 'apktool', jar)
    if os.path.exists(p):
        os.remove(p)
say('[2] apktool 3.0.3 installed as 250/251/sk; legacy 2.0-2.4 jars removed')

# ---------------------------------------------------------------- smali / baksmali 3.0.10
copy_file(os.path.join(STAGE, 'smali.jar'), os.path.join(PAYLOAD, 'apktool', 'smali.jar'))
copy_file(os.path.join(STAGE, 'baksmali.jar'), os.path.join(PAYLOAD, 'apktool', 'baksmali.jar'))
say('[3] smali/baksmali 3.0.10 fat jars installed')

# ---------------------------------------------------------------- jadx 1.5.7
copy_tree(os.path.join(STAGE, 'jadx'), os.path.join(PAYLOAD, 'jadx'))
say('[4] jadx 1.5.7 installed')

# ---------------------------------------------------------------- platform-tools 37.0.1
pt = os.path.join(STAGE, 'platform-tools', 'platform-tools')
for name in ('adb.exe', 'fastboot.exe', 'AdbWinApi.dll', 'AdbWinUsbApi.dll', 'libwinpthread-1.dll'):
    copy_file(os.path.join(pt, name), os.path.join(PAYLOAD, 'Tools', 'ADB', name))
copy_file(os.path.join(pt, 'adb.exe'), os.path.join(PAYLOAD, 'Tools', 'ApkTool', 'adb.exe'))
copy_file(os.path.join(pt, 'AdbWinApi.dll'), os.path.join(PAYLOAD, 'Tools', 'ApkTool', 'AdbWinApi.dll'))
copy_file(os.path.join(pt, 'AdbWinUsbApi.dll'), os.path.join(PAYLOAD, 'Tools', 'ApkTool', 'AdbWinUsbApi.dll'))
say('[5] platform-tools 37.0.1 (adb/fastboot) installed')

# ---------------------------------------------------------------- build-tools 37.0.0
bt = os.path.join(STAGE, 'build-tools', 'android-37.0')
copy_file(os.path.join(bt, 'zipalign.exe'), os.path.join(PAYLOAD, 'Tools', 'zipalign.exe'))
copy_file(os.path.join(bt, 'aapt.exe'), os.path.join(PAYLOAD, 'Tools', 'ApkTool', 'aapt.exe'))
copy_file(os.path.join(bt, 'aapt2.exe'), os.path.join(PAYLOAD, 'Tools', 'aapt2.exe'))
ensure_dir(os.path.join(PAYLOAD, 'Tools', 'apksigner', 'lib'))
copy_file(os.path.join(bt, 'apksigner.bat'), os.path.join(PAYLOAD, 'Tools', 'apksigner', 'apksigner.bat'))
copy_file(os.path.join(bt, 'lib', 'apksigner.jar'), os.path.join(PAYLOAD, 'Tools', 'apksigner', 'lib', 'apksigner.jar'))

# Java launchers must survive an invalid/stale JAVA_HOME: fall back to `java` in PATH
def patch_java_fallback(path, goto_label, exe_name='java.exe'):
    text, enc = read_text(path, ('utf-8', 'gbk'))
    old = 'set JAVA_EXE=%JAVA_HOME%/bin/' + exe_name + '\r\n'
    if old not in text:
        old = 'set JAVA_EXE=%JAVA_HOME%/bin/' + exe_name + '\n'
    if old in text and 'fallback to java in PATH' not in text:
        new = old + ('if exist "%JAVA_EXE%" goto ' + goto_label + '\r\n'
                     'rem fallback to java in PATH when JAVA_HOME is stale\r\n'
                     'set JAVA_EXE=' + exe_name + '\r\n'
                     '%JAVA_EXE% -version >NUL 2>&1\r\n'
                     'if %ERRORLEVEL% equ 0 goto ' + goto_label + '\r\n')
        text = text.replace(old, new, 1)
        write_text(path, text, enc)
        return True
    return False

for launcher, label, exe in (('jadx/bin/jadx.bat', 'execute', 'java.exe'), ('jadx/bin/jadx-gui.bat', 'execute', 'javaw.exe'),
                        ('Tools/apksigner/apksigner.bat', 'init', 'java.exe')):
    try:
        ok = patch_java_fallback(os.path.join(PAYLOAD, launcher), label, exe)
        say('[6b] JAVA_HOME fallback %s: %s' % (launcher, ok))
    except FileNotFoundError:
        say('[6b] WARN launcher missing: %s' % launcher)
say('[6] build-tools 37.0.0 (zipalign/aapt/aapt2/apksigner) installed')

# ---------------------------------------------------------------- 7-Zip 26.06
for arch, src in (('32', os.path.join(STAGE, '7zip32')), ('64', os.path.join(STAGE, '7zip64'))):
    for name in ('7z.exe', '7z.dll'):
        copy_file(os.path.join(src, name), os.path.join(PAYLOAD, 'Tools', '7zip', arch, name))
say('[7] 7-Zip 26.06 (x86/x64) installed')

# ---------------------------------------------------------------- OptiPNG 0.7.8 / wget 1.25.0
if os.path.isdir(os.path.join(STAGE, 'optipng')):
    shutil.rmtree(os.path.join(STAGE, 'optipng'), ignore_errors=True)
os.makedirs(os.path.join(STAGE, 'optipng'), exist_ok=True)
run([SEVEN, 'x', '-y', '-o' + os.path.join(STAGE, 'optipng'), os.path.join(DL, 'optipng-0.7.8.zip')])
copy_file(os.path.join(STAGE, 'optipng', 'optipng-0.7.8-win32', 'optipng.exe'), os.path.join(PAYLOAD, 'Tools', 'optipng.exe'))
copy_file(os.path.join(DL, 'wget-1.25.0-32.exe'), os.path.join(PAYLOAD, 'Update', 'wget.exe'))
say('[8] OptiPNG 0.7.8 + wget 1.25.0 installed')

# ---------------------------------------------------------------- ApkShellext2-Plus 2.1.5
shext_dst = os.path.join(PAYLOAD, 'Tools', 'apkshellext2')
if os.path.isdir(shext_dst):
    shutil.rmtree(shext_dst)
ensure_dir(shext_dst)
shext_bin = os.path.join(BASE, 'build_apkshellext', 'bin', 'Release')
for name in os.listdir(shext_bin):
    src = os.path.join(shext_bin, name)
    if name.lower().endswith('.pdb'):
        continue
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(shext_dst, name), dirs_exist_ok=True)
    else:
        shutil.copy2(src, os.path.join(shext_dst, name))
# legacy shell extension dll is obsolete
legacy = os.path.join(PAYLOAD, 'Tools', 'apkshellext.dll')
if os.path.exists(legacy):
    os.remove(legacy)
say('[9] ApkShellext2-Plus 2.1.5 installed; legacy apkshellext.dll removed')
shutil.rmtree(os.path.join(PAYLOAD, 'Tools', 'ApkTool333'), ignore_errors=True)
say('[9b] legacy ApkTool333 installer removed from package')

# ---------------------------------------------------------------- bootimg: magiskboot alongside legacy
magi = os.path.join(DL, 'magiskboot.exe')
if os.path.exists(magi) and os.path.getsize(magi) > 100000:
    copy_file(magi, os.path.join(PAYLOAD, 'Tools', 'bootimg', 'magiskboot.exe'))
    say('[10] magiskboot added')
else:
    say('[10] WARN magiskboot missing; legacy bootimg only')

# ---------------------------------------------------------------- scripts
sign_shim = r'''@echo off
setlocal EnableExtensions
rem Compatibility shim: signapk <cert.pem> <key.pk8> <in.apk> <out.apk>
set "CERT=%~1"
set "KEY=%~2"
set "IN=%~3"
set "OUT=%~4"
if not exist "%CERT%" exit /b 2
if not exist "%KEY%" exit /b 2
if not exist "%IN%" exit /b 2
if exist "%OUT%" del /f /q "%OUT%" >nul 2>nul
call "%~dp0..\apksigner\apksigner.bat" sign --key "%KEY%" --cert "%CERT%" --out "%OUT%" "%IN%"
if errorlevel 1 exit /b 1
exit /b 0
'''
ensure_dir(os.path.join(PAYLOAD, 'Tools', 'Signer'))
for _n in ('testkey.pk8', 'testkey.x509.pem'):
    copy_file(os.path.join(PAYLOAD, 'Temp', 'Signer', _n), os.path.join(PAYLOAD, 'Tools', 'Signer', _n))
open(os.path.join(PAYLOAD, 'Tools', 'Signer', 'apksigner-shim.bat'), 'wb').write(sign_shim.replace('\n', '\r\n').encode('ascii'))

# apkdb.cmd / apkdb_d.cmd
for fn in ('apkdb.cmd', 'apkdb_d.cmd'):
    p = os.path.join(PAYLOAD, fn)
    text, enc = read_text(p)
    n_zipalign_fix = 0
    # 1) apktool 3: -c -> --copy-original, drop aapt1/aapt2 switch
    text = text.replace(' b %aapt2% -f -c %1', ' b -f --copy-original %1')
    text = text.replace('set "aapt2=--use-aapt2"', 'set "aapt2="')
    # 2) signing: signapk jar -> apksigner shim
    text = text.replace('java -jar "%~dp0Tools\\Signer\\%signapk%.jar"',
                        'call "%~dp0Tools\\Signer\\apksigner-shim.bat"')
    # 3) batch: zipalign BEFORE apksigner (v2 signature must be last)
    old_sign = ('call "%~dp0Tools\\Signer\\apksigner-shim.bat" "%~dp0Tools\\Signer\\%key%.x509.pem" '
                '"%~dp0Tools\\Signer\\%key%.pk8" "%%b.apk" Signed_"%%b.apk" && DEL /F /Q "%%b.apk" >NUL && '
                '"%~dp0Tools\\zipalign" -v 4 Signed_"%%b.apk" "%%b.apk" >NUL && DEL /F /Q Signed_"%%b.apk"')
    new_sign = ('"%~dp0Tools\\zipalign" -v 4 "%%b.apk" "%%b_aligned.apk" >NUL && DEL /F /Q "%%b.apk" >NUL && '
                'call "%~dp0Tools\\Signer\\apksigner-shim.bat" "%~dp0Tools\\Signer\\%key%.x509.pem" '
                '"%~dp0Tools\\Signer\\%key%.pk8" "%%b_aligned.apk" "%%b.apk" && DEL /F /Q "%%b_aligned.apk"')
    if old_sign in text:
        text = text.replace(old_sign, new_sign)
        n_zipalign_fix += 1
    write_text(p, text, enc)
    say('[11] patched %s (apktool3=%s, signapk->apksigner, zipalign-order fixes=%d)'
        % (fn, ' b -f --copy-original %1' in text, n_zipalign_fix))

# optipng.cmd signing
p = os.path.join(PAYLOAD, 'optipng.cmd')
text, enc = read_text(p)
text = text.replace('java -jar "%~dp0Tools\\signer\\signapk.jar"',
                    'call "%~dp0Tools\\signer\\apksigner-shim.bat"')
write_text(p, text, enc)
say('[12] patched optipng.cmd')

# apktool 3: decode --no-debug-info must use the long option
p = os.path.join(PAYLOAD, 'apkdb_d.cmd')
text, enc = read_text(p)
text = text.replace('set "BL=-b"', 'set "BL=--no-debug-info"')
write_text(p, text, enc)
say('[13b] apkdb_d.cmd: -b -> --no-debug-info')

# user-facing labels that still name the old bundled versions
for fn in ('apkdb.cmd', 'apkdb_d.cmd', 'seesource.bat'):
    fp = os.path.join(PAYLOAD, fn)
    if not os.path.exists(fp):
        continue
    txt, enc2 = read_text(fp)
    txt = txt.replace('ShakaApktool v3.0.0', 'Apktool 3.0.3')
    txt = txt.replace('v3.0.0(ShakaApktool)', 'v3.0.3')
    txt = txt.replace('Jadx 0.6.1', 'Jadx 1.5.7')
    txt = txt.replace('Jadx 0.7.2', 'Jadx 1.5.7')
    write_text(fp, txt, enc2)
say('[13a] old version labels updated')

# bootimg menu: add magiskboot entries
p = os.path.join(PAYLOAD, 'apkdb.cmd')
text, enc = read_text(p)
marker = 'ECHO.    [3] 自定义手动操作'
if marker in text and 'magiskbootunpack' not in text:
    text = text.replace(marker,
        'ECHO.    [3] 自定义手动操作\r\n'
        'ECHO.    [4] MagiskBoot 解包(现代 boot.img)\r\n'
        'ECHO.    [5] MagiskBoot 打包(现代 boot.img)')
    text = text.replace('if /i "%id%"=="3" goto bootimg3',
        'if /i "%id%"=="3" goto bootimg3\r\n'
        'if /i "%id%"=="4" goto magiskbootunpack\r\n'
        'if /i "%id%"=="5" goto magiskbootrepack')
    labels = r''':magiskbootunpack
set "MB=%~dp0Tools\bootimg\magiskboot.exe"
if not exist "%MB%" ECHO. 未找到 magiskboot.exe & pause>NUL & goto bootimg
if /i exist boot.img ( "%MB%" unpack boot.img ) else if /i exist recovery.img ( "%MB%" unpack recovery.img ) else ECHO. 当前目录没有 boot.img / recovery.img
ECHO.^>^>按任意键返回
pause>NUL
goto bootimg

:magiskbootrepack
set "MB=%~dp0Tools\bootimg\magiskboot.exe"
if not exist "%MB%" ECHO. 未找到 magiskboot.exe & pause>NUL & goto bootimg
if /i exist boot.img ( "%MB%" repack boot.img ) else if /i exist recovery.img ( "%MB%" repack recovery.img ) else ECHO. 当前目录没有 boot.img / recovery.img
if /i exist new-boot.img ECHO. 已生成 new-boot.img
if /i exist new-recovery.img ECHO. 已生成 new-recovery.img
ECHO.^>^>按任意键返回
pause>NUL
goto bootimg

'''
    text = text.replace(':diyapktool\r\n', labels + ':diyapktool\r\n', 1)
    write_text(p, text, enc)
    say('[13] magiskboot menu added')
else:
    say('[13] WARN magiskboot menu not added (marker missing or already patched)')

# install.bat: run cleanup first; never register legacy dll
p = os.path.join(PAYLOAD, 'install.bat')
text, enc = read_text(p)
text = text.replace('color a0\r\nxcopy "%~dp0Temp\\Signer"',
                    'color a0\r\ncall "%~dp0Tools\\cleanup.bat"\r\nxcopy "%~dp0Temp\\Signer"', 1)
# never register the removed legacy shell extension
text = text.replace('"%~dp0Tools\\apkshellext.dll"', '"%~dp0Tools\\apkshellext2\\ApkShellext2.dll"')
write_text(p, text, enc)
say('[14] patched install.bat')

# uninstapkico.bat: legacy -> new dll
p = os.path.join(PAYLOAD, 'uninstapkico.bat')
text, enc = read_text(p)
text = text.replace('%REGASM% /unregister "%~dp0Tools\\apkshellext2\\ApkShellext2.dll"',
                    '%REGASM% /unregister "%~dp0Tools\\apkshellext2\\ApkShellext2.dll" >nul 2>nul')
old_xp2 = '%REGASM% /unregister "%~dp0Tools\\apkshellext.dll"'
if old_xp2 in text:
    text = text.replace(old_xp2, '%REGASM% /unregister "%~dp0Tools\\apkshellext2\\ApkShellext2.dll" >nul 2>nul')
write_text(p, text, enc)
say('[15] patched uninstapkico.bat')

# ---------------------------------------------------------------- cleanup.reg
def reg_keys(path):
    raw = open(path, 'rb').read()
    for enc in ('utf-16', 'utf-8-sig', 'latin1'):
        try:
            t = raw.decode(enc)
            break
        except Exception:
            continue
    return re.findall(r'^\[(-?)(HKEY_CLASSES_ROOT\\[^\]]+)\]', t, re.M)

keys = []
for f in ('old_shellext2.reg', 'old_shellext_legacy.reg'):
    for _, k in reg_keys(os.path.join(BASE, f)):
        if k not in keys:
            keys.append(k)
extra = [
    r'HKEY_CLASSES_ROOT\*\shell\APKDB',
    r'HKEY_CLASSES_ROOT\Directory\shell\apkdb',
    r'HKEY_CLASSES_ROOT\Apkdb.apk',
    r'HKEY_CLASSES_ROOT\Apkdb.arsc',
    r'HKEY_CLASSES_ROOT\Apkdb.dex',
    r'HKEY_CLASSES_ROOT\Apkdb.odex',
]
for k in extra:
    if k not in keys:
        keys.append(k)
lines = ['Windows Registry Editor Version 5.00', '']
for k in keys:
    lines.append('[-%s]' % k)
    lines.append('')
data = '\r\n'.join(lines).encode('utf-16-le')
open(os.path.join(PAYLOAD, 'Tools', 'cleanup.reg'), 'wb').write(b'\xff\xfe' + data)
say('[16] cleanup.reg generated (%d keys)' % len(keys))

# ---------------------------------------------------------------- cleanup.bat
cleanup = r'''@echo off
setlocal EnableExtensions
for %%i in ("%~dp0..") do set "ROOT=%%~fi"
pushd "%ROOT%"

REM ---- stop processes that lock files ----
TASKKILL /F /IM ApkTool.exe /IM adb.exe /IM fastboot.exe /IM ApkShellext2.exe >NUL 2>NUL
TASKKILL /F /IM ShuameDaemon.exe /IM shuame_helper.exe >NUL 2>NUL
TASKKILL /F /IM AndroidRomXmlEdit.exe /IM zipalign.exe /IM 7z.exe /IM aapt.exe >NUL 2>NUL

REM ---- regasm path ----
set "REGASM="
if exist "%windir%\Microsoft.NET\Framework64\v4.0.30319\regasm.exe" set "REGASM=%windir%\Microsoft.NET\Framework64\v4.0.30319\regasm.exe"
if not defined REGASM if exist "%windir%\Microsoft.NET\Framework\v4.0.30319\regasm.exe" set "REGASM=%windir%\Microsoft.NET\Framework\v4.0.30319\regasm.exe"

REM ---- unregister old shell extensions (best effort) ----
if exist "%ROOT%\Tools\apkshellext.dll" if defined REGASM "%REGASM%" /unregister "%ROOT%\Tools\apkshellext.dll" >NUL 2>NUL
if exist "%ROOT%\Tools\apkshellext2\ApkShellext2.dll" if defined REGASM "%REGASM%" /unregister "%ROOT%\Tools\apkshellext2\ApkShellext2.dll" >NUL 2>NUL
regedit /s "%ROOT%\Tools\cleanup.reg" >NUL 2>NUL

REM ---- delete legacy files / folders (2.1.4 and older) ----
rd /s /q "%ROOT%\Tools\ApkTool333" >NUL 2>NUL
del /f /q "%ROOT%\Tools\apkshellext.dll" >NUL 2>NUL
del /f /q "%ROOT%\apktool\apktool200.jar" >NUL 2>NUL
del /f /q "%ROOT%\apktool\apktool203.jar" >NUL 2>NUL
del /f /q "%ROOT%\apktool\apktool240.jar" >NUL 2>NUL
del /f /q "%ROOT%\apktool\apktool241.jar" >NUL 2>NUL
for %%f in ("%ROOT%\jadx\lib\*.jar") do if /i not "%%~nxf"=="jadx-1.5.7-all.jar" del /f /q "%%f" >NUL 2>NUL
REM legacy temp crash files
del /f /q "%ROOT%\Temp\*.log" >NUL 2>NUL

REM leftovers of an in-use DLL renamed by PreClean (deletable once explorer restarted)
del /f /q "%ROOT%\Tools\apkshellext2\*.old" >NUL 2>NUL
del /f /q "%ROOT%\Tools\*.old" >NUL 2>NUL

REM ---- register new ApkShellext2-Plus (if user enabled icons) ----
if defined REGASM if exist "%ROOT%\Tools\apkshellext2\ApkShellext2.dll" "%REGASM%" /codebase "%ROOT%\Tools\apkshellext2\ApkShellext2.dll" >NUL 2>NUL

REM ---- recreate APKDB file associations / context menus ----
reg add "HKCR\.apk" /f /ve /t REG_SZ /d "Apkdb.apk" >NUL 2>NUL
reg add "HKCR\Apkdb.apk" /f /ve /t REG_SZ /d "Android 应用程序" >NUL 2>NUL
reg add "HKCR\Apkdb.apk\DefaultIcon" /f /ve /t REG_SZ /d "\"%ROOT%\Icon\apk.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.apk\shell" /f /ve /t REG_SZ /d "open" >NUL 2>NUL
reg add "HKCR\Apkdb.apk\shell\open" /f /ve /t REG_SZ /d "查看或安装" >NUL 2>NUL
reg add "HKCR\Apkdb.apk\shell\open" /f /v Icon /t REG_SZ /d "\"%ROOT%\Icon\apk.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.apk\shell\open\command" /f /ve /t REG_SZ /d "\"%ROOT%\Tools\ApkTool\ApkTool.exe\" \"%%1\"" >NUL 2>NUL

reg add "HKCR\.arsc" /f /ve /t REG_SZ /d "Apkdb.arsc" >NUL 2>NUL
reg add "HKCR\Apkdb.arsc" /f /ve /t REG_SZ /d "APK文件源" >NUL 2>NUL
reg add "HKCR\Apkdb.arsc\DefaultIcon" /f /ve /t REG_SZ /d "\"%ROOT%\Icon\fws.ico\"" >NUL 2>NUL

reg add "HKCR\.dex" /f /ve /t REG_SZ /d "Apkdb.dex" >NUL 2>NUL
reg add "HKCR\Apkdb.dex" /f /ve /t REG_SZ /d "Android 源码包" >NUL 2>NUL
reg add "HKCR\Apkdb.dex\DefaultIcon" /f /ve /t REG_SZ /d "\"%ROOT%\Icon\dex.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.dex\shell\open" /f /ve /t REG_SZ /d "查看源码并转JAR格式" >NUL 2>NUL
reg add "HKCR\Apkdb.dex\shell\open" /f /v Icon /t REG_SZ /d "\"%ROOT%\Icon\setup.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.dex\shell\open\command" /f /ve /t REG_SZ /d "\"%ROOT%\seesource.bat\" \"%%1\"" >NUL 2>NUL

reg add "HKCR\.odex" /f /ve /t REG_SZ /d "Apkdb.odex" >NUL 2>NUL
reg add "HKCR\Apkdb.odex" /f /ve /t REG_SZ /d "Android 源码包" >NUL 2>NUL
reg add "HKCR\Apkdb.odex\DefaultIcon" /f /ve /t REG_SZ /d "\"%ROOT%\Icon\dex.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.odex\shell\dex2apk" /f /ve /t REG_SZ /d "合并Odex" >NUL 2>NUL
reg add "HKCR\Apkdb.odex\shell\dex2apk" /f /v Icon /t REG_SZ /d "\"%ROOT%\Icon\setup.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.odex\shell\dex2apk\command" /f /ve /t REG_SZ /d "\"%ROOT%\odex.cmd\" \"%%1\"" >NUL 2>NUL
reg add "HKCR\Apkdb.odex\shell\open" /f /v Icon /t REG_SZ /d "\"%ROOT%\Icon\setup.ico\"" >NUL 2>NUL
reg add "HKCR\Apkdb.odex\shell\open\command" /f /ve /t REG_SZ /d "\"%ROOT%\odex.cmd\" \"%%1\"" >NUL 2>NUL

reg add "HKCR\*\shell\APKDB" /f /ve /t REG_SZ /d "使用 APKDB 编译" >NUL 2>NUL
reg add "HKCR\*\shell\APKDB" /f /v Icon /t REG_SZ /d "\"%ROOT%\Icon\setup.ico\"" >NUL 2>NUL
reg add "HKCR\*\shell\APKDB\command" /f /ve /t REG_SZ /d "\"%ROOT%\apkdb_d.cmd\" \"%%1\"" >NUL 2>NUL

reg add "HKCR\Directory\shell\apkdb" /f /ve /t REG_SZ /d "使用 APKDB 编译" >NUL 2>NUL
reg add "HKCR\Directory\shell\apkdb" /f /v Icon /t REG_SZ /d "\"%ROOT%\Icon\setup.ico\"" >NUL 2>NUL
reg add "HKCR\Directory\shell\apkdb\Command" /f /ve /t REG_SZ /d "\"%ROOT%\apkdb.cmd\" \"%%1\"" >NUL 2>NUL

popd
exit /b 0
'''
open(os.path.join(PAYLOAD, 'Tools', 'cleanup.bat'), 'wb').write(cleanup.replace('\n', '\r\n').encode('gbk'))

# PreClean.bat (runs before overwriting an existing install)
preclean = r'''@echo off
setlocal EnableExtensions
set "OLD=%~1"
if not defined OLD exit /b 0
if not exist "%OLD%" exit /b 0

TASKKILL /F /IM ApkTool.exe /IM adb.exe /IM fastboot.exe >NUL 2>NUL
TASKKILL /F /IM ShuameDaemon.exe /IM shuame_helper.exe >NUL 2>NUL

set "REGASM="
if exist "%windir%\Microsoft.NET\Framework64\v4.0.30319\regasm.exe" set "REGASM=%windir%\Microsoft.NET\Framework64\v4.0.30319\regasm.exe"
if not defined REGASM if exist "%windir%\Microsoft.NET\Framework\v4.0.30319\regasm.exe" set "REGASM=%windir%\Microsoft.NET\Framework\v4.0.30319\regasm.exe"
if defined REGASM if exist "%OLD%\Tools\apkshellext2\ApkShellext2.dll" "%REGASM%" /unregister "%OLD%\Tools\apkshellext2\ApkShellext2.dll" >NUL 2>NUL
if defined REGASM if exist "%OLD%\Tools\apkshellext.dll" "%REGASM%" /unregister "%OLD%\Tools\apkshellext.dll" >NUL 2>NUL

REM Files explorer may have loaded cannot be deleted but CAN be renamed, so the
REM new copy can be written without restarting the shell.
call :release "%OLD%\Tools\apkshellext2\ApkShellext2.dll"
call :release "%OLD%\Tools\apkshellext2\libwebp_x64.dll"
call :release "%OLD%\Tools\apkshellext2\libwebp_x86.dll"
call :release "%OLD%\Tools\apkshellext.dll"

reg delete "HKCR\*\shell\APKDB" /f >NUL 2>NUL
reg delete "HKCR\Directory\shell\apkdb" /f >NUL 2>NUL
reg delete "HKCR\Apkdb.apk" /f >NUL 2>NUL
reg delete "HKCR\Apkdb.arsc" /f >NUL 2>NUL
reg delete "HKCR\Apkdb.dex" /f >NUL 2>NUL
reg delete "HKCR\Apkdb.odex" /f >NUL 2>NUL

exit /b 0

:release
if not exist "%~1" exit /b 0
if exist "%~1.old" del /f /q "%~1.old" >NUL 2>NUL
rem note: ren's second argument must be a bare file name, not a path.
rem A loaded DLL cannot be deleted but can be renamed, so rename first and
rem only fall back to deleting if the rename did not happen.
ren "%~1" "%~nx1.old" >NUL 2>NUL
if exist "%~1" del /f /q "%~1" >NUL 2>NUL
exit /b 0
'''
open(os.path.join(PAYLOAD, 'Tools', 'PreClean.bat'), 'wb').write(preclean.replace('\n', '\r\n').encode('gbk'))
say('[17] cleanup.bat + PreClean.bat written')

# unins.bat: full removal first
p = os.path.join(PAYLOAD, 'unins.bat')
text, enc = read_text(p)
prefix = r'''@ECHO OFF
call "%~dp0Tools\cleanup.bat" >NUL 2>NUL
reg delete "HKCR\.apk" /f >NUL 2>NUL
reg delete "HKCR\.arsc" /f >NUL 2>NUL
reg delete "HKCR\.dex" /f >NUL 2>NUL
reg delete "HKCR\.odex" /f >NUL 2>NUL
reg delete "HKCR\*\shell\APKDB" /f >NUL 2>NUL
reg delete "HKCR\Directory\shell\apkdb" /f >NUL 2>NUL
'''
text = text.replace('@ECHO OFF\r\n', prefix, 1) if '@ECHO OFF\r\n' in text else prefix + text
write_text(p, text, enc)
say('[18] patched unins.bat')

# ---------------------------------------------------------------- version strings
for fn in os.listdir(os.path.join(PAYLOAD, 'language')):
    if not fn.lower().endswith('.ini'):
        continue
    p = os.path.join(PAYLOAD, 'language', fn)
    raw = open(p, 'rb').read()
    raw = raw.replace(b'V2.1.3', b'V2.1.5').replace(b'2015-07-20', b'2026-11-19')
    open(p, 'wb').write(raw)
say('[19] language packs version -> V2.1.5')

# changelog
def prepend_changelog(path, entry):
    raw = open(path, 'rb').read()
    enc = 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else None
    if enc:
        text = raw[3:].decode('utf-8', 'replace')
    else:
        try:
            text = raw.decode('utf-8')
            enc = 'utf-8'
        except UnicodeDecodeError:
            text = raw.decode('gbk', 'replace')
            enc = 'gbk'
    text = entry + text
    data = text.encode(enc)
    if enc == 'utf-8-sig':
        data = b'\xef\xbb\xbf' + data
    open(path, 'wb').write(data)

entry_chs = '''===================================================================

\t\t\tAPKDB 更新特性

___________________________________________________________________
v2.1.5 重制版 2026.11.19
*.升级，Apktool 3.0.3（2026.07.20），保留 250/251/sk 文件名以兼容脚本
*.升级，jadx 1.5.7（2026.11.18，需要 64 位 Java 11+）
*.升级，Smali、Baksmali 3.0.10（2026.08.20）
*.升级，Android platform-tools 37.0.1（adb / fastboot）
*.升级，Android build-tools 37.0.0（zipalign / aapt / aapt2 / apksigner）
*.升级，7-Zip 26.06（x86 / x64）
*.升级，OptiPNG 0.7.8（7.9.1 无官方 Windows 二进制）
*.升级，GNU Wget 1.25.0（替换 2005 年的 1.10.x）
*.升级，ApkShellext2-Plus（上游 kkguo/ApkShellext2 的增强分支，2.1.5.0）
*.替换，ShakaApktool -> Apktool 3.0.3（上游 2017 年后停更）
*.替换，signapk（仅 v1）-> apksigner（v1+v2+v3）
*.替换，bootimg（2015）-> 新增 MagiskBoot 27.0，保留旧 bootimg 兼容老镜像
*.删除，ApkTool333（apkinstaller 4.7 + 刷机精灵组件）、ShuameDaemon、AndroidAssistHelper
*.删除，旧版 apkshellext.dll、Apktool 2.0~2.4 jar、旧 jadx 依赖
*.新增，Tools\\cleanup.bat + cleanup.reg：覆盖安装/卸载时清理旧版本文件、注册表、右键菜单、Shell 扩展，无残留
*.新增，Tools\\apksigner + Tools\\Signer\\apksigner-shim.bat
*.修复，批量回编译改为先 zipalign 再 apksigner，避免 v2 签名失效
*.修复，安装/卸载只注册 ApkShellext2-Plus，不再注册旧 Shell 扩展
*.注意，Apktool 3.x 不再支持 32 位平台与 aapt1；jadx 1.5.7 需要 64 位 Java 11+
___________________________________________________________________

'''
prepend_changelog(os.path.join(PAYLOAD, 'Changelog-CHS.txt'), entry_chs)

entry_cht = entry_chs.replace('重制版', '重製版').replace('升级', '升級').replace('替换', '替換').replace('删除', '刪除').replace('新增', '新增').replace('保留', '保留').replace('兼容', '相容').replace('脚本', '腳本').replace('残留', '殘留').replace('修复', '修復').replace('注意', '注意')
prepend_changelog(os.path.join(PAYLOAD, 'Changelog-CHT.txt'), entry_cht)
say('[20] changelog updated')

# ---------------------------------------------------------------- D.bat
dpath = os.path.join(BASE, 'apkdb_extract', 'D.bat')
text, enc = read_text(dpath, ('gbk', 'utf-8'))
text = text.replace('if not exist "%~dp0APKDB" goto r1',
                    'if exist "%~dp0APKDB" call "%~dp0APKDB_X\\Tools\\PreClean.bat" "%~dp0APKDB"\r\nif not exist "%~dp0APKDB" goto r1', 1)
text = text.replace('echo y|cacls "%~dp0APKDB" /e /g Everyone:f Administrators:f Users:f SYSTEM:f',
                    'echo y|cacls "%~dp0APKDB" /e /g Everyone:f Administrators:f Users:f SYSTEM:f >NUL 2>NUL')
text = text.replace('start "" "%~dp0APKDB\\Setup.exe"',
                    'rem drop leftovers of an in-use DLL that PreClean had to rename\r\n'
                    'del /f /q "%~dp0APKDB\\Tools\\apkshellext2\\*.old" >NUL 2>NUL\r\n'
                    'del /f /q "%~dp0APKDB\\Tools\\*.old" >NUL 2>NUL\r\n'
                    'call "%~dp0APKDB\\Tools\\cleanup.bat" >NUL 2>NUL\r\n'
                    'start "" "%~dp0APKDB\\Setup.exe"')
# D.bat is the SFX entry point and calls the UTF-8 cleanup.bat, so the console
# has to be on UTF-8 before that file is opened.
if 'chcp 65001' not in text:
    text = text.replace('@echo off\r\n', '@echo off\r\nchcp 65001 >nul\r\n', 1)
open(os.path.join(BUILD, 'D.bat'), 'wb').write(text.encode('utf-8'))
say('[21] D.bat patched (UTF-8 + chcp)')

# ---------------------------------------------------------------- batch script fixes
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('fix_bats', os.path.join(BASE, 'fix_bats.py'))
_fix = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_fix)
_fix.apply(PAYLOAD, read_text, write_text, say)

# ---------------------------------------------------------------- script encoding
# UTF-8 conversion was prototyped and rejected: cmd.exe intermittently mis-parses
# UTF-8 batch files that contain CJK text, even with chcp 65001 applied before the
# file is opened (same input file, two runs, one clean and one with 125 parse
# errors). Shipping that would make the tool flaky, so the scripts stay in the
# original GBK/CP936 encoding, which is what cmd.exe is designed for.
# See SCRIPT-AUDIT.md section "编码" for the measurements.
say('[utf8] skipped by design: scripts stay GBK/CP936 (see SCRIPT-AUDIT.md)')

# ---------------------------------------------------------------- package SFX
archive = os.path.join(BUILD, 'payload.7z')
run([SEVEN, 'a', '-t7z', '-mx=9', '-m0=lzma2', '-ms=on', archive, 'APKDB_X', 'D.bat'], cwd=BUILD)
say('[22] archive built: %.1f MB' % (os.path.getsize(archive) / 1048576.0))

orig = open(os.path.join(r'G:\APKDB_v2.1.4_20210702.exe'), 'rb').read()
i = orig.find(b';!@Install@!UTF-8!')
j = orig.find(b';!@InstallEnd@!', i)
stub = orig[:i]
old_cfg = orig[i:j + 16].decode('utf-8')
cfg = old_cfg
cfg = cfg.replace('BeginPrompt="警告：拒绝360老流氓！！',
                  'BeginPrompt="APKDB v2.1.5 (2026-11-19) 重制版\\n需要 Java 8+（jadx 需 Java 11+ 64位）\\n警告：拒绝360老流氓！！')
out = os.path.join(BUILD, 'APKDB_v2.1.5_20261119.exe')
with open(out, 'wb') as f:
    f.write(stub)
    f.write(cfg.encode('utf-8'))
    f.write(b'\n')
    f.write(open(archive, 'rb').read())
say('[23] SFX built: %s (%.1f MB)' % (out, os.path.getsize(out) / 1048576.0))

open(os.path.join(BUILD, 'BUILD-LOG.txt'), 'wb').write('\r\n'.join(log).encode('utf-8'))
