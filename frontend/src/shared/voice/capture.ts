import captureWorklet from "./pcmCapture.js?url&no-inline";
import { RECORDING_RATE, RECORDING_SECONDS, wav } from "./wav";

export interface VoiceCapture {
  finish(): Blob | null;
  cancel(): void;
}

export function canRecord(): boolean {
  return (
    typeof window !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    typeof AudioContext !== "undefined" &&
    typeof AudioWorkletNode !== "undefined"
  );
}

function collect(
  context: AudioContext,
  stream: MediaStream,
  onData: () => void,
  onLimit: () => void,
): VoiceCapture {
  const source = context.createMediaStreamSource(stream);
  const processor = new AudioWorkletNode(context, "voice-capture", { channelCount: 1 });
  const samples = new Float32Array(RECORDING_RATE * RECORDING_SECONDS);
  let length = 0;
  let phase = 0;
  let sum = 0;
  let count = 0;
  processor.port.onmessage = (event: MessageEvent<Float32Array>) => {
    const first = length === 0;
    for (const amplitude of event.data) {
      if (length === samples.length) break;
      sum += amplitude;
      count += 1;
      phase += RECORDING_RATE;
      if (phase >= context.sampleRate) {
        samples[length] = sum / count;
        length += 1;
        phase -= context.sampleRate;
        sum = 0;
        count = 0;
      }
    }
    if (first && length) onData();
    if (length === samples.length) onLimit();
  };
  source.connect(processor).connect(context.destination);
  const cancel = () => {
    processor.port.close();
    source.disconnect();
    processor.disconnect();
  };
  return {
    cancel,
    finish: () => (length ? wav(samples.subarray(0, length)) : null),
  };
}

export async function openCapture(
  signal: AbortSignal,
  onData: () => void,
  onLimit: () => void,
): Promise<VoiceCapture> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
  let context: AudioContext | undefined;
  let capture: VoiceCapture | undefined;
  let closed = false;
  const cancel = () => {
    if (closed) return;
    closed = true;
    signal.removeEventListener("abort", cancel);
    stream.getTracks().forEach((track) => track.stop());
    capture?.cancel();
    if (context && context.state !== "closed") void context.close().catch(() => undefined);
  };
  try {
    signal.throwIfAborted();
    signal.addEventListener("abort", cancel, { once: true });
    context = new AudioContext();
    if (context.sampleRate < RECORDING_RATE) throw new Error("unsupported_sample_rate");
    await context.audioWorklet.addModule(captureWorklet);
    signal.throwIfAborted();
    await context.resume();
    signal.throwIfAborted();
    capture = collect(context, stream, onData, onLimit);
    return {
      cancel,
      finish: () => {
        const clip = capture?.finish() ?? null;
        cancel();
        return clip;
      },
    };
  } catch (error) {
    cancel();
    throw error;
  }
}
