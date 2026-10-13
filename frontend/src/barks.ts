import type { DogBreed } from "./DogPortrait";

type BarkProfile = {
  pitch: number;
  formant: number;
  upperFormant: number;
  length: number;
  count: number;
  pause: number;
};

// Each dog has a different pitch, resonance, and call rhythm.
const BARK_PROFILES: Record<DogBreed, BarkProfile> = {
  bulldog: { pitch: 138, formant: 470, upperFormant: 980, length: 0.18, count: 2, pause: 0.12 },
  golden: { pitch: 238, formant: 650, upperFormant: 1370, length: 0.115, count: 2, pause: 0.1 },
  terrier: { pitch: 345, formant: 840, upperFormant: 1760, length: 0.08, count: 2, pause: 0.065 },
  shepherd: { pitch: 158, formant: 520, upperFormant: 1110, length: 0.19, count: 1, pause: 0 },
  cocker: { pitch: 222, formant: 610, upperFormant: 1290, length: 0.125, count: 2, pause: 0.16 },
};

function addBarkBurst(context: AudioContext, output: GainNode, profile: BarkProfile, start: number): void {
  const end = start + profile.length;
  const pitchJitter = 0.95 + Math.random() * 0.1;

  // Filtered breath noise makes the short, rough attack of a bark.
  const noiseBuffer = context.createBuffer(
    1,
    Math.ceil(context.sampleRate * profile.length),
    context.sampleRate,
  );
  const noiseSamples = noiseBuffer.getChannelData(0);
  for (let index = 0; index < noiseSamples.length; index += 1) {
    noiseSamples[index] = Math.random() * 2 - 1;
  }

  const noise = context.createBufferSource();
  noise.buffer = noiseBuffer;

  const lowerResonance = context.createBiquadFilter();
  lowerResonance.type = "bandpass";
  lowerResonance.Q.setValueAtTime(2.2, start);
  lowerResonance.frequency.setValueAtTime(profile.formant * pitchJitter, start);
  lowerResonance.frequency.exponentialRampToValueAtTime(profile.formant * 0.78, end);

  const lowerEnvelope = context.createGain();
  lowerEnvelope.gain.setValueAtTime(0.0001, start);
  lowerEnvelope.gain.linearRampToValueAtTime(0.2, start + 0.012);
  lowerEnvelope.gain.setValueAtTime(0.12, start + profile.length * 0.34);
  lowerEnvelope.gain.exponentialRampToValueAtTime(0.0001, end);
  noise.connect(lowerResonance);
  lowerResonance.connect(lowerEnvelope);
  lowerEnvelope.connect(output);

  const upperResonance = context.createBiquadFilter();
  upperResonance.type = "bandpass";
  upperResonance.Q.setValueAtTime(2.8, start);
  upperResonance.frequency.setValueAtTime(profile.upperFormant * pitchJitter, start);
  upperResonance.frequency.exponentialRampToValueAtTime(profile.upperFormant * 0.86, end);

  const upperEnvelope = context.createGain();
  upperEnvelope.gain.setValueAtTime(0.0001, start);
  upperEnvelope.gain.linearRampToValueAtTime(0.08, start + 0.012);
  upperEnvelope.gain.exponentialRampToValueAtTime(0.0001, end);
  noise.connect(upperResonance);
  upperResonance.connect(upperEnvelope);
  upperEnvelope.connect(output);

  // A quiet falling triangle tone gives the bark a voiced, rounded body.
  const voice = context.createOscillator();
  voice.type = "triangle";
  voice.frequency.setValueAtTime(profile.pitch * pitchJitter, start);
  voice.frequency.exponentialRampToValueAtTime(profile.pitch * 0.68, end);

  const voiceTone = context.createBiquadFilter();
  voiceTone.type = "lowpass";
  voiceTone.frequency.setValueAtTime(Math.max(420, profile.formant), start);
  voiceTone.frequency.exponentialRampToValueAtTime(Math.max(300, profile.formant * 0.7), end);

  const voiceEnvelope = context.createGain();
  voiceEnvelope.gain.setValueAtTime(0.0001, start);
  voiceEnvelope.gain.linearRampToValueAtTime(0.075, start + 0.009);
  voiceEnvelope.gain.exponentialRampToValueAtTime(0.0001, end);
  voice.connect(voiceTone);
  voiceTone.connect(voiceEnvelope);
  voiceEnvelope.connect(output);

  noise.start(start);
  noise.stop(end + 0.01);
  voice.start(start);
  voice.stop(end + 0.01);
}

/** Make a brief, quiet, locally synthesized bark. Sound remains opt-in in the dashboard. */
export function playDogBark(context: AudioContext, breed: DogBreed): void {
  if (context.state !== "running") return;

  const profile = BARK_PROFILES[breed];
  const master = context.createGain();
  master.gain.setValueAtTime(0.52, context.currentTime);
  master.connect(context.destination);

  for (let index = 0; index < profile.count; index += 1) {
    const start = context.currentTime + 0.01 + index * (profile.length + profile.pause);
    addBarkBurst(context, master, profile, start);
  }

  const finish = context.currentTime + profile.count * profile.length + (profile.count - 1) * profile.pause + 0.12;
  master.gain.setValueAtTime(0.52, finish - 0.055);
  master.gain.linearRampToValueAtTime(0.0001, finish);
  window.setTimeout(() => master.disconnect(), Math.max(0, (finish - context.currentTime) * 1000) + 200);
}
