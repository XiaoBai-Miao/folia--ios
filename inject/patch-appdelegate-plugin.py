#!/usr/bin/env python3
"""在 AppDelegate 里注册自定义 HTTP 插件"""
import sys, os

def main(appdir):
    p = os.path.join(appdir, 'AppDelegate.swift')
    if not os.path.exists(p):
        print('ERROR: AppDelegate.swift not found at', p)
        sys.exit(1)
    s = open(p, encoding='utf-8').read()
    if 'FoliaHttpPlugin' in s:
        print('already registered')
        return

    marker = 'func application(_ application: UIApplication, didFinishLaunchingWithOptions'
    idx = s.find(marker)
    if idx < 0:
        print('ERROR: didFinishLaunchingWithOptions not found')
        sys.exit(1)
    brace = s.find('{', idx)

    inject = '''
        // 注册自定义 HTTP 插件（延迟，等 bridge 建好）
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if let bridge = self.window?.rootViewController as? CAPBridgeViewController {
                bridge.bridge?.registerPluginInstance(FoliaHttpPlugin())
                print("[Folia] FoliaHttpPlugin registered")
            } else {
                print("[Folia] bridge not ready for FoliaHttpPlugin")
            }
        }
'''
    s = s[:brace+1] + inject + s[brace+1:]
    open(p, 'w', encoding='utf-8').write(s)
    t = open(p, encoding='utf-8').read()
    print('patched:', 'FoliaHttpPlugin' in t)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ios/App/App')
