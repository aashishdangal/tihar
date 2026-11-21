# S06 — Deusi and madal (AI-generated)

Scene 6 needs two sounds that **do not exist under any free licence**. Wikimedia Commons has
nothing for *deusi*, *bhailo* or *madal*; the three results on archive.org are a copyright-marked
upload, a CC **NC-ND** track (unusable), and a 48-minute "Deusi Bhailo" tagged Public Domain
Mark by an anonymous account — re-uploaded commercial music with the wrong tag. Rule 4 rules all
three out. So scene 6 is generated, decided by the owner on 2026-11-19.

Everything below is already wired. Drop the two finished files into `web/public/audio/` and the
scene plays them — no code change. Until then they are simply skipped and s06 stays as it is
(lamp crackle + wind), because a missing source is not an error in `web/src/audio.js`.

| File to produce | Where it goes | What it is |
| --- | --- | --- |
| `deusi_loop.mp3` | `web/public/audio/` | A group of young men chanting देउसी रे, outdoors, some distance off |
| `madal_loop.mp3` | `web/public/audio/` | The madal that keeps them in time |

---

## 1. Technical specification (both files)

These are not stylistic preferences — the engine depends on them.

| Property | Value | Why |
| --- | --- | --- |
| Format | MP3, **mono**, 64 kbps, 44.1 kHz | Matches the other nine files; mono halves the size and plays identically everywhere |
| Length | **8–20 s** | It loops under a 72-frame scene. Longer wastes budget, shorter repeats audibly |
| Loop | **Seamless** — the end must meet the start | It plays on a loop node; any click or gap is heard every few seconds |
| Level | RMS about **−22 dB**, peak **−1 dB**, no clipping | Everything else in the site is levelled to this |
| Tail | **No fade-out, no reverb tail at the end** | A tail that does not reach the start is a hole in the loop |
| Tempo | Steady, no ritardando | The loop point has to land on the beat |

If the generator cannot loop, make the tail overlap the head yourself:

```
python scripts/build_audio.py    # put the raw file in refrences/audio_src/ first
```

Add a block to `scripts/build_audio.py` next to the others — `loop(x, 2.0)` crossfades the last
two seconds into the first and `level(x, -22)` sets the loudness. Tell me and I will add it.

---

## 2. The chant — what the voices actually say

Deusi is **call and response**: one leader (भन्ने) sings the line, the whole group (भन्नेहरू)
answers **देउसी रे**. Keep that shape; a solo voice is not Deusi.

| Leader | Group |
| --- | --- |
| भन भन भनौँ भन्या | देउसी रे |
| हामी पनि जान्या | देउसी रे |
| रातभरि नसुत्न्या | देउसी रे |
| यो घरका मालिक | देउसी रे |
| धनले भरिऊन् भन्या | देउसी रे |
| बलि राजाले पठाको | देउसी रे |
| हामी सबै आको | देउसी रे |

Transliteration for a generator that cannot read Devanagari:

```
bhana bhana bhanau bhanya        — DEUSI RE
haami pani jaanya                — DEUSI RE
raat-bhari nasutnya              — DEUSI RE
yo gharkaa maalik                — DEUSI RE
dhanle bhariun bhanya            — DEUSI RE
bali raajaale pathaako           — DEUSI RE
haami sabai aako                 — DEUSI RE
```

The sixth and seventh lines ("sent by Bali Raja, we have all come") tie the chant back to the
legend in scene 2. That is the reason this scene exists, so keep them if you keep anything.

**Nothing of this appears on screen** — rule 1 is about visible text, and these are voices only.
No subtitle, no caption. The existing s06 caption stands as it is.

---

## 3. Prompts

### 3.1 The chant — for a music generator (Suno, Udio, or similar)

> Nepali folk festival street chant, call and response. A single male leader sings a short
> phrase and a group of six to ten young men answer in unison "deusi re". Recorded outdoors at
> night in a courtyard, a little distance from the microphone. Raw, unpolished, slightly ragged
> unison — a neighbourhood group, not a choir. Only voices and a madal hand drum. Steady tempo
> around 100 BPM, no key change, no build, no ending — it should sound like the middle of
> something that has been going on for an hour. Lyrics: [paste the transliteration above]

**Negative prompt / exclude**: studio reverb, autotune, harmony stacking, western drum kit,
guitar, synth, bass guitar, tabla, applause, fade in, fade out, solo singer, female vocals,
Bollywood production, orchestral strings.

### 3.2 The madal — for a sound-effect generator (ElevenLabs SFX or similar)

> A Nepali madal hand drum played alone, a steady folk rhythm, dry and close, recorded outdoors
> with no reverb. Two heads: a low round thump on one side and a sharp high slap on the other,
> alternating in a repeating cycle. Human timing, not quantised. 12 seconds, continuous, no
> intro and no ending.

If that generator gives you something that sounds like a tabla or a bongo, say **"madal, Nepali
folk drum, dull low head and bright small head, played with both palms, outdoors"** and try
again. A madal is dry and woody; a tabla rings and bends in pitch. The bend is the giveaway.

### 3.3 If you generate one file instead of two

A single file with voices and madal together works — name it `deusi_loop.mp3` and I will drop
`madal_loop` from the mix. Two files are better only because the mix can bring the drum in
before the voices as the camera finds the group.

---

## 4. How it is mixed (already in `web/src/scenes.json`)

```
madal_loop   frame  1 → 0.18    frame 24 → 0.34    frame 72 → 0.40
deusi_loop   frame  1 → 0.12    frame 24 → 0.30    frame 72 → 0.38
```

The drum leads slightly and both rise as you scroll into the group — you hear them before you
are among them. Scene 8 does **not** carry the Deusi over (owner, 2026-11-19): the finale is
fireworks and wind only.

---

## 5. Licensing — do this before the file goes in

AI-generated audio is not automatically free to use. Before committing either file:

1. Check the generator's terms for whether output may be used and published. Free tiers of some
   tools grant **non-commercial use only** — fine here (this is a school project, non-commercial),
   but it must be written down.
2. Add a row to `CREDITS.md`: the tool, the version or plan, the date, and the exact prompt used.
3. If the tool's terms are unclear, do not use it. Record your own voices instead — that is
   unambiguous, free, and more authentic than anything a generator will produce.

A row is already waiting to be filled in; it is marked **TBC** until you say which tool you used.
