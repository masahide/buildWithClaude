import Foundation

/// 薄いサーバーとのやりとり。サーバー側（POST /cups, GET /cups/{id}）は未実装で、この形に合わせて作る。
///
/// POST /cups  multipart/form-data
///   meta  : application/json  {"started_at", "ended_at", "features", "self_rating"}
///   photo : image/jpeg        ピッチャーの残り
///   → 202 {"cup_id": "..."}
/// GET /cups/{cup_id}
///   → 200 {"status": "diagnosing" | "done" | "failed", "diagnosis": {...}?, "error": "..."?}
struct CoachClient {
    let baseURL: URL

    /// Info.plist の CoachServerURL（ビルド設定 COACH_SERVER_URL）。空なら送信しない
    static func fromBundle() -> CoachClient? {
        guard let s = Bundle.main.object(forInfoDictionaryKey: "CoachServerURL") as? String,
              !s.isEmpty, let url = URL(string: s) else { return nil }
        return CoachClient(baseURL: url)
    }

    struct Meta: Encodable {
        let startedAt: Date
        let endedAt: Date
        let features: CupFeatures?
        let selfRating: String?
        let envelope: [[Float]]?
        enum CodingKeys: String, CodingKey {
            case startedAt = "started_at", endedAt = "ended_at", features, selfRating = "self_rating", envelope
        }
    }

    struct CupStatus: Decodable {
        let status: String
        let diagnosis: Diagnosis?
        let error: String?
    }

    func submit(cup: Cup, photo: Data?) async throws -> String {
        let boundary = "lattecoach-\(UUID().uuidString)"
        var body = Data()
        func part(_ name: String, filename: String? = nil, type: String, data: Data) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            let fn = filename.map { "; filename=\"\($0)\"" } ?? ""
            body.append("Content-Disposition: form-data; name=\"\(name)\"\(fn)\r\n".data(using: .utf8)!)
            body.append("Content-Type: \(type)\r\n\r\n".data(using: .utf8)!)
            body.append(data)
            body.append("\r\n".data(using: .utf8)!)
        }
        let meta = Meta(startedAt: cup.startedAt, endedAt: cup.endedAt, features: cup.features,
                        selfRating: cup.selfRating?.rawValue, envelope: cup.envelope)
        part("meta", type: "application/json", data: try JSONEncoder.iso.encode(meta))
        if let photo { part("photo", filename: "pitcher.jpg", type: "image/jpeg", data: photo) }
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        var req = URLRequest(url: baseURL.appendingPathComponent("cups"))
        req.httpMethod = "POST"
        // サーバーが止まっているときに「送信中」で長く待たせない
        req.timeoutInterval = 30
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await URLSession.shared.upload(for: req, from: body)
        try Self.check(response, data)
        struct Created: Decodable { let cup_id: String }
        return try JSONDecoder().decode(Created.self, from: data).cup_id
    }

    func status(of serverId: String) async throws -> CupStatus {
        let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("cups/\(serverId)"))
        try Self.check(response, data)
        return try JSONDecoder().decode(CupStatus.self, from: data)
    }

    private static func check(_ response: URLResponse, _ data: Data) throws {
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let code = (response as? HTTPURLResponse)?.statusCode ?? -1
            throw NSError(domain: "CoachClient", code: code,
                          userInfo: [NSLocalizedDescriptionKey: String(data: data, encoding: .utf8) ?? "HTTP \(code)"])
        }
    }
}
