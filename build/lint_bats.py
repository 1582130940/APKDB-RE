# -*- coding: utf-8 -*-
"""Static checks for the APKDB batch scripts."""
import io, os, re, sys
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = 'verify'
files = []
for dirpath, _, names in os.walk(ROOT):
    for n in names:
        if n.lower().endswith(('.bat', '.cmd')):
            files.append(os.path.join(dirpath, n))
files.sort()

def load(p):
    raw = open(p, 'rb').read()
    enc = None
    for e in ('gbk', 'utf-8-sig', 'utf-8'):
        try:
            return raw.decode(e), e, raw
        except UnicodeDecodeError:
            continue
    return raw.decode('latin1'), 'latin1', raw

print('%-52s %-8s %-6s %-5s %s' % ('script', 'enc', 'CRLF', 'lines', 'notes'))
print('-' * 118)

issues = defaultdict(list)
for p in files:
    rel = os.path.relpath(p, ROOT).replace('\\', '/')
    text, enc, raw = load(p)
    lines = text.splitlines()
    crlf = raw.count(b'\r\n')
    lf_only = raw.count(b'\n') - crlf
    if lf_only > 0:
        issues[rel].append('%d LF-only lines' % lf_only)
    if enc == 'latin1':
        issues[rel].append('undecodable (mixed encoding?)')
    if raw[:3] == b'\xef\xbb\xbf':
        issues[rel].append('UTF-8 BOM in a .bat/.cmd')

    # labels / gotos
    labels = [m.group(1).lower() for m in re.finditer(r'(?mi)^\s*:([A-Za-z0-9_]+)\s*$', text)]
    dup = [k for k, v in Counter(labels).items() if v > 1]
    if dup:
        issues[rel].append('duplicate labels: %s' % ','.join(dup[:6]))
    targets = set(m.group(1).lower() for m in re.finditer(r'(?i)\bgoto\s+:?([A-Za-z0-9_]+)', text))
    missing = sorted(t for t in targets if t not in labels and t not in ('eof',))
    if missing:
        issues[rel].append('goto to undefined label: %s' % ','.join(missing[:8]))

    # call to script that uses bare `exit`
    if re.search(r'(?mi)^\s*(?!::|rem\b).*\bexit\s*$', text) and 'setlocal' in text.lower():
        pass

    # delayed expansion without enabling it
    if '!' in text and re.search(r'![A-Za-z_][A-Za-z0-9_]*!', text):
        if not re.search(r'(?i)setlocal[^\r\n]*enabledelayedexpansion', text):
            issues[rel].append('uses !var! without EnableDelayedExpansion')

    # classic broken arg test
    if re.search(r'(?i)if\s+%1\s*==\s*\(\)', text):
        issues[rel].append('broken "if %1 == ()" idiom')

    # unquoted %1 in path position
    for m in re.finditer(r'(?mi)^\s*(?!::|rem\b)[^\r\n]*?(?<![\w"\\])(%1|%~1)(?![\w"])', text):
        seg = m.group(0).strip()
        if re.search(r'(?i)\b(if|for|set)\b', seg):
            issues[rel].append('possibly unquoted %1 -> ' + seg[:70])
            break

    # bare `exit` at top level (kills caller when called via call)
    bare_exit = [i + 1 for i, l in enumerate(lines)
                 if re.match(r'(?i)^\s*exit\s*$', l) and not re.match(r'(?i)^\s*(::|rem)', l)]
    if bare_exit:
        issues[rel].append('bare exit at line(s) ' + ','.join(map(str, bare_exit[:5])))

    # chcp / codepage mismatch hints
    has_cjk = any('\u4e00' <= ch <= '\u9fff' for ch in text)
    if has_cjk and enc == 'utf-8' and 'chcp' not in text.lower():
        issues[rel].append('UTF-8 CJK text without chcp 65001')

    # unbalanced parentheses (crude, strip quoted text and comments)
    stripped = re.sub(r'"[^"\r\n]*"', '""', text)
    stripped = re.sub(r'(?m)^\s*(::|rem\b).*$', '', stripped)
    if stripped.count('(') != stripped.count(')'):
        issues[rel].append('paren imbalance (%d vs %d)' % (stripped.count('('), stripped.count(')')))

    print('%-52s %-8s %-6s %-5d %s' % (rel, enc, 'yes' if lf_only == 0 else 'PART', len(lines),
                                       '; '.join(issues[rel])[:60]))

print()
print('=' * 118)
print('DETAIL')
for rel in sorted(issues):
    print('\n## %s' % rel)
    for it in issues[rel]:
        print('   - %s' % it)

print()
print('=' * 118)
print('CALL GRAPH / external dependency check')
for p in files:
    rel = os.path.relpath(p, ROOT).replace('\\', '/')
    text, enc, raw = load(p)
    refs = sorted(set(m.group(1) for m in re.finditer(r'(?i)([A-Za-z0-9_\-.]+\.(?:exe|jar|bat|cmd))', text)))
    if refs and rel in ('APKDB_X/apkdb.cmd', 'APKDB_X/apkdb_d.cmd', 'APKDB_X/odex.cmd',
                        'APKDB_X/optipng.cmd', 'APKDB_X/Tools/FLV2MP4.bat',
                        'APKDB_X/Tools/Hosts/Hostsup.bat', 'APKDB_X/Tools/reduce.bat'):
        print('\n%s:' % rel)
        for r in refs:
            hits = []
            low = r.lower()
            for dirpath, _, names in os.walk(ROOT):
                for n in names:
                    if n.lower() == low:
                        hits.append(os.path.relpath(os.path.join(dirpath, n), ROOT))
            status = 'OK' if hits else 'MISSING IN PACKAGE'
            print('   %-28s %s %s' % (r, status, hits[0] if hits else ''))
