import AVFoundation
import Foundation

/// Plays voice messages (MP3 from the server) and keeps them for the session.
@MainActor
final class VoicePlayer: NSObject, AVAudioPlayerDelegate {
    private var player: AVAudioPlayer?
    private var cache: [String: Data] = [:]

    func cached(_ id: String) -> Data? { cache[id] }
    func store(_ id: String, _ data: Data) { if !id.isEmpty { cache[id] = data } }

    func play(_ data: Data, label: String) {
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try? AVAudioSession.sharedInstance().setActive(true)
        player = try? AVAudioPlayer(data: data)
        player?.delegate = self
        if player?.play() == true {
            Announce.say("Playing \(label)")
        } else {
            Announce.say("That voice message couldn't be played.")
        }
    }

    func stop() { player?.stop(); player = nil }
    var isPlaying: Bool { player?.isPlaying ?? false }
}

/// Records a short voice message as 16 kHz mono WAV (what the server expects), up to three minutes.
@MainActor
final class VoiceRecorder {
    private var recorder: AVAudioRecorder?
    private var url: URL { FileManager.default.temporaryDirectory.appendingPathComponent("thrive-voice.wav") }
    var isRecording: Bool { recorder?.isRecording ?? false }

    func start() async -> Bool {
        let allowed = await withCheckedContinuation { cont in
            AVAudioApplication.requestRecordPermission { cont.resume(returning: $0) }
        }
        guard allowed else {
            Announce.say("Thrive can't use the microphone. Allow it in Settings, Thrive.", important: true)
            return false
        }
        try? AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetooth])
        try? AVAudioSession.sharedInstance().setActive(true)
        let settings: [String: Any] = [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 16000, AVNumberOfChannelsKey: 1,
                                       AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false]
        recorder = try? AVAudioRecorder(url: url, settings: settings)
        return recorder?.record(forDuration: 180) ?? false
    }

    /// Stops and returns the WAV bytes and length in seconds.
    func stop() -> (Data, Double)? {
        guard let r = recorder else { return nil }
        let seconds = r.currentTime
        r.stop()
        recorder = nil
        guard let data = try? Data(contentsOf: url), seconds >= 0.5 else { return nil }
        return (data, seconds)
    }
}
