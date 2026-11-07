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
        let marks: [String: Double]?
        let paramsVersion: Int?
        let audioStartSec: Double?
        let background: Float?
        let practiceId: UUID?
        let segmentSeq: Int?
        enum CodingKeys: String, CodingKey {
            case startedAt = "started_at", endedAt = "ended_at", features, selfRating = "self_rating", envelope, marks
            case paramsVersion = "params_version", audioStartSec = "audio_start_sec", background
            case practiceId = "practice_id", segmentSeq = "segment_seq"
        }
    }

    struct CupStatus: Decodable {
        let status: String
        let diagnosis: Diagnosis?
        let error: String?
    }

    func submit(cup: Cup, photo: Data?, audio: Data? = nil) async throws -> String {
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
                        selfRating: cup.selfRating?.rawValue, envelope: cup.envelope, marks: cup.marks,
                        paramsVersion: cup.paramsVersion, audioStartSec: cup.audioStartSec,
                        background: cup.background, practiceId: cup.practiceId, segmentSeq: cup.segmentSeq)
        part("meta", type: "application/json", data: try JSONEncoder.iso.encode(meta))
        if let photo { part("photo", filename: "pitcher.jpg", type: "image/jpeg", data: photo) }
        if let audio { part("audio", filename: "steam.wav", type: "audio/wav", data: audio) }
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        var req = URLRequest(url: baseURL.appendingPathComponent("cups"))
        req.httpMethod = "POST"
        // サーバーが止まっているときに「送信中」で長く待たせない
        req.timeoutInterval = 300  // 前回の区切りからの音を全部含む（数分で数十 MB）
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await URLSession.shared.upload(for: req, from: body)
        try Self.check(response, data)
        struct Created: Decodable { let cup_id: String }
        return try JSONDecoder().decode(Created.self, from: data).cup_id
    }

    /// コーチの記憶（夜の振り返りが書く）。マークダウンの文字列のまま返す
    struct Notes: Decodable, Equatable {
        var today: String
        var rules: String
        var reading: String
        var tendencies: String
    }

    func notes() async throws -> Notes {
        let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("coach"))
        try Self.check(response, data)
        return try JSONDecoder().decode(Notes.self, from: data)
    }

    /// 本人がコーチに教える。コーチの記憶（この人の音の読み方）に日付つきで残る
    func teach(_ text: String) async throws {
        var req = URLRequest(url: baseURL.appendingPathComponent("teach"))
        req.httpMethod = "POST"
        req.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: "&=+")
        req.httpBody = "text=\(text.addingPercentEncoding(withAllowedCharacters: allowed) ?? "")".data(using: .utf8)
        let (data, response) = try await URLSession.shared.data(for: req)
        try Self.check(response, data)
    }

    /// 杯につかない練習の音（終了時の最後の区間）を送る
    func uploadPracticeAudio(practiceId: UUID, seq: Int, audio: Data) async throws {
        let boundary = "lattecoach-\(UUID().uuidString)"
        var body = Data()
        body.append("--\(boundary)\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"tail.wav\"\r\nContent-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(audio)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        var req = URLRequest(url: baseURL.appendingPathComponent("practices/\(practiceId.uuidString)/audio/\(seq)"))
        req.httpMethod = "POST"
        req.timeoutInterval = 300
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await URLSession.shared.upload(for: req, from: body)
        try Self.check(response, data)
    }

    /// 判定の閾値の今の版
    struct Params: Decodable {
        let version: Int
        let values: [String: Double]
    }

    func params() async throws -> Params {
        let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("params"))
        try Self.check(response, data)
        return try JSONDecoder().decode(Params.self, from: data)
    }

    /// コーチの判定の調整の提案（承認待ち）
    struct Proposal: Decodable, Equatable {
        let changes: [String: Double]
        let before: [String: Double]
        let reason: String
        let evidence: String
    }
    struct ProposalResponse: Decodable {
        let proposal: Proposal?
        let current_version: Int
        let means: [String: String]
    }

    func proposal() async throws -> ProposalResponse {
        let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("params/proposal"))
        try Self.check(response, data)
        return try JSONDecoder().decode(ProposalResponse.self, from: data)
    }

    func decide(accept: Bool) async throws {
        var req = URLRequest(url: baseURL.appendingPathComponent("params/proposal/\(accept ? "accept" : "reject")"))
        req.httpMethod = "POST"
        let (data, response) = try await URLSession.shared.data(for: req)
        try Self.check(response, data)
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
