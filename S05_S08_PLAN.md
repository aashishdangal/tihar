# S05_S08_PLAN.md — Plan for the last four scenes (s05–s08)

Draft 2026-11-16, for the owner to approve. Nothing here is in `SCENES.md` yet.
Deadline **Wed 2026-11-18**. Owner rules applied: no scene is cut, every scene is short;
Yamaraj only as a shadow; people only as hands, shadows or soft shapes; old Nepali setting;
Tihar night lights are multicolour LED strings plus diyos; crossfades instead of black.
All captions are drafts: **needs native proofread**.

---

## 1. Story arc, s04 to the end

After the crow (Day 1) and the dog (Day 2), the same old Newari house carries us through
the rest of Tihar. Its cow is garlanded in the morning, and that night (new moon) the house
lights up for Laxmi: diyos and coloured lights, red footprints leading in, Laxmi's eyes
catching the flame. On Day 4 the same courtyard holds a cow-dung Govardhan hill and a
garlanded ox, the family sits at Mha Puja mandalas, and Deusi singing comes from the lane.
The round mandala dissolves into Jamuna's round tika plate, back in Bali Raja's chamber,
now warm with morning light. Jamuna pours a line of oil and water round her brother, breaks
a walnut at the threshold, and puts on the seven-colour tika and a makhamali garland. When
Yamaraj's crowned shadow comes to the door it stops at the oil line. The makhamali does not
wilt, so Yamaraj turns back and leaves. Her diyo flame blurs into the lit valley from
Scene 1: every sister still asks for the same thing. The viewer learns why each day
honours what it honours (crow, dog, cow and Laxmi, Govardhan and self, brother), and the
one story they all lead to.

---

## 2. Scenes

Shared method for every cut below: **the crossfade is baked in at encode time.** Add
`--xfade-in K` to `scripts/encode_frames.py`: the first K frames of scene N+1 are blended
from scene N's last PNG into the new scene's own frames, so N's last frame and N+1's first
frame are the same image and the web needs no new code. Each scene's first and last frames
are also built to match in colour and brightness (PIPELINE §4 checklist).

Render estimates use ~50 s/frame (1920×1080, 192 spp, one RX 9070 XT), plus a 5–7 min
first-frame sync.

### s05_laxmi — Day 3: Gai Tihar + Laxmi Puja · ~180 frames · ~2.5 GPU h

*Revised 2026-11-16 (owner, third pass). The goth/extension idea is dropped (kept only in
`s05_laxmi_v001`–`v005`). s05 is the **unchanged s04 courtyard**: it starts on s04's last frame
(camera looking up at the sky) and the sky is the hinge between beats. Day → night → day says
"the next day has come"; up → night → down brings Laxmi Puja night.*

**One .blend:** `s05_laxmi_v010+`, a copy of `s04_kukur_v019` (dog, hands and the dog's mala
hidden). The cow stands **where the dog sat**.

**Palette:** day = the s04 courtyard light; night = deep indigo, lit only by **many diyos**
(no LED strings, owner 2026-11-16) and the golden glow of Laxmi's footsteps. Marigold is the
only warm accent.

| Frames | Shot |
| --- | --- |
| 1–6 | **In:** s04's last camera, same file: frame 1 = s04 frame 140 (sky through the eaves) |
| 6–30 | Sky time-lapse, camera still: clouds race, day → dusk → night with stars → dawn → day. The next day (Day 3) has come |
| 30–44 | Tilt down to the courtyard centre: the **cow sits where the dog sat**, wearing the owner's marigold mala, red tika with rice on the forehead, chewing |
| 44–66 | Cow close-up, chewing, ear flick. **PAUSE 1** 50–64 (caption गाई तिहार) |
| 66–84 | Tilt back up to the sky: the light goes gold, dusk, then the dark new-moon night |
| 84–100 | Tilt down into the night courtyard, lit only by diyos (rows on the pidhi, steps, sills, hiti, around the courtyard) |
| 100–135 | **Laxmi's footsteps:** small golden footprints appear one by one from the courtyard entrance, each blooming with soft light and a few rising sparks, walking across the brick, up the steps of the portico **पिँढी (pidhi)** to the puja |
| 135–165 | The puja on the pidhi, outside the door: the owner's **Laxmi statue**, stacked sel roti on a leaf plate, owner's marigold malas and loose marigold/makhamali heads, rice, coins, kalash, many diyos. **PAUSE 2** 142–160 (caption लक्ष्मी पूजा) |
| 165–180 | **Out:** push into the main diyo flame in front of Laxmi; bloom and exposure rise to a flat gold fill (cut to s06) |

**Captions** (needs native proofread):
- `दिन ३ · गाई तिहार`: बिहान लक्ष्मीको रूप मानिने गाईलाई माला र टीका लगाएर पुजिन्छ।
- `लक्ष्मी पूजा`: औँसीको अँध्यारो रातमा लक्ष्मीलाई स्वागत गर्न घरघर दियो र बत्ती बालिन्छ।

**scenes.json beats:** `{hold:[50,64], stop:57, drift:4}`, `{hold:[142,160], stop:151, drift:6}`; progress diyo ३.

**Sound:**
```
beds:  wind_loop  [[1,0.15],[34,0.2],[62,0.1],[80,0.2],[112,0.1],[150,0]]
       dawn_loop  [[8,0],[34,0.3],[62,0.3],[78,0]]          (birds, village morning)
       crackle    [[100,0],[136,0.25],[160,0.35]]
       room_drone [[132,0],[144,0.2],[160,0.3]]
cues:  cow_bell 36 (0.4) · cow_moo 48 (0.25) · cow_bell 60 (0.25)
       bell 92 (0.12) · bell 98 (0.1, rate 0.9) · conch 116 (0.3) · bell 138 (0.15)
motion: 0.5
```

**Hero assets:**

| # | Item | Status | Plan | Seen how |
| --- | --- | --- | --- | --- |
| 5.1 | **Cow** | **FOUND** (owner) | VFX Grace "Cattle Cow" (Blender Free Universe giveaway), `blender/assets/s05_cow/`; its EatGrass rig/animation for chewing; scaled to a Nepali cow; sits/stands where the dog sat | Close-up |
| 5.2 | Cow mala + tika | **AI** (owner) + **REUSE** | Owner's marigold mala `blender/assets/s05/ai/a20defe2`, fitted round the neck; tika + rice from `s04_hand_build_tika.py` | Close-up |
| 5.4 | Courtyard | **REUSE** | Copy of `s04_kukur_v019` (dog, hands, dog mala hidden); same set day → night | Whole scene |
| 5.4b | Skies | **REUSE** | `kloofendal_38d_partly_cloudy` (the s04 exit) ↔ dark world + `starmap_2020_16k` (no moon), animated world blend + HDRI rotation for racing clouds | Both sky beats |
| 5.5 | **Many diyos** (no LED strings) | **REUSE** | s00 biswajit diyo scan + v060 flame, instanced along the pidhi, steps, sills, hiti and the courtyard edge; per-instance flicker | Night |
| 5.6 | Laxmi's divine footsteps | **BUILD** | Small footprint decals (vermilion + gold emission) appearing one by one with a bloom and a few rising sparks | Low glide |
| 5.7 | **Laxmi statue** | **AI** (owner) | `blender/assets/s05/ai/laxmi` (brass and paint, seated on a lotus with an arch) | Hero of the puja |
| 5.8 | Puja dressing on the pidhi | **AI** (owner) + **REUSE** | Stacked sel roti `ee786bd9` on leaf plate `25b9c346`, single sel roti `0d3bfe83`, marigold head `83fbe586` and makhamali `9008f69b` (instanced, never low-poly flowers), malas `a20defe2`, s04 brass pots, kalash, rice, coins; fruit only if the owner has a model (none in `refrences/` yet) | Around Laxmi |
| 5.9 | Hero flame | **REUSE** | s00 v060 approved flame | The out push |

### s06_govardhan — Day 4: Govardhan + Goru Puja, Mha Puja, Deusi · 120 frames · ~1.7 GPU h

**Setting:** the s04/s05 courtyard on the next morning, then a room on a clay floor at dusk.
**Palette:** soft green-grey morning (dung, dubo grass, stone) with marigold dots; dusk in
oxblood and ochre with diyo light.

| Frames | Shot |
| --- | --- |
| 1–10 | **In:** gold fill, crossfaded into a macro of one marigold head, out of focus, then sharp by frame 12 |
| 10–48 | Pull back and up: the marigold sits on a knee-high cow-dung Govardhan hill in the courtyard (dubo tufts, flowers, small dung cows, cotton on sticks). The garlanded ox stands soft behind it (the s05 cow, darker, oiled red horns, tika). **PAUSE 1** 34–48 |
| 48–84 | Light falls to dusk; the camera drifts through a doorway onto a row of three Mha Puja mandalas on a clay floor (rings of coloured powder, a diyo and a coiled long wick on each, flowers, fruit). Deusi singing and madal come from the lane; through the door, a lit gate with **silhouettes** only. **PAUSE 2** 84–98 |
| 98–120 | **Out:** camera climbs to a top-down view over the nearest mandala, centred, filling ~70 % of the frame height |

**Captions** (needs native proofread):
- `दिन ४ · गोवर्धन र गोरु पूजा`: कृष्णले गोवर्धन पर्वत उचालेर गाउँ जोगाएको सम्झनामा गोबरको पर्वत र गोरु पुजिन्छ।
- `म्हपूजा · देउसी`: नेवार समुदायले नयाँ वर्षमा आफ्नै शरीरको पूजा गर्छन्; रातभरि देउसी गुन्जिन्छ।

**scenes.json beats:** `{hold:[34,48], stop:41, drift:4}`, `{hold:[84,98], stop:91, drift:3}`; progress diyo ४.

**Sound:**
```
beds:  dawn_loop  [[1,0.25],[48,0.25],[70,0]]
       deusi_loop [[60,0],[84,0.35],[98,0.4],[120,0.3]]   (singing + madal)
       crackle    [[70,0],[90,0.2],[120,0.25]]
cues:  cow_bell 20 (0.35) · cow_moo 40 (0.2, rate 0.8 = ox) · bell 70 (0.1)
motion: 0.45
```

**Hero assets:**

| # | Item | Status | Plan | Seen how |
| --- | --- | --- | --- | --- |
| 6.1 | Govardhan hill | **BUILD** | Sculpted mound; dung shader (fibrous dark brown-green, Poly Haven mud/dirt tinted); instanced dubo tufts; marigold and makhamali heads from the s04 mala nodes; dung figurines as simple blobs | Hero, macro → wide |
| 6.2 | Ox | **REUSE** 5.1 | Darker coat, red-oiled horns, mala, tika | Soft, mid-ground |
| 6.3 | Courtyard, morning | **REUSE** | s04 set, s04 morning light | Background |
| 6.4 | Mha Puja mandalas ×3 | **BUILD** | Radial-ring shader on a disc (powder colours, rice, oil sheen), s00 diyo, coiled wick curve, marigolds; fruit from Poly Haven if any fits, else skip | Hero of pause 2 and the out frame |
| 6.5 | Room floor | **REUSE** | s05 shrine room or a corner of the s02 chamber floor (clay_floor_001) | Under the mandalas |
| 6.6 | Deusi group | **BUILD** (silhouettes) | Camera-invisible cut-out cards or posed MPFB figures, rendered black against a lit gate; no faces | Far, soft, through the door |

### s07_bhaitika — Day 5: Bhai Tika, the payoff · 132 frames · ~1.9 GPU h

**Setting:** **Bali Raja's chamber from s02** (a copy of `s02_legend.blend`), next morning:
warm sun through the jhyal, the panas lit, flowers everywhere. The king still lies on the
palang and Jamuna still kneels beside him (the existing poses). People are seen only as hands
and as shadows on the wall. **Palette:** honey wood, cream silk, the black and red of
Jamuna's haku patasi, the seven tika colours, makhamali purple; the cold door light from s02
returns only for Yamaraj.

| Frames | Shot |
| --- | --- |
| 1–12 | **In:** top-down on Jamuna's round brass thali on the floor, centred and the same size as s06's mandala: seven mounds of tika, makhamali and sayapatri malas, walnut, dubo, rice, a burning diyo, the karuwa beside it |
| 12–48 | Rise and tilt to floor level: a hand in a black sleeve with a red border tips the karuwa, and a thin glossy line of oil and water draws itself round the palang. The king is a soft shape behind it. At 30 the walnut cracks on the threshold stone. **PAUSE 1** 34–48 |
| 48–86 | Turn to the wall behind the bed (the wall s02's shadow rule was built for). The panas casts **shadow-play**: Jamuna's hand raising the tika to the king's forehead. The door light turns cold and **Yamaraj's crowned shadow** climbs in from the doorway, then stops where the oil line glints on the floor. **PAUSE 2** 70–86 |
| 86–112 | Close-up of the makhamali mala: sun shafts sweep across the room as hours pass, and the flowers stay fresh. The crowned shadow bows, shrinks and leaves; the door light warms from blue to gold |
| 112–132 | **Out:** push into the Bhai Tika diyo on the thali. The flame defocuses and blooms to a warm gold fill |

**Captions** (needs native proofread):
- `दिन ५ · भाइटीका`: जमुनाले दाजुको वरिपरि तेल र जलको घेरा कोरिन्, ओखर फोडिन्, सप्तरङ्गी टीका लगाइन्।
- `कथाको अन्त्य`: ‘तेल नसुकुन्जेल, मखमली नओइलाउन्जेल पर्खनुहोस्।’ मखमली ओइलाएन; यमराज बलि राजालाई छाडेर फर्के।

(The old 3/3 caption, "every sister today…", moves to s08 beat 1.)

**scenes.json beats:** `{hold:[34,48], stop:41, drift:4}`, `{hold:[70,86], stop:78, drift:4}`; progress diyo ५.

**Sound:**
```
beds:  room_drone [[1,0.2],[48,0.2],[60,0.35],[86,0.35],[112,0.15]]
       crackle    [[1,0.2],[132,0.35]]
       dawn_loop  [[90,0],[112,0.3],[132,0.2]]   (life returns after Yamaraj leaves)
cues:  oil_pour 16 (0.3) · crack 30 (0.5, synth like peck) · bell 40 (0.1)
       wind_gust 60 (0.35, rate 0.6) · bell 104 (0.15) · bell 112 (0.12, rate 1.1)
motion: 0.4
```

**Hero assets:**

| # | Item | Status | Plan | Seen how |
| --- | --- | --- | --- | --- |
| 7.1 | Chamber, palang, king, Jamuna, panas, door, jhyal, karuwa | **REUSE** | Copy of `s02_legend.blend` (v083), morning sun from the v047 window setup | Whole scene |
| 7.2 | **Thali** (brass plate) | **BUILD** (AI optional) | Lathe profile + brass shader; use the owner's AI thali if it already exists (S02_ASSETS 3.6) | Hero, top-down in |
| 7.3 | Saptarangi tika (7 powder mounds) | **BUILD** | Procedural mounds, matte powder shader | Close-up |
| 7.4 | Makhamali mala | **BUILD** | Variant of `s04_hand_build_mala.py` with globe-amaranth heads (papery purple, `--makhamali #7B2D6E`) | Hero close-up 86–112 |
| 7.5 | Sayapatri mala | **REUSE** | s04 mala | On the thali |
| 7.6 | Walnut, whole + cracked | **BUILD** | Sphere + voronoi wrinkle displacement, split in two | Thali, threshold |
| 7.7 | Oil + water line | **BUILD** | Curve round the palang, animated bevel end, thin glossy oil shader | Floor level |
| 7.8 | Jamuna's hand | **REUSE** | s04 hand + the `S02_Sari` haku patasi sleeve | Pour + shadow |
| 7.9 | Shadow-play cut-outs (hand with tika, king's head in profile) | **BUILD** | Camera-invisible silhouette cards lit by the panas | Wall |
| 7.10 | Yamaraj's crowned shadow | **REUSE** | `S02_Yama_Rig` + `S02_L_DoorSpot` (s02 shadow rule: figure in the doorway, light below the lintel); check it is not in `S02_Removed` | Wall/floor |
| 7.11 | Diyo + flame | **REUSE** | s00 scan + v060 flame | Out shot |

### s08_finale — Glowing valley · 72 frames · ~1.6 GPU h (78 s/frame, s01 measured)

**Setting:** the s01 valley, same night, all lights on (a copy of the latest `s01_hero` .blend).
**Palette:** the s01 night with its multicolour city lights, plus the gold of the incoming flame.

| Frames | Shot |
| --- | --- |
| 1–24 | **In:** the camera at the s01 valley-hold position, focused at 2 m at f/0.9, so the city lights are huge warm bokeh discs filling the frame (crossfaded from s07's gold). Focus pulls to sharp by 24 and the multicolour valley appears |
| 24–72 | Slow crane up and tilt toward the stars and the Himalaya line. **PAUSE 1** 30–44, **PAUSE 2** 58–72 (last frame held) |

**Captions** (needs native proofread):
- `आज पनि`: आज पनि दिदीबहिनीहरू दाजुभाइको लामो आयुका लागि यही प्रार्थना गर्छन्।
- `किन महत्त्वपूर्ण छ`: पशुप्रति माया। प्रकृतिप्रति आभार। परिवारको बन्धन। अँध्यारोमाथि उज्यालो।
- End, live layer: particle title **शुभ तिहार**, buttons फेरि हेर्नुहोस् · श्रेय.

**Sound:** `wind_loop [[1,0.1],[24,0.25],[72,0.2]]`, `deusi_loop [[1,0.2],[40,0.08],[72,0]]`
(distant, fading into wind), cue `bell 30 (0.1, rate 0.7)`, motion 0.5.

**Assets:** all **REUSE** from s01 (PTerrain valley + EOX 2016, GLO30 hills and Himalaya,
OSM-driven lights, starmap). Nothing new.

### New sound files (add to `scripts/build_audio.py` + CREDITS.md)

| Key | Source | Status |
| --- | --- | --- |
| cow_bell, cow_moo | Wikimedia Commons (cowbell, cow moo; CC0/PD preferred) | FIND |
| conch | Commons conch/shankha recording | FIND |
| deusi_loop | Owner records ~20 s of family singing "देउसी रे" with a madal or a hand drum (self-recorded, no licence); Commons as a fallback | OWNER |
| oil_pour | Commons pouring liquid | FIND |
| crack | Generated in `audio.js` (like "peck") | BUILD |

### AI generation list for the owner (start today)

| # | File | Size | Priority | Prompt |
| --- | --- | --- | --- | --- |
| 5.1 | `blender/assets/s05/ai/cow.glb` | ~1.2 m at the hump | **High** (s05 + s06) | "Realistic Nepali zebu cow, small, with a shoulder hump and short horns, white-grey coat, standing calmly, side view, photorealistic, PBR textures, clean mesh, neutral lighting, no collar, no rope" |
| 5.7 | `blender/assets/s05/ai/laxmi.glb` | ~45 cm tall | **High** (s05 out-shot) | "Brass statue of goddess Laxmi seated on a lotus, four arms, gold coins falling from one hand, Nepali Newari temple style, polished aged brass with darker crevices, detailed face with clear eyes, photorealistic, PBR textures" |
| 7.2 | `blender/assets/s07/ai/thali.glb` (optional) | Ø 30 cm | Low (Claude can build it) | "Round engraved brass puja plate (thali) from Nepal, empty, shallow raised rim, worn polished brass, photorealistic, PBR" |
| 5.6 | `blender/assets/s05/ai/rangoli.png` (2D, optional) | 2048² top-down | Low | "Top-down photo of a Tihar rangoli of coloured powder on a brick floor, marigold orange, red, white and green, round lotus pattern, even light, no people" |

Reference photos (comparison only, not assets): Gai Tihar cows, Laxmi Puja footprints and
rangoli, Govardhan dung hills, Mha Puja mandalas, Bhai Tika thali with saptarangi tika.

**Don't use:** `refrences/adasdas/*` (warez source). `refrences/Pro_Particles_v5.4.0` and
`refrences/Simply Cloth v1.5.2 Full` are fine: the owner confirmed (2026-11-16) they were a
giveaway from Blender Universe, a Nepali Blender teacher. The s04 3D Warehouse buildings still need
CREDITS.md lines before they are reused here.

---

## 3. Schedule to Wed 18 Nov

GPU totals: s05 2.2 h + s06 1.7 h + s07 1.9 h + s08 1.6 h = **~7.4 h**, plus ~0.4 h of
syncs and ~1 h of test renders, so **~9 GPU h** for s05–s08. On top of that, s04's full render
(~2 h). Two overnight windows give ~18 h, so the GPU is not the limit; **build time is**.
Only one GPU: while a background render runs, the live MCP Blender stays on Solid view
(it held 12 GB of VRAM on 11-16 and killed a render). Encoding, web work, AI generation and
proofreading all run alongside renders.

| When | Build (live Blender) | GPU | Web / owner |
| --- | --- | --- | --- |
| **Mon 16, now–18:00** | Finish s04 (in progress) | s04 tests | Owner: approve this plan, generate cow + Laxmi (AI), find the sound files, record Deusi |
| **Mon 16, 18:00–23:00** | **s08** (1.5 h: copy s01, new camera, focus pull) → **s07** (4 h) | s04 full render (~2 h); s08 + s07 test frames at 64 spp | Encode s04, add it to scenes.json |
| **Night 16→17** | — | **s07 full (1.9 h) → s08 full (1.6 h)**, s04 re-renders if needed | — |
| **Tue 17, 08:00–15:00** | **s05** (6 h: goth, cow, night courtyard, shrine) | s05 tests ~13:00, render-critic | Encode + integrate s07, s08 (beats, captions, sound); xfade-in in the encoder |
| **Tue 17, 15:00–22:00** | **s06** (4 h) | **s05 full (2.2 h)** once its tests are approved | Progress diyos, शुभ तिहार particle title, credits page |
| **Night 17→18** | — | **s06 full (1.7 h)**, then any fix re-renders | — |
| **Wed 18, 08:00–12:00** | Fixes only | Single-frame or short-range re-renders | Encode s05/s06, final scenes.json, `check_budget.js`, mobile frames, native proofread of all captions |
| **Wed 18, 12:00–cut-off** | — | — | Full scroll QA on desktop + phone, reduced-motion pass, CREDITS → श्रेय, submit |

Render-critic runs after every test render (CLAUDE.md). Its fixes are proposed, never applied
without the owner.

**Fallbacks** (decide at each scene's test-render gate; any can be combined with rendering
every second frame at `fps 12`, which halves the GPU time):

| Scene | If time runs short |
| --- | --- |
| s05 | Skip the goth bay: the cow stands garlanded in the open courtyard, then the time-lapse, footprints and Laxmi (≈120 frames). Worst case: 24-frame slow push on Laxmi + the eye cut |
| s06 | Govardhan hill + ox in one pull-back, then one mandala top-down (72 frames); Deusi as sound only |
| s07 | Keep the thali → oil line → wall shadow → flame (96 frames); skip the time-lapse of hours passing; the walnut is a still prop |
| s08 | Zero render: reuse s01's valley-hold frames (66–114) with a web-side fade from gold, plus the captions and title |
| Web | Lossy WebP (q≈90) for s05–s08 from the start; the particle title falls back to a Mukta fade-in |

---

## 4. Decisions needed from the owner

1. **Cut-off and size:** what hour on 18 Nov is the deadline, and is there a size limit
   for the submission? *Recommend:* plan the last render to finish by 18 Nov 08:00, and use
   lossy q≈90 for s05–s08 (s01 and s02 are already 417 MB and 337 MB lossless).
2. **One house for days 2–4:** reuse the s04 courtyard for s05 (night) and s06 (morning)?
   *Recommend:* yes. It saves about a day and reads as one family's Tihar.
3. **One AI zebu cow** for both the Gai Tihar cow and the Goru Puja ox (darker, oiled horns)?
   *Recommend:* yes, generated today, because s05 and s06 both depend on it.
4. **Laxmi:** an AI brass statue, and the scene exits through the flame reflected in her eye?
   *Recommend:* yes, with a fallback of pushing into the diyo in front of her if the eye
   doesn't read.
5. **Deusi:** sound + far silhouettes at a lit gate, no modelled singers? *Recommend:* yes.
6. **Bhai Tika staging:** the king stays lying (existing s02 pose), the tika is shown as
   hands + shadow-play on the wall, and Yamaraj is the existing crowned shadow?
   *Recommend:* yes. It keeps faces soft, reuses s02, and repeats the shadow motif.
