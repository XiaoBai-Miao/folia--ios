#!/usr/bin/env python3
"""给 Capacitor 的 AppDelegate 加后台音频支持"""
import sys, os, re

def main(appdir):
    p = os.path.join(appdir, 'AppDelegate.swift')
    if not os.path.exists(p):
        print('ERROR: AppDelegate.swift not found at', p)
        sys.exit(1)
    s = open(p, encoding='utf-8').read()

    if 'AVAudioSession' in s:
        print('already patched')
        return

    # 1) import AVFoundation
    if 'import AVFoundation' not in s:
        s = s.replace('import UIKit', 'import UIKit\nimport AVFoundation', 1)

    # 2) 在 didFinishLaunchingWithOptions 里配置音频会话
    marker = 'func application(_ application: UIApplication, didFinishLaunchingWithOptions'
    idx = s.find(marker)
    if idx < 0:
        print('ERROR: didFinishLaunchingWithOptions not found')
        sys.exit(1)
    brace = s.find('{', idx)
    inject = """
        // 后台音频：允许锁屏/切后台继续播放
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try session.setActive(true)
        } catch {
            print("[Folia] AVAudioSession setup failed: \\(error)")
        }
"""
    s = s[:brace+1] + inject + s[brace+1:]
    open(p, 'w', encoding='utf-8').write(s)
    print('patched AppDelegate.swift with AVAudioSession')
    print('AVAudioSession in file:', 'AVAudioSession' in open(p, encoding='utf-8').read())

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ios/App/App')
