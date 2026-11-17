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
| 3 | Day 1 Kaag | **Merged into s02 (owner 2026-11-16).** No separate s03 file; its caption plays on the s02 final hold (frames 184-200). The next scene opens with a drone-style transition, and the sel roti is gone there. | दिन १ · काग तिहार — यमराजका दूत कागलाई खुवाइन्छ, ताकि नराम्रो खबर टाढा रहोस्। | Drone-style rise away from the kausi into s04 (to be designed); the sel roti is gone in that shot |
| 4 | Day 2 Kukur | **Replanned (owner 2026-11-16).** Opens on s02's last frame (crow eating on the kausi). The camera tilts down past the tapari and the parapet and dives into the kausi floor: a short cut-away slice of an old Newari floor (clay/brick topping, mud, wooden planks, dalin beams) rushes past, then a **smooth crossfade (no black)** into s04 proper: down through the ground-floor ceiling beams into a dim passage (dalan) with morning sun from the courtyard door. The dog (Nubis, tan, Malinois-like) **sits, excited**: panting, tail wagging, ears and head moving. **Two scroll beats:** (1) a human hand puts a marigold mala round its neck, (2) the hand presses a red tika on its forehead (face of the person never shown). Hold for the caption, then the dog trots into a dark inner doorway (cut into s05). ~125 frames. Dive frames render from the s02 file (camera carried past 200); the rest from s04_kukur.blend; the crossfade is baked into the encoded frames. | दिन २ · कुकुर तिहार — जीवन र मृत्युको बाटोका पहरेदार कुकुरलाई माला लगाएर सम्मान गरिन्छ। | In: down through the floor (wood slice) + crossfade. Out: dog trots through a dark doorway |
| 5 | Day 3 Gai + Laxmi | Morning cowshed, cow garlanded → sky turns to night → house with red footprints, rangoli, diyos lighting one by one → Laxmi statue being worshipped; **slow push into her eyes** | दिन ३ · गाई तिहार — गाई, लक्ष्मीको रूप। · लक्ष्मी पूजा — लक्ष्मीलाई स्वागत गर्न, र अँध्यारो रातमा आशा जगाउन, दियो बालिन्छ। | **Eye cut:** reflected diyo flame in her eyes grows to fill the frame with gold |
| 6 | Day 4 Govardhan + Deusi | Morning: flower-decorated cow-dung Govardhan hill, garlanded oxen → night: Deusi group with madal at a lit door; household offers a round plate | दिन ४ · गोवर्धन पूजा — कृष्णले गोवर्धन पर्वत उचालेर गोकुलका मानिस र गाईवस्तुलाई रक्षा गरे। · देउसी — घरघरमा देउसी खेलेर सुख, समृद्धि र आशिर्वाद बाँडिन्छ। | Push into the round offering plate → match-cut to Jamuna's tika plate |
| 7 | Day 5 Bhai Tika | Same royal chamber, now warm; oil-and-water circle, seven-colour tika, makhamali garland; Yamaraj turns and fades from the doorway | दिन ५ · भाइटीका १/३ — जमुनाले तेल र जलको घेरा कोरिन्, टीका लगाइन् र मखमलीको माला पहिराइन्। · २/३ — ‘टीका नमेटिउन्जेल, तेल नसुकुन्जेल, फूल नओइलाउन्जेल पर्खनुहोस्।’ यमराज भावुक भए र बलि राजालाई छाडिदिए। · ३/३ — आज पनि हरेक दिदीबहिनी आफ्ना दाजुभाइका लागि यही प्रार्थना गर्छिन्। | Carved palace window opens, white light |
| 8 | Finale | Rise from the window to the same valley as Scene 1, fully glowing; "शुभ तिहार" forms in sparks | किन महत्त्वपूर्ण छ — पशुप्रति माया। प्रकृतिप्रति आभार। परिवारको बन्धन। अँध्यारोमाथि उज्यालो। · buttons फेरि हेर्नुहोस्, श्रेय | End of scroll |

## Progress diyos

Five diyos bottom-right. Diyo N lights during Scene N+2 (Day 1 = Scene 3 … Day 5 = Scene 7).
States: unlit, active (flickering), lit.

## Sound per scene

Built 2026-11-16. Mixes live in `web/src/scenes.json` → `sound` (beds = loops whose gain follows
the frame, cues = one-shots fired when scrolling forward past a frame, motion = wind that follows
scroll speed, i.e. every camera move). Engine: `web/src/audio.js`. Files: `web/public/audio/`,
built from Commons originals in `refrences/audio_src/` by `scripts/build_audio.py`; credits in
CREDITS.md. Sound is on by default; the first click/tap/key unlocks audio.

- s00 gate: diyo crackle (generated). Blow-out: wind gust, crackle dies with the flame.
- s01: night wind, distant bell at 60 and 120, motion wind on the flight.
- s02: lane wind; house-crow caws at 12 and 21; wings (generated) at 30 as it leaves; chamber:
  low singing-bowl drone + lamp crackle, soft bell at 80; door creak at 92; kausi: dawn birds;
  wind rises on the 136-176 push-in; beak pecks at 110/120 (soft) and 156/180; one soft caw at 194.
- Later scenes (plan): 4 courtyard, soft bark · 5 cow bell → evening bells, soft bhajan · 6 oxen
  bells → Deusi singing, madal · 7 warm room tone · 8 distant Deusi fading into wind.
