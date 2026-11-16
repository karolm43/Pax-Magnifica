# Dźwięki walki — źródła i licencje

Wszystkie pliki w tym katalogu pochodzą z materiałów na licencji **CC0 1.0 (domena publiczna)**,
przycięte, przetworzone (wysokość, filtry, wyciszenia) i znormalizowane do szczytu −1 dB, mono, Ogg Vorbis.
`<zdarzenie>-<n>.ogg` = n-ty wariant zdarzenia (front losuje wariant przy każdym odtworzeniu,
`frontend/src/domains/battle/battleSound.ts`). Brak plików zdarzenia = awaryjna synteza WebAudio.

| Zdarzenie | Źródło |
|---|---|
| laser, plasma, flak, sunfire, impact, explosion (1–5), explosionHeavy-1, sustain, fleetEnter, arrive, arriveHeavy, retreat, missile (2–3), dropPod, assaultCannon (wybuch) | Kenney — *Sci-fi Sounds* (kenney.nl/assets/sci-fi-sounds) |
| armorHit, bulletHit, bodyFall, mechCollapse, podLand | Kenney — *Impact Sounds* (kenney.nl/assets/impact-sounds) |
| diceThrow, diceClack | Kenney — *Casino Audio* (kenney.nl/assets/casino-audio) |
| retreatHorn, assaultCannon (ładowanie) | Kenney — *Digital Audio* (kenney.nl/assets/digital-audio) |
| rifle, rifleShot | *The Free Firearm Sound Library* (opengameart.org/content/the-free-firearm-sound-library) — AK-47, PPSh, Carl Gustav M45, AR-15, SKS |
| mechCannon (1–5), groundBlast (3–4) | *25 CC0 bang / firework SFX* (opengameart.org/content/25-cc0-bang-firework-sfx) |
| mechCannon-6 | *Cannon fire* (opengameart.org/content/cannon-fire) |
| groundBlast-2, explosionHeavy-3 | *Cannon hit* (opengameart.org/content/cannon-hit) |
| groundBlast-1 | *Explosion* (opengameart.org/content/explosion-0) |
| explosionHeavy-2 | *Chunky Explosion* (opengameart.org/content/chunky-explosion) |
| explosion (6–7), missile-1, warSunEnter | *50 CC0 Sci-Fi SFX* (opengameart.org/content/50-cc0-sci-fi-sfx) |
| infantryDeath (1–5) | *grunts of male death and pain* (opengameart.org/content/grunts-male-death-and-pain) |
| infantryDeath (6–9) | *Death sounds* (opengameart.org/content/death-sounds-0) |
| mechPowerDown | *Machine shutting down* (opengameart.org/content/machine-shutting-down) |
| mechStep | *Mech Stomp / Step Sound* (opengameart.org/content/mech-stomp-step-sound) |

Podmiana: wystarczy wrzucić własny plik o tej samej nazwie zdarzenia (np. `rifle-5.ogg`) —
backend (`GET /battle/sounds`) wylistuje go automatycznie.
