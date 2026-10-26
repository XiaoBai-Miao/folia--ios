#!/usr/bin/env python3
"""给 Capacitor 的 AppDelegate 加后台音频支持（最小改动，避免重复声明）"""
import sys, os

def main(appdir):
    p = os.path.join(appdir, 'AppDelegate.swift')
    if not os.path.exists(p):
        print('ERROR: AppDelegate.swift not found at', p)
        sys.exit(1)
    s = open(p, encoding='utf-8').read()

    if 'CAPBackgroundAudio' in s:
        print('already patched')
        return

    # imports
    if 'import AVFoundation' not in s:
        s = s.replace('import UIKit', 'import UIKit\nimport AVFoundation', 1)
    if 'import WebKit' not in s:
        s = s.replace('import AVFoundation', 'import AVFoundation\nimport WebKit', 1)

    # 1) didFinishLaunching 里配置 AVAudioSession
    marker = 'func application(_ application: UIApplication, didFinishLaunchingWithOptions'
    idx = s.find(marker)
    if idx < 0:
        print('ERROR: didFinishLaunchingWithOptions not found')
        sys.exit(1)
    brace = s.find('{', idx)

    inject = """
        // ===== CAPBackgroundAudio =====
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try session.setActive(true)
            print("[Folia] AVAudioSession = .playback, active")
        } catch {
            print("[Folia] AVAudioSession failed: \\(error)")
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if let window = self.window, let root = window.rootViewController {
                AppDelegate.configureWebViews(in: root.view)
            }
        }
"""
    s = s[:brace+1] + inject + s[brace+1:]

    # 2) 类末尾追加辅助方法（只加 configureWebViews，不碰生命周期方法）
    last = s.rfind('}')
    helper = """
    // ===== CAPBackgroundAudio =====
    static func configureWebViews(in view: UIView) {
        if let webView = view as? WKWebView {
            webView.configuration.mediaTypesRequiringUserActionForPlayback = []
            webView.configuration.allowsInlineMediaPlayback = true
            webView.configuration.allowsAirPlayForMediaPlayback = true
            print("[Folia] WKWebView configured for background audio")
        }
        for sub in view.subviews {
            configureWebViews(in: sub)
        }
    }
"""
    s = s[:last] + helper + s[last:]
    open(p, 'w', encoding='utf-8').write(s)

    t = open(p, encoding='utf-8').read()
    print('patched:', {
        'AVAudioSession': 'AVAudioSession' in t,
        'WebKit': 'import WebKit' in t,
        'configureWebViews': 'configureWebViews' in t,
        'no_dup_willEnterForeground': t.count('func applicationWillEnterForeground') <= 1,
    })

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ios/App/App')
