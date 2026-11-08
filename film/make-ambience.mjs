// Writes public/ambience.wav: room tone, low pad, a muffled phone ping, and one low tone per gap.
// shortcut: synthesized placeholder sound, swap for licensed music/SFX in the real film.
import {writeFileSync} from 'node:fs';

const SR = 48000, DUR = 34, N = SR * DUR;
const out = new Float32Array(N);
const PING = 9.2, GAPS0 = 12 + 4, GAPSTEP = 3.6;
const gapNotes = [110, 130.81, 146.83, 164.81, 196]; // A2 C3 D3 E3 G3

let brown = 0, seed = 7;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296) * 2 - 1;
const env = (t, a, d) => (t < 0 ? 0 : (t < a ? t / a : Math.exp(-(t - a) / d)));
const smooth = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));

for (let i = 0; i < N; i++) {
  const t = i / SR;
  brown = (brown + rnd() * 0.02) * 0.995;
  let s = brown * 0.9; // room tone
  // whoosh into the door scene
  s += rnd() * 0.05 * Math.exp(-Math.pow((t - 11.8) / 0.5, 2));
  // pad: swells from 0, dips at the cut, grows through the gaps
  const padAmp = 0.022 * smooth(t, 0, 4) * (1 - 0.6 * Math.exp(-Math.pow((t - 12) / 0.6, 2))) * (1 + 0.8 * smooth(t, 12, 32));
  const lfo = 1 + 0.25 * Math.sin(2 * Math.PI * 0.11 * t);
  s += padAmp * lfo * (Math.sin(2 * Math.PI * 55 * t) + 0.6 * Math.sin(2 * Math.PI * 82.41 * t + 1) + 0.35 * Math.sin(2 * Math.PI * 110.3 * t + 2));
  // muffled notification behind the door
  const p = t - PING;
  s += 0.07 * env(p, 0.005, 0.35) * (Math.sin(2 * Math.PI * 1046.5 * p) + 0.5 * Math.sin(2 * Math.PI * 1568 * p));
  // one low tone per gap
  gapNotes.forEach((f, k) => {
    const g = t - (GAPS0 + k * GAPSTEP);
    if (g > 0 && g < 4) s += 0.06 * env(g, 0.02, 0.9) * (Math.sin(2 * Math.PI * f * g) + 0.3 * Math.sin(2 * Math.PI * f * 2.01 * g));
  });
  out[i] = Math.max(-1, Math.min(1, s * smooth(t, 0, 0.5) * (1 - smooth(t, DUR - 1.5, DUR))));
}

const buf = Buffer.alloc(44 + N * 2);
buf.write('RIFF', 0); buf.writeUInt32LE(36 + N * 2, 4); buf.write('WAVE', 8);
buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22);
buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
buf.write('data', 36); buf.writeUInt32LE(N * 2, 40);
for (let i = 0; i < N; i++) buf.writeInt16LE(Math.round(out[i] * 32767), 44 + i * 2);
writeFileSync(new URL('./public/ambience.wav', import.meta.url), buf);
const peak = out.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
console.log('ambience.wav written, peak', peak.toFixed(3));
