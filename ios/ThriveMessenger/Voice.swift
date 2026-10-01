import AVFoundation
import Foundation

/// Plays voice messages (MP3 from the server) and keeps them for the session.
@MainActor
final class VoicePlayer: NSObject, AVAudioPlayerDelegate {
    private var player: AVAudioPlayer?
    private var cache: [String: Data] = [:]
    /// Which message the live player belongs to, so a second activation pauses instead of restarting.
    private(set) var loadedID: String?

    func cached(_ id: String) -> Data? { cache[id] }
    func store(_ id: String, _ data: Data) { if !id.isEmpty { cache[id] = data } }

    /// The one play/pause state machine. Both the VoiceOver default action and the hardware Return key
    /// go through here, so they can never end up with two competing players.
    /// Same message playing -> pause. Same message paused -> resume. Anything else -> start from 0:00.
    func toggle(id: String, data: Data, label: String) {
        if let live = player, loadedID == id, !id.isEmpty {
            if live.isPlaying {
                live.pause()
                Announce.say("Paused")
            } else if live.play() {
                Announce.say("Resumed")
            } else {
                Announce.say("That voice message couldn't be played.")
            }
            return
        }
        play(id: id, data: data, label: label)
    }

    func play(id: String, data: Data, label: String) {
        player?.stop()
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try? AVAudioSession.sharedInstance().setActive(true)
        player = try? AVAudioPlayer(data: data)
        player?.delegate = self
        loadedID = id
        if player?.play() == true {
            Announce.say("Playing \(label)")
        } else {
            player = nil
            loadedID = nil
            Announce.say("That voice message couldn't be played.")
        }
    }

    func stop() { player?.stop(); player = nil; loadedID = nil }
    var isPlaying: Bool { player?.isPlaying ?? false }

    /// Once it reaches the end, forget it, so the next activation starts from the beginning
    /// instead of saying "Resumed" and sitting at 0:00 left. `nonisolated` because AVAudioPlayerDelegate
    /// is not main-actor bound; the AVAudioPlayer itself never crosses the hop.
    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor [weak self] in self?.playbackFinished() }
    }

    private func playbackFinished() {
        guard player?.isPlaying != true else { return }   // a different message started in the meantime
        player = nil
        loadedID = nil
    }
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
        try? AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetoothHFP])
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
