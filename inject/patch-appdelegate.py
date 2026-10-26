#!/usr/bin/env python3
"""给 Capacitor 的 AppDelegate 加后台音频支持（不依赖 Capacitor 内部 API）"""
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
        s = s.replace('import UIKit', 'import UIKit\nimport AVFoundation\nimport WebKit', 1)
    elif 'import WebKit' not in s:
        s = s.replace('import AVFoundation', 'import AVFoundation\nimport WebKit', 1)

    # didFinishLaunching 注入
    marker = 'func application(_ application: UIApplication, didFinishLaunchingWithOptions'
    idx = s.find(marker)
    if idx < 0:
        print('ERROR: didFinishLaunchingWithOptions not found')
        sys.exit(1)
    brace = s.find('{', idx)

    inject = """
        // ===== CAPBackgroundAudio: 后台播放配置 =====
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try session.setActive(true)
            print("[Folia] AVAudioSession = .playback, active")
        } catch {
            print("[Folia] AVAudioSession failed: \\(error)")
        }

        // 等 WebView 建好后配置媒体播放策略
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if let window = self.window, let root = window.rootViewController {
                AppDelegate.configureWebViews(in: root.view)
            }
        }
"""
    s = s[:brace+1] + inject + s[brace+1:]

    # 类末尾加辅助方法
    last = s.rfind('}')
    helpers = """
    // ===== CAPBackgroundAudio =====
    // 用 UIView 递归找 WKWebView，不依赖 Capacitor 内部类型
    static func configureWebViews(in view: UIView) {
        if let webView = view as? WKWebView {
            webView.configuration.mediaTypesRequiringUserActionForPlayback = []
            webView.configuration.allowsInlineMediaPlayback = true
            webView.configuration.allowsAirPlayForMediaPlayback = true
            webView.configuration.preferences.javaScriptCanOpenWindowsAutomatically = true
            print("[Folia] WKWebView configured for background audio")
        }
        for sub in view.subviews {
            configureWebViews(in: sub)
        }
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try session.setActive(true)
            print("[Folia] background: audio session re-activated")
        } catch {
            print("[Folia] background re-activate failed: \\(error)")
        }
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        do { try AVAudioSession.sharedInstance().setActive(true) } catch {}
    }
"""
    s = s[:last] + helpers + s[last:]
    open(p, 'w', encoding='utf-8').write(s)

    t = open(p, encoding='utf-8').read()
    checks = {
        'AVAudioSession': 'AVAudioSession' in t,
        'WKWebView import': 'import WebKit' in t,
        'configureWebViews': 'configureWebViews' in t,
        'didEnterBackground': 'applicationDidEnterBackground' in t,
    }
    print('patched:', checks)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ios/App/App')
