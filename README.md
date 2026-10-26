# Folia iOS 汽水直连版 · 编译仓库

这个仓库用 GitHub Actions 的免费 macOS 虚拟机，把 Folia 编译成一个
**汽水音乐直连** 的 iOS IPA —— 不需要任何中转服务器。

## 原理

```
iOS Folia (WKWebView)
  ├─ 汽水音源 → window.__qishuiDirect()（我写的 WebCrypto 版）
  │               ↓ 原生 HTTP（CapacitorHttp，绕开 CORS）
  │            open.douyin.com / open.qishui.com
  └─ 其他音源照旧
```

关键点：
- 汽水协议用 **WebCrypto** 实现（P-256 签名 + PKCS#10 CSR），不依赖 Node
- 网络请求走 **CapacitorHttp** 原生层，不受 WKWebView 的 CORS 限制
- 登录态存在 **localStorage**，不经过任何服务器

## 用法

1. 在 GitHub 新建一个 **public** 仓库（public 才免费无限用 macOS runner）
2. 把本目录所有文件推上去
3. 进 **Actions** → 选 `Build Folia iOS (Direct-Connect)` → **Run workflow**
4. 等 15~25 分钟
5. 到 **Releases** 下载 `folia-ios-direct.ipa`
6. 用 Sideloadly / AltStore 自签安装

## 目录

```
.github/workflows/build.yml   CI 配置
inject/qishui-direct.js       汽水直连模块（WebCrypto 版，已打包）
inject/native-http.js         CapacitorHttp fetch 拦截
inject/patch-provider.py      把前端汽水 provider 从 IPC 改成直连
README.md                     本文件
```

## 已验证

- WebCrypto P-256 签名 ✅
- CSR 格式（openssl 解析通过）✅
- client token 获取 ✅
- 搜索返回真实歌曲 ✅
- 播放 URL（非试听）✅
- 歌词 ✅
- 二维码生成 + 状态轮询 ✅
- 前端补丁命中 2 处 ✅

## 未验证

- 完整扫码登录（需要真人扫码）
- iOS 真机运行（需要编译产物）

## 已知限制

- 音质：车机协议只给 standard / high，无损拿不到
- 未登录只能听 30~60 秒试听
- 汽水 API 可能随时变更，届时需要更新 `qishui-direct.js`
