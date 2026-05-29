import Foundation

class WebSocketManager: NSObject, URLSessionWebSocketDelegate, ObservableObject {
    @Published var isConnected = false
    @Published var lastAlert: Alert?
    @Published var connectionError: Error?

    private var webSocket: URLSessionWebSocket?
    private let urlSession = URLSession(configuration: .default)
    private let webSocketURL = URL(string: "wss://guardian.example.com/ws")!

    func connect(token: String) {
        var request = URLRequest(url: webSocketURL)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        webSocket = urlSession.webSocketTask(with: request)
        webSocket?.resume()

        DispatchQueue.main.async {
            self.isConnected = true
        }

        receiveMessage()
    }

    func disconnect() {
        webSocket?.cancel(with: .goingAway, reason: nil)
        DispatchQueue.main.async {
            self.isConnected = false
        }
    }

    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                self?.handleMessage(message)
                self?.receiveMessage()
            case .failure(let error):
                DispatchQueue.main.async {
                    self?.connectionError = error
                    self?.isConnected = false
                }
            }
        }
    }

    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .data(let data):
            if let alert = try? JSONDecoder().decode(Alert.self, from: data) {
                DispatchQueue.main.async {
                    self.lastAlert = alert
                }
            }
        case .string(let jsonString):
            if let data = jsonString.data(using: .utf8),
               let alert = try? JSONDecoder().decode(Alert.self, from: data) {
                DispatchQueue.main.async {
                    self.lastAlert = alert
                }
            }
        @unknown default:
            break
        }
    }

    func urlSessionWebSocketTask(
        _ webSocketTask: URLSessionWebSocketTask,
        didOpenWithProtocol protocol: String?
    ) {
        DispatchQueue.main.async {
            self.isConnected = true
        }
    }

    func urlSessionWebSocketTask(
        _ webSocketTask: URLSessionWebSocketTask,
        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        DispatchQueue.main.async {
            self.isConnected = false
        }
    }
}
