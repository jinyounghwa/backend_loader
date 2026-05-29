import Foundation
import CloudKit

class CloudKitManager: NSObject, ObservableObject {
    @Published var isLoggedIn = false
    @Published var lastSyncDate: Date?
    @Published var syncError: Error?

    private let container = CKContainer.default()
    private var lastSyncTimestamp: TimeInterval = 0

    override init() {
        super.init()
        checkAccountStatus()
    }

    func checkAccountStatus() {
        container.accountStatus { status, error in
            DispatchQueue.main.async {
                self.isLoggedIn = (status == .available)
                if let error = error {
                    self.syncError = error
                }
            }
        }
    }

    func syncAlertsWithCloud(alerts: [Alert]) {
        guard isLoggedIn else { return }

        let db = container.privateCloudDatabase
        var records: [CKRecord] = []

        for alert in alerts {
            let record = CKRecord(recordType: "Alert")
            record["id"] = alert.id
            record["severity"] = alert.severity.rawValue
            record["title"] = alert.title
            record["message"] = alert.message
            record["timestamp"] = alert.timestamp
            record["account"] = alert.account
            records.append(record)
        }

        let operation = CKModifyRecordsOperation(recordsToSave: records)
        operation.completionBlock = {
            DispatchQueue.main.async {
                self.lastSyncDate = Date()
            }
        }
        db.add(operation)
    }

    func fetchAlertsFromCloud(completion: @escaping ([Alert]) -> Void) {
        guard isLoggedIn else { completion([]); return }

        let db = container.privateCloudDatabase
        let query = CKQuery(recordType: "Alert", predicate: NSPredicate(value: true))
        query.sortDescriptors = [NSSortDescriptor(key: "timestamp", ascending: false)]

        db.perform(query, inZoneWith: nil) { records, error in
            DispatchQueue.main.async {
                guard let records = records, error == nil else {
                    self.syncError = error
                    completion([])
                    return
                }

                let alerts = records.compactMap { record -> Alert? in
                    guard
                        let id = record["id"] as? String,
                        let severityStr = record["severity"] as? String,
                        let severity = Alert.Severity(rawValue: severityStr),
                        let title = record["title"] as? String,
                        let message = record["message"] as? String,
                        let timestamp = record["timestamp"] as? Date,
                        let account = record["account"] as? String
                    else {
                        return nil
                    }

                    return Alert(
                        id: id,
                        severity: severity,
                        title: title,
                        message: message,
                        timestamp: timestamp,
                        account: account,
                        isRead: false
                    )
                }

                self.lastSyncDate = Date()
                completion(alerts)
            }
        }
    }
}
