#!/usr/bin/env python3
"""把 Folia 前端的汽水 provider 从 Electron IPC 改成直连模块。
   兼容不同的 chunk 命名（providerRegistry-*.js / registry-*.js 等）"""
import glob, sys, os, re

def find_target(dist):
    assets = os.path.join(dist, 'assets')
    patterns = [
        'providerRegistry-*.js',
        'registry-*.js',
        'provider*.js',
    ]
    for pat in patterns:
        hits = glob.glob(os.path.join(assets, pat))
        for h in hits:
            try:
                s = open(h, encoding='utf-8').read()
            except Exception:
                continue
            # 必须同时包含汽水标识和 Electron 调用
            if 'qishui' in s.lower() and ('electron' in s or 'Qishui' in s):
                return h, s
    return None, None

def main(dist):
    p, s = find_target(dist)
    if not p:
        print('ERROR: 找不到包含 qishui 的 chunk')
        # 列出候选帮助排查
        for f in sorted(glob.glob(os.path.join(dist, 'assets', '*.js'))):
            try:
                t = open(f, encoding='utf-8').read()
                if 'qishui' in t.lower():
                    print('  候选:', os.path.basename(f), len(t), 'bytes')
            except Exception:
                pass
        sys.exit(1)

    print('target:', os.path.basename(p), len(s), 'bytes')
    changed = 0

    # 1) 可用性判定
    patterns_qx = [
        "typeof window.electron?.qishuiRequest==`function`",
        "typeof window.electron?.qishuiRequest==='function'",
        'typeof window.electron?.qishuiRequest==="function"',
        "typeof window.electron?.qishuiRequest == `function`",
    ]
    for old in patterns_qx:
        if old in s:
            s = s.replace(old, "typeof window.__qishuiDirect==`function`", 1)
            changed += 1
            print('  patched qx check')
            break

    # 2) 调用点
    for old in ["await window.electron.qishuiRequest(e,t)",
                "await window.electron.qishuiRequest("]:
        if old in s:
            if old.endswith("(e,t)"):
                s = s.replace(old, "await window.__qishuiDirect(e,t)", 1)
            else:
                s = s.replace(old, "await window.__qishuiDirect(", 1)
            changed += 1
            print('  patched call site')
            break

    open(p, 'w', encoding='utf-8').write(s)
    print(f'patched {os.path.basename(p)}: {changed} 处')

    s2 = open(p, encoding='utf-8').read()
    print('  判定已改:', '__qishuiDirect' in s2)
    print('  仍引用 electron.qishuiRequest:', 'window.electron.qishuiRequest' in s2)
    if changed < 2:
        print('WARN: 补丁未完全命中，需要人工检查')
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dist')
