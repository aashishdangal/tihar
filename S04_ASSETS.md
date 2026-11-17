# S04_ASSETS.md — Everything Scene 4 (Day 2, Kukur Tihar) needs

Scene 4 starts from s03's dark alley fill and opens into a **sunlit stone courtyard**
(Newari chowk). A **dog wearing a marigold mala and a red tika** sits or stands in the light;
the camera **pushes down to the dog's eye level**. Pause on the dog. Exit: the **dog trots
through a dark doorway**, which fills the frame (hidden cut into s05).
Caption: दिन २ · कुकुर तिहार — जीवन र मृत्युको बाटोका पहरेदार कुकुरलाई माला लगाएर सम्मान गरिन्छ।
Sound: courtyard ambience, one soft bark. Short scene, ~100–120 frames. See `SCENES.md` row 4.

Status tags as in `S02_ASSETS.md`: **FOUND**, **AI** (owner generates), **AI?**, **BUILD**
(Claude makes it in Blender), **REUSE**.
AI files go in `blender/assets/s04/ai/<name>.glb`. Every AI asset gets a `CREDITS.md` line.

---

## 1. Courtyard

| # | Item | Status | Plan | Seen how |
| --- | --- | --- | --- | --- |
| 1.1 | Stone/brick paved courtyard floor | **FOUND** | Poly Haven cobblestone / brick paving (CC0) | Foreground, all scene |
| 1.2 | Surrounding Newari house fronts (brick, carved windows, sloping eaves) | **BUILD + REUSE** | Boxes + brick; reuse the s02 jhyal scan and AI window as dressing | Mid/background, partly in shade |
| 1.3 | **Dark doorway** the dog runs through (exit fill) | **REUSE / AI?** | Reuse the s02 AI carved door frame, leaves open, black inside | End: fills the frame |
| 1.4 | Small chaitya / stone shrine in the courtyard centre | **FOUND / AI?** | Sketchfab CC BY Newari chaitya scans exist; check. AI if none | Mid-ground, gives place |
| 1.5 | Dhunge dhara / stone water tap or a well (optional) | **AI?** | Nice-to-have | Background |
| 1.6 | Tihar dressing: marigold strings on doors, a diyo or two, rangoli smear | **REUSE / BUILD** | Marigold from s02/s03; strings instanced on curves | Background detail |
| 1.7 | Pigeons on the ground / roof edge | **FOUND?** | Free pigeon model if one exists; skip if not | Small, background life |
| 1.8 | Morning sun light | **BUILD** | Sun lamp + Poly Haven clear-sky HDRI (CC0) | Hard shadows across the stone |

## 2. The dog (hero)

| # | Item | Status | Plan | Seen how |
| --- | --- | --- | --- | --- |
| 2.1 | **Nepali street dog** (brown/tan, short coat, curled tail), realistic, rigged or at least posable | **AI** (or FOUND?) | `ASSETS.md` lists WildMesh "Realistic Wolf 2.0" demo to retexture; check licence first. An AI dog will likely look closer to a real Nepali kukur. Needs fur (Claude adds hair particles if mesh is clean) | **Eye-level close-up**, hero |
| 2.2 | Dog **trotting** pose / animation | **AI?** / **BUILD** | If the model has a rig, Claude keys a short trot. Otherwise a second AI mesh in mid-trot + motion blur | Last 20–30 frames, from behind |
| 2.3 | **Marigold mala** around the neck | **BUILD** | Instanced marigold heads on a curve around the neck | Close-up |
| 2.4 | **Red tika** on the forehead (with rice grains) | **BUILD** | Decal/texture paint + a few rice grains | Close-up, sharp |
| 2.5 | Hero marigold flower (for mala instances) | **REUSE / AI?** | Same marigold as s02/s03 (`ASSETS.md`: Sketchfab "Marigold", CC BY) | Many instances |
| 2.6 | Food offering in front of the dog: steel bowl or leaf plate with meat/egg/sel roti | **REUSE / FOUND** | Reuse s03 leaf plate + sel roti; or Poly Haven metal bowl | Foreground, soft |

## 3. Sound

| # | Item | Status | Plan |
| --- | --- | --- | --- |
| 3.1 | One soft dog bark (not aggressive) | **FOUND** | Freesound CC0 |
| 3.2 | Courtyard ambience: pigeons, distant voices, a bell, birds | **FOUND** | Freesound CC0 / CC BY (credit) |
| 3.3 | Paw steps on stone (trot out) | **FOUND** | Freesound CC0 |

---

## AI generation list for the owner

| # | File | Size | Priority | Prompt |
| --- | --- | --- | --- | --- |
| 2.1 | `s04_dog.glb` | ~0.55 m at shoulder, ~0.9 m long | **High: eye-level close-up** | "Realistic Nepali street dog (kukur), medium size, short tan-brown coat with lighter chest, pointed ears, curled tail, sitting calmly, photorealistic, PBR textures, clean mesh, neutral lighting" — sitting pose, no collar (Claude adds the mala) |
| 2.2 | `s04_dog_trot.glb` (only if 2.1 has no rig) | same | Mid | "Same dog in mid-trot, side view, one front leg raised" — use the same image/seed as 2.1 so it matches |
| 1.4 | `s04_chaitya.glb` (optional) | ~1.5 m tall | Low | "Small stone Buddhist chaitya from a Kathmandu Newari courtyard, weathered grey stone with moss, carved niches, realistic, PBR" |

**Tip:** Generators handle fur badly. Ask for a short-coated dog; Claude can add a light hair
layer in Blender. If the tool supports auto-rigging (e.g. Meshy / Tripo animal rig), export
rigged — it saves the trot.

**Reference photos to save:** `blender/assets/s04/refs/` — Kukur Tihar dogs with mala and tika
(search "Kukur Tihar dog"), Patan / Bhaktapur courtyards in morning sun, a trotting street dog.

**Priority if time is short:** 2.1 dog (the whole scene rests on it), then 2.2 trot.
Everything else is reuse, Poly Haven, or Blender-built.
