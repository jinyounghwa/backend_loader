import Foundation

struct Cost: Codable, Identifiable {
    let id: String
    let date: Date
    let amount: Double
    let service: String
    let account: String

    enum CodingKeys: String, CodingKey {
        case id
        case date
        case amount
        case service
        case account
    }
}

struct CostSummary: Codable {
    let dailyCost: Double
    let monthlyCost: Double
    let trend: Double // percentage change
    let byService: [String: Double]
    let byAccount: [String: Double]
}

struct CostHistory: Codable {
    let dates: [String]
    let amounts: [Double]
}
