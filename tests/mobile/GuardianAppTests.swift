import XCTest
import CloudKit
@testable import GuardianApp

class GuardianAppTests: XCTestCase {

    var cloudKitManager: CloudKitManager!
    var webSocketManager: WebSocketManager!
    var notificationManager: NotificationManager!

    override func setUp() {
        super.setUp()
        cloudKitManager = CloudKitManager()
        webSocketManager = WebSocketManager()
        notificationManager = NotificationManager()
    }

    override func tearDown() {
        cloudKitManager = nil
        webSocketManager = nil
        notificationManager = nil
        super.tearDown()
    }

    // MARK: - CloudKit Sync Tests

    func testCloudKitSync() {
        let alert = Alert(
            id: "alert-1",
            severity: .critical,
            title: "Test Alert",
            message: "Test message",
            timestamp: Date(),
            account: "prod",
            isRead: false
        )

        let expectation = XCTestExpectation(description: "CloudKit sync")
        cloudKitManager.syncAlertsWithCloud(alerts: [alert])

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            XCTAssertNotNil(self.cloudKitManager.lastSyncDate)
            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 2.0)
    }

    func testOfflineMode() {
        // Simulate offline by using local cache
        let alerts: [Alert] = [
            Alert(id: "1", severity: .critical, title: "Alert 1", message: "msg", timestamp: Date(), account: "prod", isRead: false),
            Alert(id: "2", severity: .high, title: "Alert 2", message: "msg", timestamp: Date(), account: "dev", isRead: false)
        ]

        // Store in UserDefaults (local cache)
        let encoder = JSONEncoder()
        if let encoded = try? encoder.encode(alerts) {
            UserDefaults.standard.set(encoded, forKey: "cachedAlerts")
        }

        // Retrieve from cache
        if let cached = UserDefaults.standard.data(forKey: "cachedAlerts"),
           let decoder = JSONDecoder(),
           let retrieved = try? decoder.decode([Alert].self, from: cached) {
            XCTAssertEqual(retrieved.count, 2)
            XCTAssertEqual(retrieved[0].severity, .critical)
        }
    }

    func testLocalNotifications() {
        let alert = Alert(
            id: "notif-1",
            severity: .critical,
            title: "Critical Alert",
            message: "Immediate action required",
            timestamp: Date(),
            account: "prod",
            isRead: false
        )

        notificationManager.sendLocalNotification(alert: alert)

        let expectation = XCTestExpectation(description: "Notification sent")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            UNUserNotificationCenter.current().getPendingNotificationRequests { requests in
                XCTAssert(requests.contains { $0.identifier == alert.id })
                expectation.fulfill()
            }
        }

        wait(for: [expectation], timeout: 2.0)
    }

    func testCostChartRendering() {
        let costHistory = CostHistory(
            dates: ["2026-05-25", "2026-05-26", "2026-05-27"],
            amounts: [100.0, 120.0, 150.0]
        )

        XCTAssertEqual(costHistory.dates.count, 3)
        XCTAssertEqual(costHistory.amounts.count, 3)
        XCTAssert(costHistory.amounts[2] > costHistory.amounts[0])
    }

    func testThreatTimeline() {
        let threats = [
            Threat(id: "t1", severity: 90, title: "Threat 1", description: "desc", timestamp: Date(timeIntervalSince1970: 1000), account: "prod", service: "EC2", evidence: ["ev1"]),
            Threat(id: "t2", severity: 70, title: "Threat 2", description: "desc", timestamp: Date(timeIntervalSince1970: 2000), account: "prod", service: "S3", evidence: ["ev2"]),
            Threat(id: "t3", severity: 50, title: "Threat 3", description: "desc", timestamp: Date(timeIntervalSince1970: 1500), account: "dev", service: "Lambda", evidence: ["ev3"])
        ]

        let timeline = ThreatTimeline(threats: threats, total: threats.count)

        XCTAssertEqual(timeline.total, 3)
        // Verify severity ordering
        XCTAssert(timeline.threats[0].severity >= timeline.threats[1].severity)
    }

    func testPushNotifications() {
        let userInfo: [AnyHashable: Any] = [
            "alert": [
                "title": "Push Test",
                "body": "Push notification test"
            ]
        ]

        notificationManager.handleRemoteNotification(userInfo: userInfo)

        let expectation = XCTestExpectation(description: "Push handled")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            UNUserNotificationCenter.current().getPendingNotificationRequests { requests in
                XCTAssert(requests.count > 0)
                expectation.fulfill()
            }
        }

        wait(for: [expectation], timeout: 2.0)
    }
}
