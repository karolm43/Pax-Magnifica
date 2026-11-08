"""Jednostki neutralne (R_neutral_units, RULES.md 50).

Neutralnych NIE prowadzi żaden gracz: „Neutral units are considered to be another player's
ships ... However, there is no neutral player". Silnik trzyma je w ``space_units`` /
``planet_units`` pod stałym kluczem :data:`NEUTRAL_PLAYER_ID`, a nie w ``state.players``.
Walka widzi w nich zwykłego przeciwnika (statki / siły naziemne innego „gracza"), ale
neutralni nigdy nie przejmują kontroli nad planetą (patrz ``control.recompute_from_units``).
"""

from __future__ import annotations

NEUTRAL_PLAYER_ID = "neutral"
