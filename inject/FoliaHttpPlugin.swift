import Foundation
import Capacitor

/// 自定义 HTTP 插件：用 URLSession 发请求，把包括 Set-Cookie 在内的完整响应头回传给 JS。
/// Capacitor 自带的 CapacitorHttp 会过滤 Set-Cookie，导致网易云登录态丢失。
@objc(FoliaHttpPlugin)
public class FoliaHttpPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "FoliaHttpPlugin"
    public let jsName = "FoliaHttp"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "request", returnType: CAPPluginReturnPromise)
    ]

    @objc func request(_ call: CAPPluginCall) {
        guard let urlString = call.getString("url"), let url = URL(string: urlString) else {
            call.reject("bad url")
            return
        }
        let method = (call.getString("method") ?? "GET").uppercased()
        let headers = call.getObject("headers") as? [String: String] ?? [:]
        let body = call.getString("data")

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.cachePolicy = .reloadIgnoringLocalCacheData
        req.httpShouldHandleCookies = false          // 关键：不让系统自动吞 cookie
        for (k, v) in headers {
            req.setValue(v, forHTTPHeaderField: k)
        }
        if let body, method != "GET", method != "HEAD" {
            req.httpBody = body.data(using: .utf8)
        }

        let config = URLSessionConfiguration.ephemeral
        config.httpCookieStorage = nil
        config.httpShouldSetCookies = false
        config.httpCookieAcceptPolicy = .never
        config.timeoutIntervalForRequest = 30
        let session = URLSession(configuration: config)

        session.dataTask(with: req) { data, response, error in
            if let error {
                call.reject("request failed: \(error.localizedDescription)")
                return
            }
            guard let http = response as? HTTPURLResponse else {
                call.reject("no response")
                return
            }
            var outHeaders: [String: String] = [:]
            for (k, v) in http.allHeaderFields {
                outHeaders[String(describing: k)] = String(describing: v)
            }
            // 额外把 Set-Cookie 单独收集（allHeaderFields 里可能被合并）
            let cookies = HTTPCookie.cookies(withResponseHeaderFields: outHeaders, for: url)
                .map { "\($0.name)=\($0.value)" }
            if !cookies.isEmpty {
                outHeaders["x-set-cookie"] = cookies.joined(separator: "; ")
            }
            let text = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
            call.resolve([
                "status": http.statusCode,
                "headers": outHeaders,
                "body": text
            ])
        }.resume()
    }
}
