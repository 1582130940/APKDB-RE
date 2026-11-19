# -*- coding: utf-8 -*-
"""Post-build fixes for APKDB batch scripts.

Each fix targets a defect confirmed by reading the generated payload, not a style
preference. apply() is called from build_apkdb.py after the payload is assembled.
"""
import os
import re


def apply(PAYLOAD, read_text, write_text, say):
    def edit(rel, fn, label, force_enc=None):
        p = os.path.join(PAYLOAD, rel)
        if not os.path.exists(p):
            say('[fix] SKIP missing %s' % rel)
            return
        text, enc = read_text(p)
        new = fn(text)
        if new == text:
            say('[fix] NOCHANGE %s (%s)' % (rel, label))
            return
        write_text(p, new, force_enc or enc)
        say('[fix] %s: %s' % (rel, label))

    # ---------------------------------------------------------------- keytool2
    # apkdb.cmd / apkdb_d.cmd define :DP/:DP86/:javahome/:CPNV/:CP twice (the
    # "查看签名" block and the "制作签名包" block). CMD always jumps to the first
    # definition, so with JAVA_HOME set the keystore wizard silently ran the
    # printcert flow instead. Isolate the second block with distinct labels.
    def isolate_keytool2(text):
        m = re.search(r'(?mi)^:Keytool2[ \t]*\r?$', text)
        if not m:
            return text
        start = m.end()
        m2 = re.search(r'(?mi)^:Keytool22[ \t]*\r?$', text[start:])
        if not m2:
            return text
        end = start + m2.start()
        region = text[start:end]

        def rename_label(mo):
            return mo.group(1) + ':' + mo.group(2) + '2' + mo.group(3)

        region = re.sub(
            r'(?mi)^([ \t]*):(javahome|cpnv|dp86|dp|cp)([ \t]*)\r?$',
            rename_label, region)
        region = re.sub(
            r'(?i)\bgoto[ \t]+(javahome|cpnv|dp86|dp|cp)\b',
            lambda mo: 'goto ' + mo.group(1) + '2', region)
        return text[:start] + region + text[end:]

    for fn in ('apkdb.cmd', 'apkdb_d.cmd'):
        edit(fn, isolate_keytool2, 'Keytool2 duplicate labels isolated')

    # apkdb_d.cmd has its own defects on top of the shared ones
    def fix_apkdb_d(text):
        # "%dexd_ERRORLEVEL%" is never defined -> "IF  == 1" is a syntax error,
        # so a failed baksmali still printed "success"
        text = text.replace('%dexd_ERRORLEVEL%', '%ERRORLEVEL%')
        # "goto 230c" targets a label that does not exist: any jar containing
        # classes2.dex aborted the whole decompile. Let it fall through to the
        # normal baksmali path, which accepts zip/jar input.
        text = text.replace(
            '&&if /i exist "%Temp%\\%~n1\\classes2.dex" goto 230c', '')
        # after "查看签名信息" the script did "goto Start", but the menu label is
        # ":StartAPK" -> the window died instead of returning to the menu
        text = re.sub(r'(?mi)^goto Start[ \t]*\r?$', 'goto StartAPK', text)
        # keytool was called with an unquoted path, breaking on spaces
        text = text.replace('keytool -file %1 -printcert',
                            'keytool -file "%~1" -printcert')
        return text

    edit('apkdb_d.cmd', fix_apkdb_d, 'dexd_ERRORLEVEL typo + dead goto 230c')

    # ---------------------------------------------------------------- odex.cmd
    def fix_odex(text):
        # 1) ":A16" was written without the colon -> "goto A16" aborted the script
        text = re.sub(r'(?mi)^A16[ \t]*\r?$', ':A16', text, count=1)
        # 2) "apktool bs" is a ShakaApktool-only verb; Apktool 3 has no such
        #    command. baksmali 3 exposes the same work as "deodex".
        text = re.sub(
            r'java -jar "%~dp0apktool\\%apktooljar%" bs -x -a (\S+) %1 -d "%fr%" -o "([^"]+)"',
            r'java -jar "%~dp0apktool\\baksmali.jar" deodex -a \1 -d "%fr%" -o "\2" %1',
            text)
        # 3) second ":A71" (the "any API" path) shadowed nothing but duplicated
        #    the name; give it its own label.
        hits = [m.start() for m in re.finditer(r'(?mi)^:A71[ \t]*\r?$', text)]
        if len(hits) > 1:
            pos = hits[1]
            end = text.find('\n', pos)
            if end < 0:
                end = len(text)
            line = text[pos:end]
            text = text[:pos] + re.sub(r'(?i):A71', ':AANY', line) + text[end:]
        return text

    edit('odex.cmd', fix_odex, 'A16 label, bs -> baksmali deodex, A71 duplicate')

    # ---------------------------------------------------------------- sign.bat
    # sign.bat is invoked with CALL from apkdb.cmd / apkdb_d.cmd. A bare "exit"
    # terminates the whole console, killing the parent flow.
    def fix_sign(text):
        return re.sub(r'(?mi)^([ \t]*)exit[ \t]*\r?$', r'\1exit /b', text)

    edit('apktool/sign.bat', fix_sign, 'exit -> exit /b (called via CALL)')

    # ---------------------------------------------------------------- optipng.cmd
    def fix_optipng_cmd(text):
        text = text.replace('set apk=%1', 'set "apk=%~1"')
        text = text.replace('md %1\\01%optipng04% >NUL 2>NUL',
                            'md "%apk%\\01%optipng04%" >NUL 2>NUL')
        text = text.replace('md %1\\02%optipng06% >NUL 2>NUL',
                            'md "%apk%\\02%optipng06%" >NUL 2>NUL')
        text = re.sub(r'FOR %%F IN \(%1\\"\*\.apk"\) DO \(call :optipng "%%F"\)',
                      'for %%F in ("%~1\\*.apk") do (call :optipng "%%F")\r\nexit /b',
                      text, flags=re.I)
        text = text.replace('IF %1 == () goto end', 'if "%~1"=="" goto :eof')
        # %parent% was stored WITH quotes, so building "%parent%\7zip\..." produced
        # a doubly-quoted, unusable path ("...Tools"\7zip\64\7z.exe")
        text = text.replace('set parent="%~dp0Tools"', 'set "parent=%~dp0Tools"')
        text = text.replace('set szip="%parent%\\7zip\\%bit%\\7z.exe"',
                            'set "szip=%parent%\\7zip\\%bit%\\7z.exe"')
        text = text.replace('set optipng="%parent%\\optipng.exe"',
                            'set "optipng=%parent%\\optipng.exe"')
        text = text.replace('set signer=%~dp0Tools\\signer',
                            'set "signer=%~dp0Tools\\signer"')
        # %ZIP% is never defined in this script (7-Zip path lives in %szip%)
        text = text.replace('%ZIP% d "%apk%', '%szip% d "%apk%')
        text = text.replace('if not %PROCESSOR_ARCHITECTURE%==x86 set bit=64',
                            'if /i not "%PROCESSOR_ARCHITECTURE%"=="x86" set bit=64')
        return text

    edit('optipng.cmd', fix_optipng_cmd, 'arg quoting, fall-through, %ZIP% -> %szip%')

    # ---------------------------------------------------------------- Tools/optipng.bat
    def fix_optipng_bat(text):
        text = text.replace('IF %1 == () goto end', 'if "%~1"=="" goto :eof')
        text = text.replace('%optipng% -o7 %1', '%optipng% -o7 "%~1"')
        return text

    edit('Tools/optipng.bat', fix_optipng_bat, 'arg test + quoting')

    # ---------------------------------------------------------------- apkdb.cmd
    def fix_apkdb(text):
        # second ":b1x" is the "missing input dirs" message; gotos from :bxxx
        # landed on the first (full rebuild) definition instead.
        hits = [m.start() for m in re.finditer(r'(?mi)^:b1x[ \t]*\r?$', text)]
        if len(hits) > 1:
            pos = hits[1]
            end = text.find('\n', pos)
            end = len(text) if end < 0 else end + 1
            text = text[:pos] + ':b1x_err\r\n' + text[end:]
            start = re.search(r'(?mi)^:bxxx[ \t]*\r?$', text)
            if start and start.start() < pos:
                head, tail = text[:start.start()], text[start.start():]
                tail = tail.replace('goto b1x\r\n', 'goto b1x_err\r\n')
                tail = tail.replace('goto b1x\n', 'goto b1x_err\n')
                text = head + tail
        # :bxxx2 looped onto itself forever when resources.arsc was missing
        text = text.replace('resources.arsc goto bxxx2', 'resources.arsc goto b1x_err')
        # menu item [7] jumped to a label that only exists in apkdb_d.cmd
        if re.search(r'(?mi)^:APKinTool[ \t]*\r?$', text) is None:
            text = text.replace('GOTO APKinTool',
                                'start "" "%~dp0apktool.exe" && GOTO StartAPK', 1)
        # duplicate ":7ZIP" (apk / jar variants): the jar CALL hit the apk body
        hits = [m.start() for m in re.finditer(r'(?mi)^:7ZIP[ \t]*\r?$', text)]
        if len(hits) > 1:
            pos = hits[1]
            end = text.find('\n', pos)
            end = len(text) if end < 0 else end + 1
            text = text[:pos] + ':7ZIPJAR\r\n' + text[end:]
            text = text.replace('Call :7ZIP "%%j"', 'Call :7ZIPJAR "%%j"')
        return text

    edit('apkdb.cmd', fix_apkdb, 'b1x duplicate + bxxx2 infinite loop')

    # ---------------------------------------------------------------- install.bat
    # Full rewrite. The 2.1.4 flow had four defects that made "显示APK自身图标"
    # fail or look like a crash:
    #   1. no elevation -> RegAsm reports "需要管理员权限" and nothing is installed,
    #      yet the script still printed 安装完成;
    #   2. "%PROCESSOR_IDENTIFIER% | FIND /i x86" depends on Windows find.exe;
    #      any find.exe shim earlier in PATH makes it scan the disk / return wrongly;
    #   3. no .NET 4.8 check although ApkShellext2-Plus targets 4.8;
    #   4. ":end" did mode con + mshta + unconditional taskkill explorer, so the
    #      window vanished instantly and the desktop flashed.
    new_install = '''@ECHO OFF
setlocal EnableExtensions
if /i not exist "%~dp0language\\Language.bat" ( copy /a /d /y "%~dp0language\\Language.bat.ini" "%~dp0language\\Language.bat" >nul 2>nul )
call "%~dp0language\\Language.bat"
title %install015%
color a0

rem ================= administrator rights =================
if /i "%~1"=="--elevated" goto elevated
>nul 2>&1 "%SYSTEMROOT%\\system32\\cacls.exe" "%SYSTEMROOT%\\system32\\config\\system"
if not errorlevel 1 goto elevated
cls
ECHO.
ECHO  写入注册表、注册 Shell 扩展需要管理员权限。
ECHO  正在请求管理员权限，请在弹出窗口中选择“是”...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '--elevated' -Verb RunAs" >nul 2>nul
if errorlevel 1 (
  ECHO.
  ECHO  无法自动获取管理员权限。
  ECHO  请关闭本窗口，右键点击 install.bat 选择“以管理员身份运行”。
  ECHO.
  pause
)
exit /b

:elevated
cd /d "%~dp0"

rem ================= runtime detection =================
set "REGASM=%windir%\\Microsoft.NET\\Framework\\v4.0.30319\\regasm.exe"
if /i not "%PROCESSOR_ARCHITECTURE%"=="x86" set "REGASM=%windir%\\Microsoft.NET\\Framework64\\v4.0.30319\\regasm.exe"

set "NETREL="
for /f "tokens=3" %%v in ('reg query "HKLM\\SOFTWARE\\Microsoft\\NET Framework Setup\\NDP\\v4\\Full" /v Release 2^>nul') do set "NETREL=%%v"
set "NETNUM="
if defined NETREL set /a NETNUM=%NETREL% >nul 2>nul
set "NETFX_OK="
if not defined NETNUM goto netfx_done
if %NETNUM% GEQ 528040 set "NETFX_OK=1"
:netfx_done

set "ICONSTATE=未启用"
call "%~dp0Tools\\cleanup.bat"
xcopy "%~dp0Temp\\Signer" "%~dp0Tools\\Signer\\" /e /g /r /h /a /s /y /c /q >nul 2>nul

rem ================= apk installer choice =================
:REG
cls
ECHO.
ECHO.
ECHO.
ECHO. ===================================================
ECHO.
ECHO.  %install016%
ECHO.
ECHO.
ECHO.           [Y] %install017%
ECHO.           [N] %install018%
ECHO. ____________________________________________________
set ID=Y
set /p ID= ^>^>%install012%(%apkdb021%=Y):%=% 
if /i "%id%"=="Y" goto new
if /i "%id%"=="N" goto old
goto REG
::
::
:new
if exist "%~dp0Temp\\unapk.reg" regedit /s "%~dp0Temp\\unapk.reg" >nul 2>nul
reg delete "HKEY_CLASSES_ROOT\\.apk" /f >nul 2>nul
reg add "HKCR\\.apk" /f /ve /t REG_SZ /d "Apkdb.apk" >nul 2>nul
reg add "HKCR\\Apkdb.apk" /f /ve /t REG_SZ /d "%Setup009%" >nul 2>nul
reg add "HKCR\\Apkdb.apk\\DefaultIcon" /f /ve /t REG_SZ /d "\\"%~dp0Icon\\apk.ico\\"" >nul 2>nul
reg add "HKCR\\Apkdb.apk\\shell" /f /ve /t REG_SZ /d "open" >nul 2>nul
reg add "HKCR\\Apkdb.apk\\shell\\open" /f /ve /t REG_SZ /d "%Setup010%" >nul 2>nul
reg add "HKCR\\Apkdb.apk\\shell\\open" /f /v Icon /t REG_SZ /d "\\"%~dp0Icon\\apk.ico\\"" >nul 2>nul
reg add "HKCR\\Apkdb.apk\\shell\\open\\command" /f /ve /t REG_SZ /d "\\"%~dp0Tools\\ApkTool\\ApkTool.exe\\" \\"%%1\\"" >nul 2>nul
goto start
::
:old
if not exist "%~dp0apk.reg" goto new
regedit /s "%~dp0apk.reg" >nul 2>nul
::
:start
title %install001%
cls
color a0
ECHO.
ECHO.___________________________________________________________________
ECHO.
ECHO.  %install002%
ECHO.
ECHO.  %install003%
ECHO.        %install004%
ECHO.
ECHO.   %install005%
ECHO.
ECHO.   %install006%
ECHO.   %install007%
ECHO.
ECHO.___________________________________________________________________
ECHO.  [1]%install009%  [2]%install010%  [3]%install011%
ECHO.________________
set ID=1
set /p ID= ^>^> %install012%(%apkdb021%=1):%=% 
if /i "%id%"=="1" goto noicon
if /i "%id%"=="2" goto apkico
if /i "%id%"=="3" goto netfx_dl
goto start
::
:netfx_dl
start "" "https://www.microsoft.com/en-us/download/details.aspx?id=17718"
goto start
::
:apkico
title %install013%
cls
ECHO.
ECHO.
ECHO.
ECHO. %install014%
ECHO.________________________________________________
if not defined NETFX_OK goto nofx
if not exist "%REGASM%" goto nofx
if not exist "%~dp0Tools\\apkshellext2\\ApkShellext2.dll" goto nofx
>>"%~dp0install.log" echo [%TIME%] RegAsm output:
"%REGASM%" /codebase "%~dp0Tools\\apkshellext2\\ApkShellext2.dll" >>"%~dp0install.log" 2>&1
if errorlevel 1 goto iconfail
>"%~dp0Tools\\.icons-enabled" echo 1
set "ICONSTATE=已启用"
ECHO.
ECHO  [OK] 已启用"显示 APK 自身图标"。
goto end
::
:nofx
ECHO.
ECHO  [跳过] 未检测到 .NET Framework 4.8 或 RegAsm。
ECHO         该功能需要 .NET Framework 4.8，其余功能不受影响。
ECHO         装好 4.8 后重新运行 Setup.exe 即可开启。
>>"%~dp0install.log" echo [%TIME%] icon skipped: .NET 4.8 or RegAsm not found
ECHO.
pause
goto end
::
:iconfail
ECHO.
ECHO  [失败] 注册 Shell 扩展未成功（RegAsm 返回错误）。
ECHO         常见原因：安全软件拦截、系统策略禁止。
ECHO         已按“不启用图标”继续，其余功能不受影响。
>>"%~dp0install.log" echo [%TIME%] icon failed: RegAsm returned an error
ECHO.
pause
goto end
::
:noicon
if exist "%~dp0Tools\\.icons-enabled" del /f /q "%~dp0Tools\\.icons-enabled" >nul 2>nul
if exist "%REGASM%" if exist "%~dp0Tools\\apkshellext2\\ApkShellext2.dll" "%REGASM%" /unregister "%~dp0Tools\\apkshellext2\\ApkShellext2.dll" >nul 2>nul
set "ICONSTATE=未启用"
goto end
::
:end
echo.
echo  ============================================================
echo   %install020%
echo.
echo   目录    : %~dp0
echo   图标功能: %ICONSTATE%
echo  ============================================================
>>"%~dp0install.log" echo [%TIME%] install finished, icon=%ICONSTATE%
if not "%ICONSTATE%"=="已启用" goto bye
echo.
echo   图标组件已注册。需要重启资源管理器一次，新图标才会显示。
echo   [R] 现在重启     直接回车 = 稍后自己重启（或重启电脑）
echo.
set "RS="
set /p RS= ^>^> 
if /i not "%RS%"=="R" goto bye
echo.
echo   正在重启资源管理器...
taskkill /f /im explorer.exe >nul 2>nul
ping -n 2 127.0.0.1 >nul
if exist "%~dp0Tools\\apkshellext2\\*.old" del /f /q "%~dp0Tools\\apkshellext2\\*.old" >nul 2>nul
if exist "%~dp0Tools\\*.old" del /f /q "%~dp0Tools\\*.old" >nul 2>nul
if exist "%LOCALAPPDATA%\\IconCache.db" del /f /q "%LOCALAPPDATA%\\IconCache.db" >nul 2>nul
if exist "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer" del /f /q "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\iconcache_*.db" >nul 2>nul
start "" "%windir%\\explorer.exe"
:bye
echo.
echo   按任意键关闭本窗口...
pause>nul
endlocal
exit /b 0
'''

    edit('install.bat', lambda _t: new_install, 'rewrite: elevation, .NET 4.8, no mshta/taskkill surprise', force_enc='gbk')

    # ---------------------------------------------------------------- uninstapkico.bat
    def fix_uninstapkico(text):
        old = ('echo %PROCESSOR_IDENTIFIER% | FIND /i "x86"\r\n'
               '\r\n'
               'set FRAMEWORK=%windir%\\Microsoft.NET\\Framework\r\n'
               'set DOTNETVERSION=v4.0.30319\r\n'
               'IF %ERRORLEVEL%==1 (\r\n'
               '  set FRAMEWORK=%FRAMEWORK%64\r\n'
               ')')
        new = ('set FRAMEWORK=%windir%\\Microsoft.NET\\Framework\r\n'
               'set DOTNETVERSION=v4.0.30319\r\n'
               'if /i not "%PROCESSOR_ARCHITECTURE%"=="x86" set FRAMEWORK=%FRAMEWORK%64')
        text = text.replace(old, new)
        text = text.replace('/d "\\"%~dp0Icon\\apk.ico"\\"', '/d "\\"%~dp0Icon\\apk.ico\\""')
        text = re.sub(r'(?mi)^([ \t]*)exit[ \t]*\r?$', r'\1exit /b', text)
        if 'TASKKILL /F /IM explorer.exe' in text:
            text = text.replace('TASKKILL /F /IM explorer.exe >nul 2>NUL\r\n'
                                'attrib -s -r -h "%userprofile%\\AppData\\Local\\iconcache.db" >nul 2>NUL\r\n'
                                'del /f /q "%userprofile%\\AppData\\Local\\iconcache.db" >nul 2>NUL\r\n'
                                'START "" "%windir%\\explorer.exe" >nul 2>NUL',
                                'taskkill /F /IM explorer.exe >nul 2>NUL\r\n'
                                'ping -n 2 127.0.0.1 >nul\r\n'
                                'if exist "%LOCALAPPDATA%\\IconCache.db" del /f /q "%LOCALAPPDATA%\\IconCache.db" >nul 2>NUL\r\n'
                                'if exist "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer" del /f /q "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\iconcache_*.db" >nul 2>NUL\r\n'
                                'start "" "%windir%\\explorer.exe" >nul 2>NUL')
        return text

    edit('uninstapkico.bat', fix_uninstapkico, 'find -> PROCESSOR_ARCHITECTURE, exit /b, cache path')

    # ---------------------------------------------------------------- upstream shell-ext scripts
    for rel in ('Tools/apkshellext2/install.bat', 'Tools/apkshellext2/uninstall.bat'):
        def fix_upstream(text):
            for nl in ('\r\n', '\n'):
                text = text.replace('echo %PROCESSOR_IDENTIFIER% | FIND /i "x86"' + nl, '')
                text = text.replace(
                    'IF %ERRORLEVEL%==1 (' + nl + '  set FRAMEWORK=%FRAMEWORK%64' + nl + ')',
                    'if /i not "%PROCESSOR_ARCHITECTURE%"=="x86" set FRAMEWORK=%FRAMEWORK%64')
            return text
        edit(rel, fix_upstream, 'find -> PROCESSOR_ARCHITECTURE')

    # ---------------------------------------------------------------- cleanup.bat
    def fix_cleanup(text):
        if 'uninstall mode' not in text:
            text = text.replace('pushd "%ROOT%"\r\n',
                                'pushd "%ROOT%"\r\n'
                                'rem uninstall mode: clean only, never re-register or rebuild menus\r\n'
                                'if /i "%~1"=="uninstall" goto :uninstall\r\n', 1)
        # only re-register when the user actually enabled icons
        text = text.replace(
            'if defined REGASM if exist "%ROOT%\\Tools\\apkshellext2\\ApkShellext2.dll" "%REGASM%" /codebase',
            'if exist "%ROOT%\\Tools\\.icons-enabled" if defined REGASM if exist "%ROOT%\\Tools\\apkshellext2\\ApkShellext2.dll" "%REGASM%" /codebase')
        if re.search(r'(?mi)^:uninstall[ \t]*\r?$', text) is None:
            text = text.replace(
                'popd\r\nexit /b 0\r\n',
                'popd\r\nexit /b 0\r\n\r\n'
                ':uninstall\r\n'
                'if exist "%ROOT%\\Tools\\.icons-enabled" del /f /q "%ROOT%\\Tools\\.icons-enabled" >NUL 2>NUL\r\n'
                'if defined REGASM if exist "%ROOT%\\Tools\\apkshellext2\\ApkShellext2.dll" "%REGASM%" /unregister "%ROOT%\\Tools\\apkshellext2\\ApkShellext2.dll" >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.apk" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.arsc" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.dex" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.odex" /f >NUL 2>NUL\r\n'
                'del /f /q "%ROOT%\\Tools\\apkshellext2\\*.old" >NUL 2>NUL\r\n'
                'del /f /q "%ROOT%\\Tools\\*.old" >NUL 2>NUL\r\n'
                'popd\r\nexit /b 0\r\n')
        return text

    edit('Tools/cleanup.bat', fix_cleanup, 'uninstall mode + conditional registration')

    # ---------------------------------------------------------------- unins.bat
    def fix_unins(text):
        # The 2.1.4 file contained mojibake shortcut paths (GBK bytes that were
        # not valid GBK) and only deleted a handful of keys. Rewrite it cleanly
        # and in uninstall mode, so nothing is re-registered behind our back.
        return ('@ECHO OFF\r\n'
                'setlocal\r\n'
                'if exist "%~dp0Tools\\.icons-enabled" del /f /q "%~dp0Tools\\.icons-enabled" >NUL 2>NUL\r\n'
                'call "%~dp0Tools\\cleanup.bat" uninstall >NUL 2>NUL\r\n'
                'del /f /q "%PUBLIC%\\Desktop\\XML文件编辑器.lnk" >NUL 2>NUL\r\n'
                'del /f /q "%PUBLIC%\\桌面\\XML文件编辑器.lnk" >NUL 2>NUL\r\n'
                'rd /s /q "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\APKDB" >NUL 2>NUL\r\n'
                'rd /s /q "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\APKDB" >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.apk" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.arsc" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.dex" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\.odex" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\*\\shell\\APKDB" /f >NUL 2>NUL\r\n'
                'reg delete "HKCR\\Directory\\shell\\apkdb" /f >NUL 2>NUL\r\n'
                'cd /d "%USERPROFILE%" >NUL 2>NUL\r\n'
                'exit /b 0\r\n')

    edit('unins.bat', fix_unins, 'rewrite: uninstall mode, no mojibake, full key removal', force_enc='gbk')

    # ---------------------------------------------------------------- seesource.bat
    def fix_seesource(text):
        return text.replace('if exist %~p1seesource.bat',
                            'if exist "%~p1seesource.bat"')

    edit('seesource.bat', fix_seesource, 'quote %~p1')

    # ---------------------------------------------------------------- reduce.bat
    def fix_reduce(text):
        if 'delang' in text and 'if not defined delang' not in text:
            text = 'if not defined delang exit /b 1\r\ncd /d "%delang%\\res" || exit /b 1\r\n' + \
                   re.sub(r'(?mi)^cd /d %delang%\\res[ \t]*\r?\n', '', text, count=1)
        return text

    edit('Tools/reduce.bat', fix_reduce, 'guard undefined %delang%')

    # ---------------------------------------------------------------- JavaSet.bat
    def fix_javaset(text):
        if 'where wmic' in text:
            return text
        old = ('wmic ENVIRONMENT where "name=\'path\' and username=\'<system>\'" '
               'set VariableValue="%%JAVA_HOME%%\\bin;%%JAVA_HOME%%\\jre\\bin;%path%"')
        new = ('where wmic >nul 2>nul\r\n'
               'if errorlevel 1 (\r\n'
               '  echo 警告: 本系统未提供 wmic，PATH 未被修改。\r\n'
               '  echo 请手动把 %%JAVA_HOME%%\\bin 和 %%JAVA_HOME%%\\jre\\bin 加入系统 PATH。\r\n'
               ') else (\r\n'
               '  ' + old + '\r\n'
               ')')
        return text.replace(old, new)

    edit('Tools/JavaSet.bat', fix_javaset, 'wmic removal fallback')

    # ---------------------------------------------------------------- FLV2MP4.bat
    def fix_flv(text):
        text = text.replace('goto :end2', 'goto :end')
        if 'ffmpeg.exe' not in text.split('\r\n')[2:6]:
            pass
        if '缺少 ffmpeg.exe' not in text:
            text = text.replace('@ECHO OFF\r\n',
                                '@ECHO OFF\r\n'
                                'if not exist "%~dp0ffmpeg.exe" (\r\n'
                                '  ECHO 缺少 ffmpeg.exe，视频转换不可用。\r\n'
                                '  ECHO 请把 ffmpeg.exe 放到 %~dp0 后重试。\r\n'
                                '  pause\r\n'
                                '  exit /b 1\r\n'
                                ')\r\n', 1)
        return text

    edit('Tools/FLV2MP4.bat', fix_flv, 'end2 label + ffmpeg guard')

    # ---------------------------------------------------------------- Update/update.bat
    def fix_update(text):
        # the upstream update server (idoog.me) no longer resolves
        notice = ('@echo off\r\n'
                  'mode con lines=20 cols=70\r\n'
                  'color 0e\r\n'
                  'echo.\r\n'
                  'echo  ============================================================\r\n'
                  'echo   APKDB v2.1.5 重制版 (2026-11-19)\r\n'
                  'echo.\r\n'
                  'echo   原在线更新服务器 idoog.me 已停止解析，本版本不再提供\r\n'
                  'echo   在线检测更新。请从发布页获取新的整合包。\r\n'
                  'echo.\r\n'
                  'echo   内置组件版本可通过以下命令确认：\r\n'
                  'echo     java -jar apktool\\apktool250.jar --version\r\n'
                  'echo     jadx\\bin\\jadx.bat --version\r\n'
                  'echo     Tools\\ADB\\adb.exe version\r\n'
                  'echo  ============================================================\r\n'
                  'echo.\r\n'
                  'pause>nul\r\n'
                  'exit /b 0\r\n')
        return notice

    edit('Update/update.bat', fix_update, 'dead update server -> offline notice')

    # ---------------------------------------------------------------- line endings
    # cmd.exe is line-ending tolerant in most cases, but LF-only batch files
    # break "goto" scanning and multi-line blocks on some builds.
    normalized = 0
    for dirpath, _, names in os.walk(PAYLOAD):
        for n in names:
            if not n.lower().endswith(('.bat', '.cmd')):
                continue
            p = os.path.join(dirpath, n)
            raw = open(p, 'rb').read()
            norm = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            if norm != raw:
                open(p, 'wb').write(norm)
                normalized += 1
    say('[fix] CRLF normalized in %d script(s)' % normalized)
