# SCENES.md — Story, scenes and transitions

Source of truth for the story. The editable master copy is the "Scene & Flow Bible"
Claude Doc; keep this file in sync when it changes.

## Story

Folk tale of **बलि राजा (King Bali)** and his sister **जमुना (Jamuna)**, a popular
explanation of Bhai Tika. Bali Raja is a king, so his scenes are in a palace.

- Scene 2: Bali Raja lies dying. यमराज comes for him. Jamuna asks him to wait
  until her rituals are done.
- Scenes 3–6: each Tihar day is explained by its own tradition. Captions never
  claim these days are chapters of the tale.
- Scene 7 (climax): Jamuna draws a circle of mustard oil and water, gives tika and
  a makhamali garland, and asks Yamaraj to wait until the tika fades, the oil dries
  and the flowers wilt. Moved, he spares the king.
- Scene 8: today every sister prays the same.
- Credits note: this is one folk retelling; another account tells of Yamaraj
  visiting his sister Yamuna.

## Global rules

- **Light arc:** black → night → lamplit room → dawn → day → evening → lit night → glowing valley.
- **Frame budget:** ~150–250 frames per scene, ~1,800 total, 1920×1080.
- **Mobile:** keep key action in the centre safe zone (middle ~56% width) so frames crop to portrait.
  Exception: s00 puts the diyo on the left third (title on the right); its mobile frames
  use a custom framing (`scripts/mobile_framing.json`).
- **s00 → s01 cut:** a gust blows the diyo out (s00_blowout ends on pure black). Scene 1's first
  frame must start on pure black and rise out of it (stars first, then the valley).
- **Pause point:** one per scene; scroll holds while the caption shows.

## Scenes

| # | Scene | Setting and camera | Caption(s) | Out (hidden cut) |
| --- | --- | --- | --- | --- |
| 0 | Enter gate | Black, one diyo flame (loop, not scrolled) | तिहार (Mukta) · "light the wick" control सुरु · sound icon (HUD) | Wind blows the diyo out (rendered s00_blowout, 3 s: flame tears off, ember, smoke wisp, black); the page's text is carried off by the same gust |
| 1 | Hero | Aerial valley at night, stars, Tihar lights twinkling and changing colour. 0.5 s sky hold → tilt down to the valley → 2 s valley hold (camera locked) → dark cloud sweeps in from the left over the valley and mountains → short push toward it. No title here (तिहार is already shown in Scene 0) | उज्यालोको पर्व — पाँच दिन। एउटी बहिनी, जसले यमराजलाई पर्खन भनिन्। | Push toward the dark cloud; the website fades to black over the last ~12 frames (no close-up cloud render). Scene 2 rises out of the dark |
| 2 | Legend | Overcast late afternoon outside (HDRI), the chamber dark inside, lit only by tuki lamps and a panas (decided 2026-11-14). Starts on black: the camera is pressed against the crow's black feathers; the first scroll pulls back (unzoom) from behind the crow, so it appears on its jacaranda branch with the carved window across the lane in the same view (decided 2026-11-14, replaces the eye close-up); the crow caws twice at the window while the camera pulls back (frames 11-27: head up, beak open, body bows, tail dips) → rack focus to the window and push past the crow; the crow flies off **as sound only** (no flying crow on screen) → push through the jhyal's open middle bay into the chamber. Pause 1: Bali Raja's crown set aside on a stool, sharp in the foreground; behind it, soft, the king lying facing the wall and Jamuna (from behind) sobbing. Pause 2 (changed by owner 2026-11-14): **no Yamaraj shadow in s02**; from frame 90 the camera pans left straight onto the carved door (no pull-back), the leaves swing open on the next morning: a sunrise roof terrace (kausi) with brick rooftops, black water tanks and a pagoda, the leaf plate of rice and sel roti on the parapet; the camera pushes through and rises to standing eye height over the parapet. Sky and light cross-fade from the overcast afternoon to sunrise (frames 92-108). 136 frames (out of black, pull back behind the crow 1-24, rack to the window 24-31, lane 18-38, window 38-66, pause 1 66-90, shadow + move 90-115, pan to the door 90-102, push out onto the kausi 102-136) **Extended to 200 frames (owner 2026-11-16), s03 merged in:** after the door, a wide kausi at frame 136 (brick parapet, clay matka, brass gagri, potted plants, two jacarandas half-screening the Kathmandu valley photo; old Nepali setting, no modern props), then the camera pushes in 136-176 (35→45 mm) to a close-up of the VFX Grace crow eating the sel roti from the owner's leaf tapari on the parapet; pecks at 156 and 180, a bite goes missing at 180; hold 184-200 for the Kaag Tihar caption. | कथा १/२ — धेरै पहिले, जमुनाका दाजु बलि राजा अन्तिम अवस्थामा थिए। · कथा २/२ — यमराज उनलाई लिन आउँदा, जमुनाले आफ्नो पूजा नसकिएसम्म पर्खन बिन्ती गरिन्। | **Out through the door onto the kausi** (owner 2026-11-14): no white cut; the last s02 frame (camera at the threshold, plate on the parapet, rooftops and sunrise beyond) is the first s03 frame. In through the jhyal, out through the door. Crow caw + wings over the cut |
| 3 | Day 1 Kaag | **Merged into s02 (owner 2026-11-16).** No separate s03 file; its caption plays on the s02 final hold (frames 184-200). The next scene opens with a drone-style transition, and the sel roti is gone there. | कागलाई यमराजको दूत मानिन्छ, त्यसैले तिहारको पहिलो दिनमा नराम्रो खबर नआओस् भनेर खुवाइन्छ। (rewritten by the owner, 2026-11-19; the marigold दिन १ · काग तिहार label was dropped on 2026-11-18) | Drone-style rise away from the kausi into s04 (to be designed); the sel roti is gone in that shot |
| 4 | Day 2 Kukur | **Replanned (owner 2026-11-16).** Opens on s02's last frame (crow eating on the kausi). The camera tilts down past the tapari and the parapet and dives into the kausi floor: a short cut-away slice of an old Newari floor (clay/brick topping, mud, wooden planks, dalin beams) rushes past, then a **smooth crossfade (no black)** into s04 proper: down through the ground-floor ceiling beams into a dim passage (dalan) with morning sun from the courtyard door. The dog (Nubis, tan, Malinois-like) **sits, excited**: panting, tail wagging, ears and head moving. **Two scroll beats:** (1) a human hand puts a marigold mala round its neck, (2) the hand presses a red tika on its forehead (face of the person never shown). Hold for the caption, then the dog trots into a dark inner doorway (cut into s05). ~125 frames. Dive frames render from the s02 file (camera carried past 200); the rest from s04_kukur.blend; the crossfade is baked into the encoded frames. | दिन २ · कुकुर तिहार — जीवन र मृत्युको बाटोका पहरेदार कुकुरलाई माला लगाएर सम्मान गरिन्छ। | In: down through the floor (wood slice) + crossfade. Out: dog trots through a dark doorway |
| 5 | Day 3 Gai + Laxmi | Morning cowshed, cow garlanded → sky turns to night → house with red footprints, rangoli, diyos lighting one by one → Laxmi statue being worshipped; **slow push into her eyes** | दिन ३ · गाई तिहार — गाई, लक्ष्मीको रूप। · लक्ष्मी पूजा — लक्ष्मीलाई स्वागत गर्न, र अँध्यारो रातमा आशा जगाउन, दियो बालिन्छ। | **Eye cut:** reflected diyo flame in her eyes grows to fill the frame with gold |
| 6 | Day 4 Govardhan + Deusi | Morning: flower-decorated cow-dung Govardhan hill, garlanded oxen → night: Deusi group with madal at a lit door; household offers a round plate | दिन ४ · गोवर्धन पूजा — कृष्णले गोवर्धन पर्वत उचालेर गोकुलका मानिस र गाईवस्तुलाई रक्षा गरे। · देउसी — घरघरमा देउसी खेलेर सुख, समृद्धि र आशिर्वाद बाँडिन्छ। | Push into the round offering plate → match-cut to Jamuna's tika plate |
| 7 | Day 5 Bhai Tika | Same royal chamber, now warm; oil-and-water circle, seven-colour tika, makhamali garland; Yamaraj turns and fades from the doorway | दिन ५ · भाइटीका १/३ — जमुनाले तेल र जलको घेरा कोरिन्, टीका लगाइन् र मखमलीको माला पहिराइन्। · २/३ — ‘टीका नमेटिउन्जेल, तेल नसुकुन्जेल, फूल नओइलाउन्जेल पर्खनुहोस्।’ यमराज भावुक भए र बलि राजालाई छाडिदिए। · ३/३ — आज पनि हरेक दिदीबहिनी आफ्ना दाजुभाइका लागि यही प्रार्थना गर्छिन्। | Carved palace window opens, white light |
| 8 | Finale | Rise from the window to the same valley as Scene 1, fully glowing; "शुभ तिहार" forms in sparks | किन महत्त्वपूर्ण छ — पशुप्रति माया। प्रकृतिप्रति आभार। परिवारको बन्धन। अँध्यारोमाथि उज्यालो। · buttons फेरि हेर्नुहोस्, श्रेय | End of scroll |

## Progress diyos

Five diyos bottom-right. Diyo N lights during Scene N+2 (Day 1 = Scene 3 … Day 5 = Scene 7).
States: unlit, active (flickering), lit.

## Sound per scene

Built 2026-11-16, reworked with the owner 2026-11-19. Mixes live in `web/src/scenes.json` →
`sound` (beds = loops whose gain follows the frame, cues = one-shots fired when scrolling forward
past a frame, motion = wind that follows scroll speed, i.e. every camera move). Engine:
`web/src/audio.js`. Files: `web/public/audio/`, built from the originals in
`refrences/audio_src/` by `scripts/build_audio.py` (each block there is guarded, so a partial
source folder rebuilds what it can); credits in CREDITS.md. Sound is on by default; the first
click/tap/key unlocks audio. A source whose file is missing is skipped, never an error.

- s00 gate: `flame_loop`, at 0.12 — barely there. **A diyo is an oil wick: it does not crackle
  and is nearly silent** (owner, 2026-11-19). The campfire it is built from is divided by its own
  envelope so no pop survives, then low-passed to 900 Hz; what is left is air moving, not
  burning (crest 9.6 dB, where a fire is 18-25). The generated `crackle` is now unused
  everywhere — every lamp in the site uses this flutter, quietly.
  **The breath is heard as well as seen** (owner-supplied recordings, 2026-11-19): holding सुरु
  plays `breath_in` while the boy fills his lungs, and the blow cuts it off, so a long hold and a
  quick tap both sound like one breath. **Blow-out: a person blowing it out, not the wind** —
  `blow`, a recording of a candle being blown out, trimmed to the breath itself. Both replaced
  generated versions, which have been removed. The breath is played by the control
  (`web/src/breath.js` → `playBreath`/`stopBreath` in `audio.js`), not by a frame cue, because it
  belongs to the gesture rather than to the blow-out's clock.
  *Note: the scene table above still describes this as wind; the sound is now a breath.*
- s01: **the valley underneath, not the wind** (owner, 2026-11-19). The wind was too loud and too
  bare, so it steps back to 0.1 (motion wind 0.55 → 0.22) and `city_night` comes up under it:
  traffic, a far street, four horns and one child, all low-passed to 700 Hz — *recognisable, not
  clearly audible*. The bed is **87 s long** so a pass of the scene never reaches its seam. One
  aeroplane crosses at frame 34 and a child is heard at 104. The two distant bells were dropped —
  there is no bell in the scene and it read as a cliché over an aerial shot.
- s02: no wind. **The city does not stop at the cut** (owner, 2026-11-19): `city_night` follows the
  camera down into the lane (0.42), is muffled to 0.1 by the chamber walls, and comes back when
  the door opens onto the kausi (0.34). Lane: house-crow caws at 12 and 21; wings at 30 as it leaves; chamber: low singing-bowl
  drone + the lamp flutter (0.08), soft bell at 80. **The room is not empty any more** (owner,
  2026-11-19): Jamuna sobs at 67 and 84 and Bali Raja coughs at 75, with one small dry cough at
  89 — the last of him before the camera pans away. Both are owner-supplied recordings, pitched
  down and low-passed hard (centroids 3.8/3.6 kHz → 885/949 Hz) so they sit behind cloth and
  distance: rule 6 applies to the mix as much as to the frame. The drone ducks from 0.3 to 0.18
  across the pause so they are the loudest things in the room, and the valley outside drops to
  0.07 because we are indoors. door creak at 92, heavier than before.
  **The door and the sunrise open up** (owner, 2026-11-19): the drone lets go by 102 and the
  morning arrives as a change in the sound and not only in the picture. The dawn chorus first
  carried this alone and was too heavy — it is a South Indian recording, too many birds for a
  Kathmandu kausi — so it was cut to roughly a third (0.64 → 0.24) and now sits under a
  **शंख from across the rooftops at 113** and a **rooster at 124, answered further off at
  168**. **Nothing from outside is heard until the camera is through the doorway** (owner,
  2026-11-19): the leaves open at 92 but the valley holds at its indoor level until 108 and the
  birds stay at zero until then, both arriving over 108-120 as we cross the threshold. The two
  soft pecks moved from 110/120 to 118/128 for the same reason — the crow is outside as well. Both are low-passed hard (554 Hz and 1.3 kHz): they are somewhere else in the town,
  never on the terrace. Beak pecks at 118/128 (soft) and 156/180. The closing caw at 194 was removed (owner, 2026-11-19): the scene ends on the morning, not on the bird.
- s04: a South Asian village morning (`village_morning`: dogs far off, birds, crickets) rather
  than a generic bird bed. **The dog does not bark** (owner, 2026-11-19): `dog_breath` (an owner-supplied
  panting take, cut to five whole breaths so the loop never lands mid-breath) comes up as the
  camera reaches it at 22 and **is gone by 44, when its ears come up** — the dog is excited when
  we arrive and goes still as the hands approach. (`scripts/s04_animate.py:148` keys the ears up
  to 44, then flattening to -0.4 by 52 as the mala passes.) Panting as a constant bed under the
  ceremony did not work (owner, 2026-11-19): it read as agitated under a tender moment and, held
  that long, started to be heard as a loop. After 44 the tail thumps carry the animal instead.
  The bed is also marked **`onlyMoving`**: it follows the scroll and goes quiet whenever the
  picture is still, so a reader who stops is left with the village morning alone. Any bed can
  take that flag; nothing that is meant to be background should. **the mala lands at 60** (generated: nine dry flower-head rustles over a
  soft settle — a garland on fur is not an impact), and four `tail_thump`s at 40/45/70/96/100 at
  varied rates. Bells at 62 and 78 mark the mala and the tika.
- s05: `cow_bell` at 18 and 44 in the goth — one animal shifting, not a herd; the cow moos
  twice, long then short, from two separate owner-supplied takes (owner, 2026-11-19 — **frames
  provisional at 48 and 58 until the animation's keyframes are confirmed**). Dawn birds cut to a third (0.35 → 0.12, the same
  too-busy Sakleshpur chorus as in s02) and gone by 84,
  then the house: the lamp flutter **builds in five steps as the diyos light** (owner,
  2026-11-19), topping out at 0.18 — a row of diyos, not a fire, and a `harmonium_drone` (one chord an octave down, looped) sits under it from 88 —
  worship elsewhere in the house, never a tune. Bell at 57 only — **the two bells over the statue were removed** (owner,
  2026-11-19: `Bell-ring.flac` is thin and bright and read as a bicycle bell). In their place
  **Laxmi's footsteps**, ten of them across 100-135, each nearer and each a different pitch,
  walking the brick and up the pidhi steps; then **`divine` at 136** — a struck bowl built from
  inharmonic partials with a 2.2 s reverse swell, tuned to C to match the harmonium, which
  itself lifts from 0.15 to 0.24 as she arrives. Generated rather than sampled: everything else
  here is a real recording, and a synth sparkle would have been the one fake thing in the site.
- s06: a courtyard of lamps at 0.12-0.16. Deusi and madal are **AI-generated by the owner** (2026-11-19) — no free recording of
  either exists. `deusi_loop` and `madal_loop` are already wired and stay silent until the files
  land in `web/public/audio/`. Brief, chant script and prompts: `S06_DEUSI_AUDIO.md`.
- **The wind** (owner, 2026-11-19, three times). It was too loud and it whistled, and the scroll
  wind — the layer whose level follows how fast you scroll — now exists in **scene 1 and the
  finale only** (0.22 each). It is off in s02, s04, s05, s06 and s07, where it used to run at
  0.4-0.7; s02 was the worst in the site at 0.7 over a bed reaching 0.3. The whistle is a
  property of the recording: 88 % of its energy sits in 420-1800 Hz, and the send used to pitch
  it *up* to 1.15, so it now plays at 0.8 and is banded to 140-1500 Hz (`web/src/audio.js`).
  Level was the main fix; pitch and band changed the character. The finale places its mix from
  the story tick rather than from ScrollTrigger, so its scroll wind falls away when you stop
  scrolling instead of holding at whatever level it had reached.
  **There is now no wind at all outside scene 1 and the finale** (owner, 2026-11-19): the quiet
  still-wind beds were removed from s02, s04, s05 and s06 as well, so `wind_loop` appears in
  exactly two mixes. What those scenes used it for is carried by what is already there — s02's
  lane and kausi by `city_night` and the dawn birds, s04's closing doorway by the village
  morning falling away, s05's goth by the dawn bed.

- s07: warm room tone, the lamp flutter rising to 0.18, dawn at the end. **A real brass ghanta**
  at 54, 210 and 244 (owner, 2026-11-19), replacing Bell-ring.flac: 3.4 kHz against its 7.3 kHz
  and a 5 s ring-out against 2.6 s. The tail is what separates a puja bell from a ping, so the
  strike's tail is kept whole.
- s08 finale: **fireworks only, no Deusi** (owner, 2026-11-19). `fw_far_loop` and five
  `fw_burst`es, both low-passed hard — across a valley only the thud arrives — over the wind that
  opened the site. The finale is drawn by the browser rather than played as frames, so its mix is
  placed by scroll progress (0-100 standing in for the frame number) from `web/src/story.js`;
  while it is on screen the frame scenes stop placing the mix so the two do not fight.
