import Foundation
import UserNotifications

class NotificationManager: NSObject, ObservableObject {
    @Published var authorizationStatus: UNAuthorizationStatus = .notDetermined

    override init() {
        super.init()
        checkNotificationAuthorizationStatus()
    }

    func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            DispatchQueue.main.async {
                if granted {
                    DispatchQueue.main.async {
                        UIApplication.shared.registerForRemoteNotifications()
                    }
                }
                self.checkNotificationAuthorizationStatus()
            }
        }
    }

    func checkNotificationAuthorizationStatus() {
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                self.authorizationStatus = settings.authorizationStatus
            }
        }
    }

    func sendLocalNotification(alert: Alert) {
        let content = UNMutableNotificationContent()
        content.title = alert.title
        content.body = alert.message
        content.sound = .default
        content.badge = NSNumber(value: UIApplication.shared.applicationIconBadgeNumber + 1)

        // Set color based on severity
        switch alert.severity {
        case .critical:
            content.userInfo = ["color": "red"]
        case .high:
            content.userInfo = ["color": "orange"]
        case .medium:
            content.userInfo = ["color": "yellow"]
        case .low:
            content.userInfo = ["color": "blue"]
        }

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
        let request = UNNotificationRequest(identifier: alert.id, content: content, trigger: trigger)

        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("Error sending notification: \(error.localizedDescription)")
            }
        }
    }

    func handleRemoteNotification(userInfo: [AnyHashable: Any]) {
        if let alertData = userInfo["alert"] as? [String: Any],
           let title = alertData["title"] as? String,
           let body = alertData["body"] as? String {
            let content = UNMutableNotificationContent()
            content.title = title
            content.body = body
            content.sound = .default

            let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
            let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: trigger)
            UNUserNotificationCenter.current().add(request)
        }
    }
}
