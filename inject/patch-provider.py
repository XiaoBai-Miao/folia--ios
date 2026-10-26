#!/usr/bin/env python3
"""把 Folia 前端的汽水 provider 从 Electron IPC 改成直连模块。"""
import glob, sys, os

def main(dist):
    files = glob.glob(os.path.join(dist, 'assets', 'providerRegistry-*.js'))
    if not files:
        print('ERROR: providerRegistry-*.js not found'); sys.exit(1)
    p = files[0]
    s = open(p, encoding='utf-8').read()
    changed = 0

    # 1) 可用性判定：改为检查直连模块
    for old in [
        "typeof window.electron?.qishuiRequest==`function`",
        "typeof window.electron?.qishuiRequest==='function'",
        'typeof window.electron?.qishuiRequest==="function"',
    ]:
        if old in s:
            s = s.replace(old, "typeof window.__qishuiDirect==`function`", 1)
            changed += 1
            break

    # 2) 调用点
    for old in [
        "await window.electron.qishuiRequest(e,t)",
        "await window.electron.qishuiRequest(",
    ]:
        if old in s:
            s = s.replace(old, "await window.__qishuiDirect(e,t)" if old.endswith("(e,t)") else "await window.__qishuiDirect(", 1)
            changed += 1
            break

    open(p, 'w', encoding='utf-8').write(s)
    print(f'patched {os.path.basename(p)}: {changed} 处')
    if changed < 2:
        print('WARN: 补丁未完全命中，需人工检查')
    # 自检
    s2 = open(p, encoding='utf-8').read()
    print('  判定已改:', '__qishuiDirect' in s2)
    print('  仍引用 electron.qishuiRequest:', 'window.electron.qishuiRequest' in s2)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dist')
