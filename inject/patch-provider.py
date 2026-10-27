#!/usr/bin/env python3
"""把 Folia 前端的汽水 provider 从 Electron IPC 改成直连模块。
   策略：遍历所有 chunk，找含 window.electron.qishuiRequest 的那个"""
import glob, sys, os

def find_targets(dist):
    assets = os.path.join(dist, 'assets')
    hits = []
    for f in glob.glob(os.path.join(assets, '*.js')):
        try:
            s = open(f, encoding='utf-8').read()
        except Exception:
            continue
        if 'window.electron.qishuiRequest' in s or 'electron?.qishuiRequest' in s:
            hits.append((f, s))
    return hits

def main(dist):
    hits = find_targets(dist)
    if not hits:
        print('ERROR: 没有 chunk 包含 window.electron.qishuiRequest')
        # 列出含 qishui 的文件帮助排查
        for f in sorted(glob.glob(os.path.join(dist, 'assets', '*.js'))):
            try:
                t = open(f, encoding='utf-8').read()
                if 'qishui' in t.lower():
                    print('  含 qishui:', os.path.basename(f), len(t), 'bytes',
                          '| 有 electron.qishuiRequest:', 'electron.qishuiRequest' in t)
            except Exception:
                pass
        sys.exit(1)

    total_changed = 0
    for p, s in hits:
        print('target:', os.path.basename(p), len(s), 'bytes')
        changed = 0

        # 1) 可用性判定
        for old in [
            "typeof window.electron?.qishuiRequest==`function`",
            "typeof window.electron?.qishuiRequest==='function'",
            'typeof window.electron?.qishuiRequest==="function"',
        ]:
            if old in s:
                s = s.replace(old, "typeof window.__qishuiDirect==`function`", 1)
                changed += 1
                print('  patched qx check')
                break

        # 2) 调用点
        if 'await window.electron.qishuiRequest(e,t)' in s:
            s = s.replace('await window.electron.qishuiRequest(e,t)',
                          'await window.__qishuiDirect(e,t)', 1)
            changed += 1
            print('  patched call site (e,t)')
        elif 'await window.electron.qishuiRequest(' in s:
            s = s.replace('await window.electron.qishuiRequest(',
                          'await window.__qishuiDirect(', 1)
            changed += 1
            print('  patched call site')

        if changed:
            open(p, 'w', encoding='utf-8').write(s)
            print(f'  patched: {changed} 处')
            total_changed += changed

    print(f'总命中文件 {len(hits)} 个，总改动 {total_changed} 处')

    # 自检
    remain = 0
    for f in glob.glob(os.path.join(dist, 'assets', '*.js')):
        try:
            if 'window.electron.qishuiRequest' in open(f, encoding='utf-8').read():
                remain += 1
        except Exception:
            pass
    print('  仍含 electron.qishuiRequest 的文件数:', remain)
    if total_changed < 2:
        print('WARN: 补丁未完全命中')
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dist')
