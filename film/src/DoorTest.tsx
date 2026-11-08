import React from 'react';
import {AbsoluteFill, Audio, Easing, Sequence, interpolate, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont as loadLiterata} from '@remotion/google-fonts/Literata';
import {loadFont as loadAtkinson} from '@remotion/google-fonts/AtkinsonHyperlegible';

const {fontFamily: DISPLAY} = loadLiterata('normal', {weights: ['600'], subsets: ['latin']});
const {fontFamily: BODY} = loadAtkinson('normal', {weights: ['400', '700'], subsets: ['latin']});

export const DURATION_S = 34;
const HALL_S = 12;
const GAP0 = 4, GAPSTEP = 3.6;

const C = {ink: '#070a12', text: '#e9edf5', muted: '#8d96ab', screen: '#7cc4ff', core: '#d8efff', warm: '#f2a65a', warn: '#ffc857'};

const ramp = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
const fade = (t: number, a: number, b: number, c: number, d: number) => Math.min(ramp(t, a, b), 1 - ramp(t, c, d));

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  return {t: frame / fps, frame, width, height, portrait: height > width, u: Math.min(width, height) / 1080};
};

const GAPS: [string, string][] = [
  ['Strangers can reach them', 'Anyone in a shared server can send a friend request or a message.'],
  ['Anyone can pretend', 'A new account and a stolen photo look exactly like a real 15-year-old.'],
  ['The playbook looks like normal chat', 'Compliments, age questions, "add me on snap".'],
  ['Some servers exist to find kids', 'And an invite link looks the same whoever sent it.'],
  ['No one is watching', "Most servers are run by volunteers who can't read every message."],
];

type Cap = [number, number, 'Mom' | 'Narrator', string];
const CAPS: Cap[] = [
  [1.8, 6.6, 'Mom', 'He was home. Door closed, headphones on.'],
  [6.8, 11.4, 'Mom', "I remember thinking: at least he's safe in there."],
  [HALL_S + 0.4, HALL_S + 3.8, 'Narrator', 'A closed door feels safe. But there are gaps.'],
  ...GAPS.map(([a, b], i): Cap => [HALL_S + GAP0 + i * GAPSTEP, HALL_S + GAP0 + (i + 1) * GAPSTEP - 0.1, 'Narrator', `${a}. ${b}`]),
];

/* ---------------- scene 1: the hallway ---------------- */
const VP = {x: 800, y: 430};
const floorLine = (bx: number) => {
  const k = (690 - VP.y) / (900 - VP.y);
  return {x1: bx, y1: 900, x2: VP.x + (bx - VP.x) * k, y2: 690};
};

const Hallway: React.FC = () => {
  const {t, u} = useT();
  const push = 1 + 0.42 * ramp(t, 0, HALL_S);
  const drift = interpolate(t, [0, HALL_S], [0, -14]);
  const ping = Math.exp(-Math.pow((t - 9.2) / 0.32, 2));
  const flicker = 0.78 + 0.1 * Math.sin(t * 7.1) + 0.07 * Math.sin(t * 13.7 + 1) + 0.6 * ping;
  const dust = Array.from({length: 34}, (_, i) => {
    const x = 120 + random(`dx${i}`) * 420, y0 = 250 + random(`dy${i}`) * 480;
    const y = ((y0 - t * (6 + random(`ds${i}`) * 10) - 250 + 480 * 10) % 480) + 250;
    return {x: x + Math.sin(t * 0.6 + i) * 6, y, r: 0.8 + random(`dr${i}`) * 1.8, o: 0.25 + 0.5 * Math.abs(Math.sin(t * 0.8 + i))};
  });

  return (
    <AbsoluteFill style={{opacity: 1 - ramp(t, HALL_S - 0.9, HALL_S)}}>
      <svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" style={{width: '100%', height: '100%', transform: `translateX(${drift}px) scale(${push})`, transformOrigin: '50% 54%'}}>
        <defs>
          <radialGradient id="lamp" cx="300" cy="350" r="760" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#f2a65a" stopOpacity="0.55" />
            <stop offset="0.45" stopColor="#f2a65a" stopOpacity="0.12" />
            <stop offset="1" stopColor="#f2a65a" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="lwall" x1="0" x2="1"><stop offset="0" stopColor="#222842" /><stop offset="1" stopColor="#131829" /></linearGradient>
          <linearGradient id="rwall" x1="1" x2="0"><stop offset="0" stopColor="#151a2e" /><stop offset="1" stopColor="#10142a" /></linearGradient>
          <linearGradient id="floor" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor="#2c2318" /><stop offset="1" stopColor="#16120c" /></linearGradient>
          <radialGradient id="bspill" cx="800" cy="694" r="300" gradientTransform="translate(0 451) scale(1 0.35)" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#7cc4ff" stopOpacity="0.75" /><stop offset="1" stopColor="#7cc4ff" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="door" x1="0" x2="1"><stop offset="0" stopColor="#2f3657" /><stop offset="1" stopColor="#262c48" /></linearGradient>
          <filter id="b6" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" /></filter>
          <filter id="b18" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18" /></filter>
        </defs>
        <rect width="1600" height="900" fill="#0b0f1e" />
        <polygon points="0,0 1600,0 980,170 620,170" fill="#0c1020" />
        <polygon points="0,0 620,170 620,690 0,900" fill="url(#lwall)" />
        <polygon points="1600,0 980,170 980,690 1600,900" fill="url(#rwall)" />
        <polygon points="0,900 1600,900 980,690 620,690" fill="url(#floor)" />
        {Array.from({length: 13}, (_, i) => { const l = floorLine(-100 + i * 150); return <line key={i} {...l} stroke="#0d0a06" strokeOpacity="0.55" strokeWidth="2" />; })}
        <rect x="620" y="170" width="360" height="520" fill="#171c30" />
        <line x1="0" y1="900" x2="620" y2="690" stroke="#2a3150" strokeWidth="7" />
        <line x1="1600" y1="900" x2="980" y2="690" stroke="#1e2440" strokeWidth="7" />
        {/* picture frames */}
        <polygon points="120,290 300,322 300,462 120,468" fill="#1a2038" stroke="#3b3424" strokeWidth="6" />
        <circle cx="185" cy="380" r="22" fill="#2b3456" /><circle cx="240" cy="392" r="16" fill="#2b3456" />
        <polygon points="410,330 520,346 520,430 410,432" fill="#1a2038" stroke="#3b3424" strokeWidth="5" />
        <polygon points="1450,250 1300,292 1300,430 1450,428" fill="#161b34" stroke="#2a2a30" strokeWidth="5" />
        {/* the door */}
        <rect x="726" y="284" width="148" height="406" fill="#20263e" />
        <rect x="740" y="298" width="120" height="392" fill="url(#door)" />
        <rect x="752" y="312" width="96" height="150" rx="3" fill="none" stroke="#3a4266" strokeWidth="3" />
        <rect x="752" y="480" width="96" height="190" rx="3" fill="none" stroke="#3a4266" strokeWidth="3" />
        <circle cx="846" cy="500" r="5" fill="#a3aac0" />
        {/* light leaking: a hint of the gaps to come */}
        <line x1="740.5" y1="320" x2="740.5" y2="660" stroke={C.screen} strokeWidth="1.5" opacity={0.18 * flicker} />
        <line x1="859.5" y1="330" x2="859.5" y2="640" stroke={C.screen} strokeWidth="1.5" opacity={0.14 * flicker} />
        <ellipse cx="800" cy="702" rx="300" ry="60" fill="url(#bspill)" opacity={flicker} />
        <rect x="742" y="683" width="116" height="8" fill={C.screen} filter="url(#b6)" opacity={flicker} />
        <rect x="742" y="685" width="116" height="4" fill={C.core} opacity={0.9 * flicker} />
        {/* sneakers by the door */}
        <path d="M680 700 q18 -14 44 -4 l4 10 h-50z" fill="#0d1018" /><path d="M680 706 h52" stroke="#c9ced8" strokeWidth="2.5" />
        <path d="M694 714 q18 -14 44 -4 l4 10 h-50z" fill="#10131c" /><path d="M694 720 h52" stroke="#c9ced8" strokeWidth="2.5" />
        {/* wall lamp */}
        <circle cx="300" cy="350" r="120" fill="#f2a65a" opacity="0.22" filter="url(#b18)" />
        <polygon points="268,322 332,322 348,368 252,368" fill="#f6c98a" />
        <rect x="296" y="368" width="8" height="34" fill="#3a3326" />
        <rect width="1600" height="900" fill="url(#lamp)" />
        {/* laundry basket, foreground */}
        <polygon points="40,830 290,790 330,900 70,900" fill="#2c2619" />
        <polygon points="40,830 290,790 300,812 52,852" fill="#3a3222" />
        {dust.map((d, i) => <circle key={i} cx={d.x} cy={d.y} r={d.r} fill="#ffd9a6" opacity={d.o * 0.6} />)}
      </svg>
      <div style={{position: 'absolute', top: '11%', left: '6%', right: '6%', textAlign: 'center', fontFamily: DISPLAY, fontWeight: 600,
        fontSize: 64 * u, color: C.text, textShadow: '0 4px 30px #000', opacity: fade(t, 0.2, 1, 4, 5.2)}}>
        He was home. Door closed. Safe.
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- scene 5: where it gets in ---------------- */
const CRACKS = [
  {x1: 119, y1: 92, x2: 119, y2: 228, nx: 84, ny: 160},
  {x1: 281, y1: 100, x2: 281, y2: 246, nx: 316, ny: 172},
  {x1: 152, y1: 59, x2: 256, y2: 59, nx: 204, ny: 28},
  {x1: 281, y1: 292, x2: 281, y2: 430, nx: 316, ny: 360},
  {x1: 119, y1: 272, x2: 119, y2: 430, nx: 84, ny: 350},
];

const Door: React.FC<{t: number}> = ({t}) => {
  const under = 0.8 + 0.12 * Math.sin(t * 2.3) + 0.06 * Math.sin(t * 7.3);
  return (
    <svg viewBox="0 0 400 520" style={{width: '100%', height: '100%', overflow: 'visible'}}>
      <defs>
        <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#10162a" /><stop offset="1" stopColor="#151b30" /></linearGradient>
        <linearGradient id="dpanel" x1="0" x2="1"><stop offset="0" stopColor="#323a5e" /><stop offset="1" stopColor="#272d4a" /></linearGradient>
        <radialGradient id="knob" cx="0.35" cy="0.35" r="0.7"><stop offset="0" stopColor="#e3e7f0" /><stop offset="1" stopColor="#6d7488" /></radialGradient>
        <linearGradient id="spill2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7cc4ff" stopOpacity="0.7" /><stop offset="1" stopColor="#7cc4ff" stopOpacity="0" /></linearGradient>
        <filter id="g8" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="7" /></filter>
        <filter id="g20" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="20" /></filter>
      </defs>
      {/* wall and floor run far past the viewBox so the room fills the frame in every aspect ratio */}
      <rect x="-3000" y="-2000" width="6400" height="2470" fill="url(#wall)" />
      <rect x="-3000" y="470" width="6400" height="2000" fill="#1c1710" />
      {Array.from({length: 41}, (_, i) => -1800 + i * 100).map(x => <line key={x} x1={x} y1="472" x2={x + (x - 200) * 2.5} y2="1400" stroke="#0f0c08" strokeWidth="1.5" />)}
      <rect x="-3000" y="464" width="6400" height="8" fill="#232a44" />
      <rect x="104" y="44" width="192" height="428" fill="#1f253b" />
      <path d="M104 472 V44 H296" fill="none" stroke="#2c3452" strokeWidth="3" />
      <rect x="120" y="60" width="160" height="408" fill="url(#dpanel)" />
      <rect x="138" y="82" width="124" height="150" rx="4" fill="#2a3150" stroke="#3d4670" strokeWidth="2.5" />
      <rect x="138" y="262" width="124" height="180" rx="4" fill="#2a3150" stroke="#3d4670" strokeWidth="2.5" />
      <circle cx="262" cy="262" r="6.5" fill="url(#knob)" />
      {/* gap under the door: always open */}
      <polygon points="120,471 280,471 350,560 50,560" fill="url(#spill2)" opacity={under * 0.8} />
      <line x1="122" y1="469" x2="278" y2="469" stroke={C.screen} strokeWidth="10" filter="url(#g8)" opacity={under} />
      <line x1="122" y1="469" x2="278" y2="469" stroke={C.core} strokeWidth="2.5" opacity={under} />
      {CRACKS.map((c, i) => {
        const a = GAP0 + i * GAPSTEP, p = ramp(t, a, a + 0.9), shimmer = 0.85 + 0.15 * Math.sin(t * 3 + i * 1.7);
        const pop = interpolate(t, [a + 0.3, a + 0.6, a + 0.85], [0, 1.18, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const vertical = c.x1 === c.x2;
        return (
          <g key={i}>
            <ellipse cx={(c.x1 + c.x2) / 2 + (vertical ? (c.x1 < 200 ? -26 : 26) : 0)} cy={(c.y1 + c.y2) / 2 + (vertical ? 0 : -20)}
              rx={vertical ? 30 : 70} ry={vertical ? 80 : 22} fill={C.screen} filter="url(#g20)" opacity={0.35 * p * shimmer} />
            <line {...c} stroke={C.screen} strokeWidth="10" strokeLinecap="round" filter="url(#g8)" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} opacity={shimmer} />
            <line {...c} stroke={C.core} strokeWidth="2.5" strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} />
            <g transform={`translate(${c.nx} ${c.ny}) scale(${pop})`} opacity={Math.min(1, pop)}>
              <circle r="14" fill="#16223a" stroke={C.screen} strokeWidth="2" />
              <text y="5" textAnchor="middle" fontFamily={BODY} fontWeight={700} fontSize="15" fill={C.text}>{i + 1}</text>
            </g>
          </g>
        );
      })}
    </svg>
  );
};

const Gaps: React.FC = () => {
  const {t, u, portrait} = useT();
  const push = 1 + 0.06 * ramp(t, 0, 22);
  const doorBox: React.CSSProperties = portrait
    ? {position: 'absolute', left: '10%', right: '10%', top: '3%', height: '46%'}
    : {position: 'absolute', left: '4%', width: '42%', top: '6%', bottom: '20%'};
  const listBox: React.CSSProperties = portrait
    ? {position: 'absolute', left: '8%', right: '6%', top: '52%', bottom: '22%'}
    : {position: 'absolute', left: '49%', right: '5%', top: '8%', bottom: '22%'};
  return (
    <AbsoluteFill style={{opacity: ramp(t, 0, 0.8)}}>
      <div style={{...doorBox, transform: `scale(${push})`}}><Door t={t} /></div>
      <div style={{...listBox, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: (portrait ? 22 : 26) * u, fontFamily: BODY, color: C.text}}>
        <div style={{fontSize: 24 * u, letterSpacing: '0.18em', fontWeight: 700, color: C.muted, opacity: ramp(t, 0.4, 1.2)}}>WHERE IT GETS IN</div>
        {GAPS.map(([title, sub], i) => {
          const a = GAP0 + i * GAPSTEP, p = ramp(t, a + 0.2, a + 0.9);
          return (
            <div key={i} style={{display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 22 * u, rowGap: 4 * u, alignItems: 'start',
              opacity: 0.1 + 0.9 * p, transform: `translateX(${(1 - p) * 30 * u}px)`}}>
              <div style={{width: 46 * u, height: 46 * u, borderRadius: '50%', border: `${3 * u}px solid ${C.screen}`, display: 'grid', placeItems: 'center',
                fontWeight: 700, fontSize: 24 * u, background: '#16223a', boxShadow: `0 0 ${24 * u * p}px ${C.screen}66`}}>{i + 1}</div>
              <div style={{fontSize: (portrait ? 40 : 38) * u, fontWeight: 700, lineHeight: 1.2, alignSelf: 'center'}}>{title}</div>
              {!portrait && <div style={{gridColumn: 2, fontSize: 26 * u, color: '#b9c1d3', lineHeight: 1.35}}>{sub}</div>}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- overlays ---------------- */
const Captions: React.FC = () => {
  const {t, u, portrait} = useT();
  const c = CAPS.find(([a, b]) => t >= a && t < b);
  if (!c) return null;
  const [a, b, who, text] = c, o = fade(t, a, a + 0.25, b - 0.25, b);
  return (
    <div style={{position: 'absolute', left: '5%', right: '5%', bottom: portrait ? '4%' : '6%', display: 'flex', justifyContent: 'center', opacity: o}}>
      <div style={{background: 'rgba(5,7,13,0.78)', borderRadius: 14 * u, padding: `${12 * u}px ${30 * u}px`, maxWidth: portrait ? '94%' : '78%', textAlign: 'center', fontFamily: BODY}}>
        <div style={{fontSize: 20 * u, letterSpacing: '0.16em', fontWeight: 700, color: who === 'Mom' ? C.warn : C.screen, marginBottom: 4 * u}}>{who.toUpperCase()}</div>
        <div style={{fontSize: (portrait ? 40 : 40) * u, lineHeight: 1.35, color: C.text}}>{text}</div>
      </div>
    </div>
  );
};

const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{mixBlendMode: 'overlay', opacity: 0.09, pointerEvents: 'none'}}>
      <svg width="100%" height="100%">
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={frame % 12} /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </AbsoluteFill>
  );
};

export const DoorTest: React.FC = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: C.ink}}>
      <Audio src={staticFile('ambience.wav')} />
      <Sequence durationInFrames={HALL_S * fps}><Hallway /></Sequence>
      <Sequence from={HALL_S * fps}><Gaps /></Sequence>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,0.55) 100%)'}} />
      <Grain />
      <Captions />
    </AbsoluteFill>
  );
};
