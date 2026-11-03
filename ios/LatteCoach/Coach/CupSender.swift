import Foundation

/// 杯をサーバーへ送り、診断が出るまで取りに行く。プッシュ通知は後で足す（plan.md の削る順4）
@MainActor
final class CupSender {
    private let store: CupStore
    private let pollInterval: Duration = .seconds(3)
    private let timeout: Duration = .seconds(600)

    init(store: CupStore) { self.store = store }

    func send(_ id: UUID) async {
        guard let cup = store.cup(id) else { return }
        guard let client = CoachClient.fromBundle() else {
            store.update(id) { $0.status = .ready; $0.errorMessage = "サーバー未設定（COACH_SERVER_URL）。端末に保存しました" }
            return
        }
        store.update(id) { $0.status = .sending; $0.errorMessage = nil }
        do {
            let photo = cup.photoFilename.flatMap(store.photoData)
            let serverId = try await client.submit(cup: cup, photo: photo)
            store.update(id) { $0.serverId = serverId; $0.status = .diagnosing }
            try await poll(client: client, id: id, serverId: serverId)
        } catch {
            store.update(id) { $0.status = .failed; $0.errorMessage = error.localizedDescription }
        }
    }

    private func poll(client: CoachClient, id: UUID, serverId: String) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now + timeout
        while clock.now < deadline {
            try await Task.sleep(for: pollInterval)
            let s = try await client.status(of: serverId)
            switch s.status {
            case "done":
                guard let d = s.diagnosis else { continue }
                store.update(id) { $0.diagnosis = d; $0.status = .done }
                Notifier.diagnosed(d)
                return
            case "failed":
                store.update(id) { $0.status = .failed; $0.errorMessage = s.error ?? "診断に失敗しました" }
                return
            default:
                continue
            }
        }
        store.update(id) { $0.status = .failed; $0.errorMessage = "診断がタイムアウトしました" }
    }
}
