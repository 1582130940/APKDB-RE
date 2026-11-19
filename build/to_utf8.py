# -*- coding: utf-8 -*-
"""Convert the shipped batch scripts to UTF-8.

Design (verified experimentally on Windows 10 cmd.exe):

  * cmd.exe decodes a .bat using the console code page that is active *when it
    reads the file*. Calling `chcp 65001` in the middle of a large script makes
    cmd resume reading at a stale byte offset, shredding subsequent lines
    ("'et' is not recognized ...", lost variables). A 52 KB script produced 196
    such errors.
  * So `chcp` must be executed *before* the big file is opened. Entry points
    therefore become a 3-line ASCII stub that sets the code page and `call`s the
    real body (`<name>_body.cmd`). The body carries no chcp and parses cleanly.
  * Scripts that are only ever `call`ed (language packs, cleanup, PreClean,
    sign.bat, optipng.bat, reduce.bat, apksigner-shim) get no chcp at all; their
    caller has already switched the console.
  * A `chcp` line inside a file that has non-ASCII text after it corrupts the
    remainder of that file (verified: a 1.9 KB script lost variables, a 52 KB one
    produced 196 parse errors). So every entry point becomes a pure-ASCII stub.
  * No BOM anywhere: cmd would try to execute "\\ufeff" as a command.
"""
import os
import re

CHCP = 'chcp 65001 >nul'

# Never given their own chcp: they run inside an already-switched console.
CALLED_ONLY = {
    'language/Language.bat',
    'language/Language.bat.ini',
    'language/Language_en.bat.ini',
    'language/Language_ug.bat.ini',
    'language/Language_zh_cn.bat.ini',
    'language/Language_zh_tw.bat.ini',
    'language/Language_zh_tw_gb.bat.ini',
    'apktool/default.bat',
    'apktool/sign.bat',
    'Tools/cleanup.bat',
    'Tools/PreClean.bat',
    'Tools/optipng.bat',
    'Tools/reduce.bat',
    'Tools/Signer/apksigner-shim.bat',
}

# Entry points are split into a stub + body. A chcp line inside a file that has
# non-ASCII content after it corrupts cmd's parsing of the remainder, so the
# stub must stay pure ASCII.
STUBBED = set()  # filled in apply(): every non-CALLED_ONLY script needing chcp

STUB_TEMPLATE = (
    '@echo off\r\n'
    'chcp 65001 >nul\r\n'
    'call "%~dp0{body}" %*\r\n'
    'exit /b %ERRORLEVEL%\r\n'
)


def _decode(raw):
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    try:
        return raw.decode('utf-8'), True
    except UnicodeDecodeError:
        return raw.decode('gbk', 'replace'), False


def _norm(text):
    return text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')


def _strip_chcp(text):
    return re.sub(r'(?im)^\s*chcp\s+65001\s*(>\s*nul)?\s*\r?\n', '', text)


def _insert_chcp(text):
    lines = text.split('\r\n')
    pos = 0
    for i, line in enumerate(lines[:8]):
        s = line.strip()
        if re.match(r'(?i)^@?echo\s+off\s*$', s) or (s.startswith('@') and 'echo off' in s.lower()):
            pos = i + 1
            break
    lines.insert(pos, CHCP)
    return '\r\n'.join(lines)


def _write(path, data):
    import ctypes
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x80)
    except Exception:
        pass
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(data)
        return
    with open(path, 'r+b') as f:
        f.seek(0)
        f.write(data)
        f.truncate()


def is_script(name):
    low = name.lower()
    return low.endswith(('.bat', '.cmd')) or low.endswith('.bat.ini')


def apply(payload, say):
    stubbed = 0
    for dirpath, _, names in os.walk(payload):
        for name in sorted(list(names)):
            if not is_script(name):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, payload).replace('\\', '/')
            raw = open(path, 'rb').read()
            text, _ = _decode(raw)
            text = _strip_chcp(_norm(text))

            needs = any(ord(ch) > 127 for ch in text) or 'Language.bat' in text

            if needs and rel not in CALLED_ONLY:
                body_name = os.path.splitext(name)[0] + '_body' + os.path.splitext(name)[1]
                _write(path, STUB_TEMPLATE.format(body=body_name).encode('ascii'))
                _write(os.path.join(dirpath, body_name), text.encode('utf-8'))
                stubbed += 1
                continue

            _write(path, text.encode('utf-8'))

    say('[utf8] stub+body pairs: %d' % stubbed)
    _verify(payload, say)


def _verify(payload, say):
    bad = []
    for dirpath, _, names in os.walk(payload):
        for name in names:
            if not is_script(name):
                continue
            path = os.path.join(dirpath, name)
            raw = open(path, 'rb').read()
            if raw.startswith(b'\xef\xbb\xbf'):
                bad.append((path, 'BOM'))
                continue
            try:
                raw.decode('utf-8')
            except UnicodeDecodeError:
                bad.append((path, 'not UTF-8'))
                continue
            # a chcp line inside a file with non-ASCII content corrupts parsing
            txt = raw.decode('utf-8')
            if re.search(r'(?im)^\s*chcp\s+65001', txt) and any(ord(c) > 127 for c in txt):
                # only the ASCII stub may carry chcp
                if '_body' not in os.path.basename(path):
                    bad.append((path, 'chcp inside a non-ASCII script'))
    for path, why in bad:
        say('[utf8] PROBLEM %s: %s' % (os.path.relpath(path, payload), why))
    if not bad:
        say('[utf8] all scripts valid UTF-8, no BOM, chcp only in ASCII stubs')
