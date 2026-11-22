/* global AudioWorkletProcessor, registerProcessor */

class VoiceCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const samples = inputs[0]?.[0];
    if (samples?.length) {
      const batch = samples.slice();
      this.port.postMessage(batch, [batch.buffer]);
    }
    return true;
  }
}

registerProcessor("voice-capture", VoiceCaptureProcessor);
