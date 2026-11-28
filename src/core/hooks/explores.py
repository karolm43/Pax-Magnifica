"""Deklaracja kart eksploracji (80/80) zaimplementowanych w regułach bazowych ``core/``.

Karty eksploracji planet i frontier działają bezpośrednio w ``core/exploration.py``,
``core/exploration_frontier.py``, ``core/relic_fragments.py`` i ``core/planet_stats.py``
(efekty natychmiastowe, attachmenty planet, fragmenty reliktów, żetony wormhole i Mirage).
``ed1``/``ed2``, ``ion`` oraz ``dmz`` są już zarejestrowane w ``hooks/frontier_cards.py``.
Ten moduł rejestruje pozostałe 76 kart, aby raport pokrycia (``hook_coverage``) i
``EffectRegistry`` odzwierciedlały ich faktyczny status ``IMPLEMENTED``.
"""

from __future__ import annotations

from src.core.rules_hooks import declare_core_rule

_CORE_EXPLORES: tuple[str, ...] = (
    # Natychmiastowe — planety (core/exploration.py)
    "aw1", "aw2", "aw3", "aw4",  # Abandoned Warehouses
    "cm1", "cm2", "cm3",  # Core Mine
    "exp1", "exp2", "exp3",  # Expedition
    "fb1", "fb2", "fb3", "fb4",  # Functioning Base
    "frln1", "frln2", "frln3",  # Freelancers
    "lf1", "lf2", "lf3", "lf4",  # Local Fabricators
    "mo1", "mo2", "mo3",  # Mercenary Outfit
    "vfs1", "vfs2", "vfs3",  # Volatile Fuel Source
    # Natychmiastowe — frontier (core/exploration_frontier.py)
    "dv1", "dv2",  # Derelict Vessel
    "dw",  # Dead World
    "ent",  # Entropic Field
    "kel1", "kel2",  # Keleres Ship
    "lc1", "lc2",  # Lost Crew
    "majent",  # Major Entropic Field
    "minent",  # Minor Entropic Field
    "ms1", "ms2",  # Merchant Station
    # Attachmenty planet (core/exploration.py + core/planet_stats.py + core/hooks/relics_events.py)
    "biotic",  # Biotic Research Facility
    "cybernetic",  # Cybernetic Research Facility
    "ds",  # Dyson Sphere
    "ls",  # Lazax Survivors
    "mw",  # Mining World
    "propulsion",  # Propulsion Research Facility
    "pw",  # Paradise World
    "rw",  # Rich World
    "toe",  # Tomb of Emphidia
    "warfare",  # Warfare Research Facility
    # Żetony na planszy (core/exploration.py)
    "gamma",  # Gamma Relay
    "gw",  # Gamma Wormhole
    "mirage",  # Mirage
    # Fragmenty reliktów (core/relic_fragments.py)
    "crf1", "crf2", "crf3", "crf4", "crf5", "crf6", "crf7", "crf8", "crf9",
    "hrf1", "hrf2", "hrf3", "hrf4", "hrf5", "hrf6", "hrf7",
    "irf1", "irf2", "irf3", "irf4", "irf5",
    "urf1", "urf2", "urf3",
)

declare_core_rule(*(f"explores:{cid}" for cid in _CORE_EXPLORES))
