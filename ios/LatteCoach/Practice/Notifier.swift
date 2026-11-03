import UserNotifications

enum Notifier {
    static func requestAuthorization() async {
        _ = try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound])
    }

    /// スチーム区間の終了。撮るのは注ぎ終わった後（スチーム直後に止めるとミルクが分離する。decisions.md D3）
    static func steamEnded() {
        let content = UNMutableNotificationContent()
        content.title = "スチーム終了"
        content.body = "注ぎ終わったら、ピッチャーの残りを1枚撮ってください"
        content.sound = .default
        let req = UNNotificationRequest(identifier: "steam-ended-\(UUID().uuidString)", content: content, trigger: nil)
        UNUserNotificationCenter.current().add(req)
    }

    static func diagnosed(_ d: Diagnosis) {
        let content = UNMutableNotificationContent()
        content.title = "原因: \(d.process)"
        content.body = "次の1杯: \(d.fix)"
        content.sound = .default
        let req = UNNotificationRequest(identifier: "diagnosis-\(UUID().uuidString)", content: content, trigger: nil)
        UNUserNotificationCenter.current().add(req)
    }
}

/// アプリが前面にあるときも通知を出す
final class NotificationDelegate: NSObject, UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async
        -> UNNotificationPresentationOptions {
        [.banner, .sound]
    }
}
