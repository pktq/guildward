# Making "The Door" for real: tools and costs (researched 2026-11-07)

Short version: Claude can build a polished **motion-graphics** film (light, UI, chat, counters, silhouettes, parallax, captions, voice, music, every aspect ratio) with code-to-video tools. What Claude can't do is expressive **character acting** (faces, body language) at the level of a human 2D animator. Most of "The Door" is light, screens and silhouettes, so the realistic best route is a **hybrid**: a human illustrator draws the characters and backgrounds as layered stills, and Claude animates and assembles everything.

## Option A: Claude makes it (code-to-video)

| Tool | How Claude uses it | Good for | Cost | Notes |
|---|---|---|---|---|
| **Remotion** (React → MP4) | **Official plugin in the Anthropic directory** (12 skills: create, captions, audio, render…), or `npx skills add remotion-dev/skills` | Motion graphics, captions, audio sync, multi-format renders | Free for companies of **3 people or fewer**; paid company licence beyond that | Biggest ecosystem. The animatic's per-scene `render(t)` ports to React components. |
| **HyperFrames** (HeyGen, HTML → MP4) | Official skills: `npx skills add heygen-com/hyperframes` | Same as Remotion, but plain HTML/SVG, the closest match to the existing animatic | Free (Apache 2.0) | Needs Node 22+ and FFmpeg. Windows support not verified. |
| **animation-studio** plugin (Anthropic directory) | Skill draws every frame in code and synthesises the soundtrack; outputs a 1080p MP4 in 16:9 or 9:16 | A quick experiment | Free | Community plugin; quality unknown. Worth one test scene. |
| **Figma Motion** (already connected) | Figma MCP `export_video` renders a timeline to MP4 | Product UI cards only | Needs a Figma plan with motion | One report says exported colours come out darker. |
| After Effects / Blender MCP | Community MCP servers | Highest ceiling, but a human still has to design the animation | AE subscription / free | Not worth it without an animator. |

**Avoid AI video generators (Runway, Veo, Sora, Kling) for this film.** Their child-safety filters target exactly this subject: Veo rejects depictions of children unless your project is allowlisted, and Runway bans grooming content and reports to NCMEC. A film about a minor being sextorted risks refusals, account flags or bans, even though ours is non-explicit. At most, use them for empty shots (a hallway, a door, light).

**Audio**
- **Voice:** ElevenLabs. Commercial use starts on the ~$5–6/month plan, and it supports Swedish. Have a native speaker check the Swedish read. For the emotional lines (Mom), a real voice actor is noticeably better.
- **Music and SFX:** Epidemic Sound or Artlist, about $200–400/year. Check that the plan covers paid social ads and what happens after you cancel.
- **Captions:** generated from the voice track (Whisper word timings); Remotion has caption skills.

**Pipeline (Claude does everything except the steps marked "you")**
1. Install the Remotion plugin (or HyperFrames skills).
2. Generate the VO in English and Swedish. **You** pick the voice and approve the Swedish read.
3. Time the captions from the VO.
4. Port the seven animatic scenes, driven by the audio timeline.
5. Add music and SFX. **You** buy the licences.
6. Render 16:9, 4:5 and 9:16 plus the 90/60/30 s cuts. **You** review frames.

Cost: about **$50–500**, plus a few days of work. Quality: strong motion graphics; characters stay as silhouettes, back views and simple puppets.

## Option B: Hybrid (recommended)

Same pipeline as A, but a **human illustrator** draws the art in layers, so Claude can move it with parallax, light, blinks and small puppet motion:
- a character sheet for Leo, Mom and the offender silhouette
- 6–8 backgrounds (hallway, bedroom, desk, kitchen…)
- style frames

Cost estimate (not quoted): illustration about **$1.5–5k**, plus optional human VO about $1–4k. **Total about $2–9k (≈ 19–85k SEK).** This gets you about 80% of a studio look at roughly a fifth of the price.

## Option C: Commission an animator or studio (last resort)

Sources are mostly vendor price guides, so treat these as ranges and get real quotes. FX assumed: 1 USD ≈ 9.5 SEK.

| Tier | Who | All-in for this film (3 min + cutdowns + EN/SV VO + music) | Time |
|---|---|---|---|
| Cheap | Fiverr/Upwork mid-tier, or an Eastern Europe/Asia freelancer; rigged, limited animation | **$4.5–11k (≈ 43–105k SEK)** | 10–16 weeks |
| Solid | Portfolio freelancer or small studio; custom characters, 2–3 revision rounds | **$12–33k (≈ 115–310k SEK)** | 8–14 weeks |
| Premium | Nordic/Western studio or agency; style frames, strong character acting | **$33–62k (≈ 315–590k SEK)** | 8–14 weeks |
| Student | The Animation Workshop (Denmark) takes client briefs | ~$3–10k | Slow, quality varies |

Rates and drivers:
- Character-driven 2D runs about $4–15k per finished minute; frame-by-frame costs $15–30k/min.
- Cost is driven by the number of characters and how much they act, the number of unique scenes, and revision rounds. UI cards and stats are cheap; the boy and mother acting is the expensive part.
- The existing script and animatic should save 1–2 weeks and roughly 10–20%.

**If you commission, put these in the brief and contract:**
- In the brief: the script and animatic, runtime, the 4 formats and 3 aspect ratios, EN + SV versions, 2–3 style references, and a budget range.
- Full copyright assignment, including cutdowns and derivatives.
- Source files (AE, Moho, Toon Boom or Rive projects).
- 2–3 defined revision rounds, and milestone payments (style frames → animatic lock → rough → final).
- Music licences that cover paid social.
- A sensitivity review, since the film depicts a minor.

Red flags:
- no character-acting samples in the portfolio
- "unlimited revisions" with no timeline
- refusal to hand over source files
- a quote far below everyone else

**Funding:** nothing confirmed. Allmänna arvsfonden funds work for children and youth, but only through a non-profit association, which is one more reason to form the planned ideell förening.

## Sources
Remotion: [AI skills](https://www.remotion.dev/docs/ai/skills) · [licence pricing](https://www.remotion.dev/docs/license/pricing) · [licence FAQ](https://www.remotion.dev/docs/license/faq) · [HyperFrames](https://github.com/heygen-com/hyperframes) · [Remotion vs Motion Canvas vs Revideo](https://www.pkgpulse.com/guides/remotion-vs-motion-canvas-vs-revideo-programmatic-video-2026) · [Runway usage policy](https://runway.com/safety/usage-policy) · [Vertex/Veo responsible-AI guidelines](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/responsible-ai-and-usage-guidelines) · [ElevenLabs Swedish](https://elevenlabs.io/languages/swedish) · [Figma Motion export issue](https://forum.figma.com/report-a-problem-6/figma-motion-exporting-problem-57413) · [Prolific Studio](https://blog.prolificstudio.co/blog/how-much-does-animation-cost/) · [Maverick Frame](https://maverickframe.com/blog/explainer-video-cost/) · [Pixune](https://pixune.com/blog/animated-explainer-video-cost/) · [Vidico](https://vidico.com/news/how-much-does-animation-cost/) · [GVAA rate guide](https://globalvoiceacademy.com/gvaa-rate-guide-2/) · [Contra cutdown package](https://contra.com/s/mYAbFFkg-social-cutdowns-and-format-adaptations) · [The Animation Workshop student work](https://noem.natmus.dk/taw-student-work)

Not verified: Nordic freelance day rates, Swedish VO rates, Remotion's paid price, HyperFrames on Windows, Swedish TTS quality, Sora and Kling policies, and the illustration estimate in option B.
