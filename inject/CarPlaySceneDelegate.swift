import CarPlay
import AVKit
import UIKit

/// CarPlay 歌词视频流最小实验：
/// 在 CarPlay 场景里创建一个 UIViewController，用 AVPlayerLayer 播放一段 H.264 视频，
/// 验证「第三方 AVPlayerLayer 能否渲染到 CarPlay 屏幕」（APTV 同类的技术路线）。
/// 若实验通过，后续把 Folia 的 WebGL 歌词动画帧实时编码成 H.264 流喂给该播放器。
class CarPlaySceneDelegate: NSObject, CPTemplateApplicationSceneDelegate {

    private var window: UIWindow?
    private var player: AVPlayer?
    private var playerLayer: AVPlayerLayer?

    /// 换成你自己的测试视频 URL（H.264）。可以用本地打包的视频更稳定。
    private let testVideoURL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    func templateApplicationScene(
        _ scene: CPTemplateApplicationScene,
        didConnect interfaceController: CPInterfaceController,
        to window: UIWindow?
    ) {
        self.window = window

        let rootVC = UIViewController()
        rootVC.view.backgroundColor = .black

        let player = AVPlayer(url: URL(string: testVideoURL)!)
        let layer = AVPlayerLayer(player: player)
        layer.videoGravity = .resizeAspect
        layer.frame = window?.bounds ?? UIScreen.main.bounds
        rootVC.view.layer.addSublayer(layer)

        player.play()
        self.player = player
        self.playerLayer = layer

        window?.rootViewController = rootVC
        window?.makeKeyAndVisible()
    }

    func templateApplicationScene(
        _ scene: CPTemplateApplicationScene,
        didDisconnectInterfaceController interfaceController: CPInterfaceController,
        from window: UIWindow?
    ) {
        player?.pause()
        playerLayer?.removeFromSuperlayer()
        player = nil
        playerLayer = nil
    }
}