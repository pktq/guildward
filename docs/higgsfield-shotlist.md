# "The Door": Higgsfield shot list

**Split of work.** Higgsfield makes the *plates*: rooms, light, objects, adult hands, the man from behind. Remotion (`film/`) adds everything that must be exact: chat bubbles, numbers, product UI, the glowing gaps, captions, voice and music. AI video still garbles text, so no shot below asks for readable text.

**No child on screen, ever.** Every prompt below describes only what is in the frame. There are no children, no faces of minors, and nothing sexual. That keeps us inside Higgsfield's terms (section 5.1) and keeps the film honest.

## Setup

1. Connect the official MCP: Claude desktop → **Settings → Connectors → Add custom connector**, name `Higgsfield`, URL `https://mcp.higgsfield.ai/mcp`, then **Connect** and sign in to Higgsfield. (Claude Code CLI: `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp`.) After that, Claude can generate, check and download the shots itself.
2. Plan: the free tier has a small daily allowance. Expect to need one month of a paid plan; its exact cost per Veo/Kling clip wasn't verified. Ask Claude for a credit estimate before each batch.
3. Plates go in `film/public/plates/NN-name.mp4`. Remotion runs the composition at **24 fps** to match.

## Style bible (start every image prompt with this)

> Cinematic film still, quiet Scandinavian family drama. Night interior of a modest home. Low-key lighting: warm amber tungsten lamp light against cold blue screen glow. Soft haze, subtle 35mm film grain, shallow depth of field, muted desaturated colours, deep soft shadows, painterly realism. No text, no logos, no watermark.

**Negative / avoid:** text, letters, logos, watermark, children, faces, cartoon, 3D render look, oversaturated, HDR, plastic skin.

**Consistency:** generate the **hero door (shot 11) first**, then use it as the reference image for shots 01, 02 and 13 so it's the same door everywhere. Use the shot 01 frame as the reference for every hallway shot.

**Workflow per shot:** generate 3–4 keyframe images → pick one → image-to-video, 5–10 s, using the camera move given → download at the highest resolution.

**Locked-off (L) shots:** Remotion draws UI or light on top of these, so the camera must not move, or only push in very slowly. Say "static camera, tripod" in the motion prompt.

## Shots

| # | Scene | Len | Image prompt (after the style bible) | Motion prompt | Remotion adds |
|---|---|---|---|---|---|
| 01 | 1 The door | 8 s | A long narrow hallway at night. Framed family photos on the walls, a warm wall lamp on the left, wooden floorboards. At the far end, a closed white bedroom door with cold blue light glowing from the gap underneath. A pair of sneakers beside the door. | Slow dolly forward toward the door. Dust drifts in the lamp light. The blue light under the door flickers softly, like a screen. | Hook text, Mom captions |
| 02 | 1 The door | 4 s | Floor-level close-up of the gap under a closed bedroom door. Cold blue flickering light spills onto the floorboards; warm light from behind the camera. | Static camera. The light flickers, then pulses brighter once. | The phone "ping" sound |
| 03 | 2 What it is | 10 s **L** | Abstract dark bedroom wall and ceiling, washed with slowly moving blue light from an unseen screen, out of focus. | Static camera. Slow rippling light. | The "Sextortion" title, diagram, the two cards |
| 04 | 3 How it works | 10 s **L** | Seen from behind an empty gaming chair: a desk at night, a glowing monitor with an out-of-focus blurred screen, a headset resting on the desk, a soda can, posters on the wall in shadow. Nobody in the room. | Static camera, very slow push in. The monitor light flickers. | The Meet→Trust→Move→Trap rail and the whole chat window |
| 05 | 3 Trap | 6 s **L** | A smartphone lying face-up on a rumpled duvet in a dark bedroom. Its screen is a soft white glow with no content, casting blue light on the fabric. | Static camera, slow rack focus onto the phone. | Threat messages, countdown timer |
| 06 | 3 Trap | 8 s | Seen from directly behind: an adult man sitting in a dim, cluttered room at a desk with six glowing monitors, each showing a blurred, unreadable chat window. Harsh cold light. His face is never visible. | Slow push in over his shoulder. | The "copy-pasted chats" grid, cut in afterwards |
| 07 | 4 Why kids | 6 s **L** | A family dinner table in warm light: three plates, one barely touched, a smartphone lying face-down beside it. Out-of-focus adult hands at the edge of the frame. | Static camera. The face-down phone buzzes slightly on the table. | "Phone face-down at dinner" circle and caption |
| 08 | 4 Why kids | 5 s | A kitchen doorway at night seen from the hallway, warm light, an adult woman's silhouette washing dishes, seen from behind. | Slow drift sideways. | "Just tired." |
| 09 | 4 Why kids | 6 s **L** | Pure black background with very faint blue haze. | Static camera, haze drifts. | The stats counting up (or use plain black in Remotion and skip this shot) |
| 11 | 5–6 Gaps | 12 s **L** | **Hero door.** Front view of a closed white bedroom door at night in a dark hallway, perfectly centred and symmetrical. A strong cold blue glow comes from the gap under the door; the rest of the frame is faint. | Static camera, tripod. Only the light under the door flickers. | The five glowing gaps, numbers, list, the product cards, closing each gap |
| 12 | 6 | 6 s **L** | Same door, but the glow under the door is much softer and the hallway is warmer, as if the lamp was turned on. | Static camera. | The summary of closed gaps |
| 13 | 7 Last gap | 8 s | Same door, seen from the hallway. The door slowly swings open toward the camera's left, and soft light floods out of the room and fills the frame. No one is visible, only light. | The door opens slowly; light blooms until it almost washes out the frame. | Leo's line (voice only), the parent card before it |
| 14 | 7 Last gap | 5 s | Close-up of an adult woman's hand resting gently on a doorframe, warm light. | Static camera. The fingers relax slightly. | The sentence: "Whatever happens online, you can tell me…" |
| 15 | End | 6 s **L** | A warm, softly lit hallway, out of focus, calm. | Static camera, gentle light. | Help card, end card, logo |

About 15 plates and about 2 minutes of footage. At 3–4 tries per shot that's roughly 50–60 generations.

## Vertical versions

- Generate **01, 11 and 13** a second time natively in **9:16** and **4:5**, centred. These are the shots where cropping hurts most.
- The rest can be cropped from 16:9 if the subject is in the middle third, so ask for "centred composition" in every prompt.

## Checklist before a shot goes in the film

- No readable text and no logos (the screens must be blurred).
- No child, no child's face, no child's body.
- The door matches the hero door.
- On locked-off shots, the camera really doesn't move. Otherwise Remotion's overlays will slide off.
- Lighting matches: amber for safety and parents, blue for screens and danger.
