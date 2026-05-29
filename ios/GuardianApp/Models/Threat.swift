import Foundation

struct Threat: Codable, Identifiable {
    let id: String
    let severity: Int // 0-100
    let title: String
    let description: String
    let timestamp: Date
    let account: String
    let service: String
    let evidence: [String]

    enum CodingKeys: String, CodingKey {
        case id
        case severity
        case title
        case description
        case timestamp
        case account
        case service
        case evidence
    }
}

struct ThreatTimeline: Codable {
    let threats: [Threat]
    let total: Int
}

struct ThreatStats: Codable {
    let criticalCount: Int
    let highCount: Int
    let mediumCount: Int
    let lowCount: Int
}
