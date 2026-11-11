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
- **s00 → s01 cut:** the web layer swells a glow from the flame to a full-screen warm white
  `#FFF4E0` (`--cream`). Scene 1's first frame must start on that same flat warm white.
- **Pause point:** one per scene; scroll holds while the caption shows.

## Scenes

| # | Scene | Setting and camera | Caption(s) | Out (hidden cut) |
| --- | --- | --- | --- | --- |
| 0 | Enter gate | Black, one diyo flame (loop, not scrolled) | तिहार (Mukta) · "light the wick" control सुरु · sound icon (HUD) | Wick burns, then the diyo flame swells to warm white |
| 1 | Hero | Aerial misty valley at night, pagodas, stars; drifts down. "तिहार" forms from sparks | तिहार · उज्यालोको पर्व — पाँच दिन। एउटी बहिनी, जसले यमराजलाई पर्खन भनिन्। | Dive into low cloud (fog) |
| 2 | Legend | Through a carved palace window into the royal chamber; Bali Raja on his deathbed, crown set aside; Jamuna with a diyo; Yamaraj in the doorway | कथा १/२ — धेरै पहिले, जमुनाका दाजु बलि राजा अन्तिम अवस्थामा थिए। · कथा २/२ — यमराज उनलाई लिन आउँदा, जमुनाले आफ्नो पूजा नसकिएसम्म पर्खन बिन्ती गरिन्। | Crow on the sill lifts off, wing wipes the lens |
| 3 | Day 1 Kaag | Brick rooftops at sunrise; crow lands at a leaf plate of rice and sel roti | दिन १ · काग तिहार — यमराजका दूत कागलाई खुवाइन्छ, ताकि नराम्रो खबर टाढा रहोस्। | Tilt down into dark alley shadow |
| 4 | Day 2 Kukur | Sunlit stone courtyard; dog with marigold mala and red tika; push to eye level | दिन २ · कुकुर तिहार — जीवन र मृत्युको बाटोका पहरेदार कुकुरलाई माला लगाएर सम्मान गरिन्छ। | Dog trots through a dark doorway |
| 5 | Day 3 Gai + Laxmi | Morning cowshed, cow garlanded → sky turns to night → house with red footprints, rangoli, diyos lighting one by one → Laxmi statue being worshipped; **slow push into her eyes** | दिन ३ · गाई तिहार — गाई, लक्ष्मीको रूप। · लक्ष्मी पूजा — लक्ष्मीलाई स्वागत गर्न, र अँध्यारो रातमा आशा जगाउन, दियो बालिन्छ। | **Eye cut:** reflected diyo flame in her eyes grows to fill the frame with gold |
| 6 | Day 4 Govardhan + Deusi | Morning: flower-decorated cow-dung Govardhan hill, garlanded oxen → night: Deusi group with madal at a lit door; household offers a round plate | दिन ४ · गोवर्धन पूजा — कृष्णले गोवर्धन पर्वत उचालेर गोकुलका मानिस र गाईवस्तुलाई रक्षा गरे। · देउसी — घरघरमा देउसी खेलेर सुख, समृद्धि र आशिर्वाद बाँडिन्छ। | Push into the round offering plate → match-cut to Jamuna's tika plate |
| 7 | Day 5 Bhai Tika | Same royal chamber, now warm; oil-and-water circle, seven-colour tika, makhamali garland; Yamaraj turns and fades from the doorway | दिन ५ · भाइटीका १/३ — जमुनाले तेल र जलको घेरा कोरिन्, टीका लगाइन् र मखमलीको माला पहिराइन्। · २/३ — ‘टीका नमेटिउन्जेल, तेल नसुकुन्जेल, फूल नओइलाउन्जेल पर्खनुहोस्।’ यमराज भावुक भए र बलि राजालाई छाडिदिए। · ३/३ — आज पनि हरेक दिदीबहिनी आफ्ना दाजुभाइका लागि यही प्रार्थना गर्छिन्। | Carved palace window opens, white light |
| 8 | Finale | Rise from the window to the same valley as Scene 1, fully glowing; "शुभ तिहार" forms in sparks | किन महत्त्वपूर्ण छ — पशुप्रति माया। प्रकृतिप्रति आभार। परिवारको बन्धन। अँध्यारोमाथि उज्यालो। · buttons फेरि हेर्नुहोस्, श्रेय | End of scroll |

## Progress diyos

Five diyos bottom-right. Diyo N lights during Scene N+2 (Day 1 = Scene 3 … Day 5 = Scene 7).
States: unlit, active (flickering), lit.

## Sound per scene

0 flame crackle · 1 night wind, distant bell · 2 wind, low drone, flame · 3 crows ·
4 courtyard, soft bark · 5 cow bell → evening bells, soft bhajan · 6 oxen bells →
Deusi singing, madal · 7 warm room tone, swell as Yamaraj leaves · 8 distant Deusi
fading into wind. Muted by default.
