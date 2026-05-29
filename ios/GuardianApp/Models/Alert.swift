import Foundation

struct Alert: Codable, Identifiable {
    let id: String
    let severity: Severity
    let title: String
    let message: String
    let timestamp: Date
    let account: String
    let isRead: Bool

    enum Severity: String, Codable {
        case critical = "CRITICAL"
        case high = "HIGH"
        case medium = "MEDIUM"
        case low = "LOW"
    }
}

struct AlertListResponse: Codable {
    let alerts: [Alert]
    let total: Int
}
