export const RECORDING_RATE = 16_000;
export const RECORDING_SECONDS = 60;

export function wav(samples: Float32Array): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const bytes = new DataView(buffer);
  bytes.setUint32(0, 0x52494646);
  bytes.setUint32(4, buffer.byteLength - 8, true);
  bytes.setUint32(8, 0x57415645);
  bytes.setUint32(12, 0x666d7420);
  bytes.setUint32(16, 16, true);
  bytes.setUint16(20, 1, true);
  bytes.setUint16(22, 1, true);
  bytes.setUint32(24, RECORDING_RATE, true);
  bytes.setUint32(28, RECORDING_RATE * 2, true);
  bytes.setUint16(32, 2, true);
  bytes.setUint16(34, 16, true);
  bytes.setUint32(36, 0x64617461);
  bytes.setUint32(40, samples.length * 2, true);
  for (let index = 0; index < samples.length; index += 1) {
    const amplitude = Math.max(-1, Math.min(1, samples[index] ?? 0));
    bytes.setInt16(44 + index * 2, amplitude * (amplitude < 0 ? 32768 : 32767), true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}
