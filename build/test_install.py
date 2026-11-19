# -*- coding: utf-8 -*-
"""Dry-run harness for install.bat: stubs registry/regasm/explorer, forces branches."""
import io, os, shutil, subprocess, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = 'verify/APKDB_X'
WORK = 'testrun'


def prepare(force_option, regasm_rc, netfx_ok=True, option1=False, tag='x'):
    root = WORK + '_' + tag
    if os.path.isdir(root):
        shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    dst = os.path.join(root, 'APKDB')
    shutil.copytree(SRC, dst)
    p = os.path.join(dst, 'install.bat')
    t = open(p, 'rb').read().decode('gbk')

    out = []
    for line in t.split('\r\n'):
        s = line.strip()
        low = s.lower()
        if low.startswith('reg ') or low.startswith('regedit '):
            out.append('echo [stub-reg] ' + s[:50])
        elif s.startswith('"%REGASM%" /codebase') or s.startswith('"%REGASM%" /unregister'):
            out.append('cmd /c exit %d' % regasm_rc)
        elif low.startswith('call "%~dp0tools\\cleanup.bat"'):
            out.append('echo [stub] cleanup skipped')
        elif low.startswith('taskkill'):
            out.append('echo [stub] taskkill explorer')
        elif low.startswith('start "" "%windir%\\explorer.exe"'):
            out.append('echo [stub] start explorer')
        elif low.startswith('powershell -noprofile'):
            out.append('echo [stub] elevation skipped')
        elif low.startswith('xcopy'):
            out.append('rem xcopy skipped')
        else:
            out.append(line)
    t = '\r\n'.join(out)

    if not netfx_ok:
        t = t.replace('set "NETFX_OK="\r\n',
                      'set "NETFX_OK="\r\ngoto netfx_forced\r\n', 1)
        t = t.replace(':netfx_done\r\n', ':netfx_done\r\n:netfx_forced\r\n', 1)

    if option1:
        t = t.replace('set ID=1\r\nset /p ID= ^>^> %install012%(%apkdb021%=1):%=% ',
                      'set ID=1\r\nrem forced option 1', 1)
    else:
        t = t.replace('set ID=1\r\nset /p ID= ^>^> %install012%(%apkdb021%=1):%=% ',
                      'set ID=2\r\nrem forced option 2', 1)
    open(os.path.join(dst, 'install_test.bat'), 'wb').write(t.encode('gbk'))
    return dst


def run(dst, label):
    inp = os.path.join(os.path.dirname(dst), 'in.txt')
    open(inp, 'wb').write(b'Y\r\n\r\n\r\n')
    p = os.path.join(dst, 'install_test.bat')
    r = subprocess.run(['cmd.exe', '/c', p, '--elevated'],
                       stdin=open(inp, 'rb'), capture_output=True, timeout=120)
    text = r.stdout.decode('gbk', 'replace').replace('\r', '')
    print('=' * 70)
    print(label, ' rc=%s' % r.returncode)
    tail = [l for l in text.splitlines() if l.strip()]
    for l in tail[-9:]:
        print('   ', l.strip()[:110])
    marker = os.path.join(dst, 'Tools', '.icons-enabled')
    print('    marker:', os.path.exists(marker))
    log = os.path.join(dst, 'install.log')
    print('    log   :', open(log, 'rb').read().decode('gbk', 'replace').strip() if os.path.exists(log) else '(none)')


cases = [
    ('A. option1 (default icons)', dict(force_option=1, regasm_rc=0, option1=True, tag='a')),
    ('B. option2, RegAsm OK', dict(force_option=2, regasm_rc=0, tag='b')),
    ('C. option2, RegAsm FAIL', dict(force_option=2, regasm_rc=1, tag='c')),
    ('D. option2, no .NET 4.8', dict(force_option=2, regasm_rc=0, netfx_ok=False, tag='d')),
]
for label, kw in cases:
    run(prepare(**kw), label)
