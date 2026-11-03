import SwiftUI
import UserNotifications

@main
struct LatteCoachApp: App {
    @StateObject private var practice = PracticeSession()
    @StateObject private var store: CupStore
    @StateObject private var sender: CupSenderBox
    private let notificationDelegate = NotificationDelegate()

    init() {
        let store = CupStore()
        _store = StateObject(wrappedValue: store)
        _sender = StateObject(wrappedValue: CupSenderBox(store: store))
        UNUserNotificationCenter.current().delegate = notificationDelegate
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(practice)
                .environmentObject(store)
                .environmentObject(sender)
        }
    }
}
