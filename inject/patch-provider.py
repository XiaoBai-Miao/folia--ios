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
        # 可能已经被补过（本地重跑）或上游改了实现
        already = []
        for f in glob.glob(os.path.join(dist, 'assets', '*.js')):
            try:
                if '__qishuiDirect' in open(f, encoding='utf-8').read():
                    already.append(os.path.basename(f))
            except Exception:
                pass
        if already:
            print('汽水已补过，跳过:', already[:3])
            hits = []
        else:
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

    # 3) 网易云 API base：指向外部服务（WebView 里没有 Node，必须外部提供）
    NET_BASE = os.environ.get('FOLIA_NETEASE_API', 'http://192.168.0.65:3001')
    net_changed = 0
    for p2 in glob.glob(os.path.join(dist, 'assets', '*.js')):
        try:
            t = open(p2, encoding='utf-8').read()
        except Exception:
            continue
        if 'VITE_NETEASE_API_BASE' not in t:
            continue
        old_fn = ("Dt=()=>{let e={BASE_URL:`/`,DEV:!1,MODE:`production`,PROD:!0,SSR:!1};"
                  "return e&&typeof e.VITE_NETEASE_API_BASE==`string`&&e.VITE_NETEASE_API_BASE?"
                  "e.VITE_NETEASE_API_BASE:typeof process<`u`&&typeof{}.VITE_NETEASE_API_BASE==`string`&&"
                  "{}.VITE_NETEASE_API_BASE?{}.VITE_NETEASE_API_BASE:null}")
        if old_fn in t:
            t = t.replace(old_fn, "Dt=()=>`%s`" % NET_BASE, 1)
            open(p2, 'w', encoding='utf-8').write(t)
            net_changed += 1
            print('  patched netease base ->', NET_BASE, 'in', os.path.basename(p2))
        else:
            # 兜底：只替换最后那个 null 返回
            import re as _re
            pat = _re.compile(r"VITE_NETEASE_API_BASE==`string`&&\{\}\.VITE_NETEASE_API_BASE\?"
                              r"\{\}\.VITE_NETEASE_API_BASE:null")
            if pat.search(t):
                t = pat.sub("VITE_NETEASE_API_BASE==`string`&&{}.VITE_NETEASE_API_BASE?"
                            "{}.VITE_NETEASE_API_BASE:`%s`" % NET_BASE, t, count=1)
                open(p2, 'w', encoding='utf-8').write(t)
                net_changed += 1
                print('  patched netease base (fallback) ->', NET_BASE)
    print('  网易云 base 改动文件数:', net_changed)

    # 自检
    remain = 0
    for f in glob.glob(os.path.join(dist, 'assets', '*.js')):
        try:
            if 'window.electron.qishuiRequest' in open(f, encoding='utf-8').read():
                remain += 1
        except Exception:
            pass
    print('  仍含 electron.qishuiRequest 的文件数:', remain)
    if total_changed < 2 and net_changed == 0:
        print('ERROR: 补丁完全没命中')
        sys.exit(1)
    if total_changed < 2:
        print('NOTE: 汽水补丁 0 处（可能已补过），网易云 base 已注入')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dist')
