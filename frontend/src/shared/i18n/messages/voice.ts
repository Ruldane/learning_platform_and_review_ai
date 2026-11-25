export const voice = {
  microphoneHint:
    "Record up to one minute. The audio is sent to OpenAI when you ask for its transcription.",
  start: "Start recording",
  asking: "Requesting microphone access…",
  stop: "Stop recording",
  recording: "Microphone on · stops after one minute.",
  transcribe: "Transcribe the recording",
  transcribing: "Transcribing…",
  cancel: "Discard audio",
  cancelled: "Audio discarded. You can keep typing.",
  noAudio: "No sound recorded. You can type instead.",
  microphoneError: "The microphone is unavailable. You can type instead.",
  review: "Transcription added. Read over and fix your text before sending it.",
  listen: "Prepare playback with an AI voice",
  preview: "Prepare playback of the beginning with an AI voice",
  preparing: "Preparing playback…",
  player: "Playback with an AI voice",
} as const;
