/**
 * AudioWorkletProcessor that captures raw PCM Float32 samples
 * and forwards them to the main thread for conversion and transmission.
 */
class AudioProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length > 0) {
      // Clone the array since it's reused by the AudioWorklet engine
      this.port.postMessage(input[0].slice());
    }
    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
