"""Autorytatywna klasyfikacja pól ``PlayerState`` na JAWNE i TAJNE (R2).

To JEDYNE źródło prawdy o tym, które pola gracza są publiczne (``Public_Info``),
a które prywatne (``Private_Info``) — zgodnie z zasadą „jedno źródło klasyfikacji"
(R2.4). Warstwa widoczności (``core/visibility.py``) czyta WYŁĄCZNIE te zbiory,
nie powiela klasyfikacji ani nie rozsiewa metadanych po polach modelu.

Zbiory są jawnymi stałymi ``frozenset`` + test spójności
(``assert_classification_complete``). Powód takiego wyboru (zamiast metadanych
``Field(json_schema_extra=...)``): zestaw pól ``PlayerState`` można odczytać
z ``model_fields``, więc test wymusza równość zbiorów automatycznie (R2.6) — przy
dodaniu nowego pola bez klasyfikacji test jest czerwony. To prostsze i bardziej
czytelne, a jednocześnie trzyma logikę w jednym miejscu.

Warstwa ``core/`` — bez importów HTTP; czyste struktury i funkcje.
"""

from __future__ import annotations

from .game_state import PlayerState

# Pola JAWNE (Public_Info) gracza — widoczne dla wszystkich (R2.2). Pola ``private``
# oraz ``hidden_card_counts`` NIE należą tu z definicji (pierwsze jest tajne, drugie
# jest polem technicznym projekcji).
PUBLIC_FIELDS: frozenset[str] = frozenset(
    {
        "player_id",
        "display_name",
        "control_type",
        "difficulty",
        "personality",
        "faction",
        "color",
        "home_position",
        "seat_position",
        "victory_points",
        "trade_goods",
        "commodities",
        "commodity_value",
        "tactical_cc",
        "fleet_cc",
        "strategic_cc",
        "cc_reinf",
        "passed",
        "took_action_this_turn",
        "transacted_with",
        "strategy_cards",
        "exhausted_strategy_cards",
        "controlled_planets",
        "exhausted_planets",
        "technologies",
        "exhausted_technologies",
        "leader_states",
        "breakthrough_unlocked",
        "breakthrough_exhausted",
        "breakthrough_tg",
        "promissory_notes_in_play",
        "scored_secrets",
        "relic_fragments",
        "relics",
        "exhausted_relics",
        "exhausted_legendaries",
    }
)

# Pola TAJNE (Private_Info) gracza — widoczne tylko właścicielowi (R2.3). Całe pole
# ``private`` (podmodel ``PlayerPrivateState``) jest prywatne, więc klasyfikacja
# pozostaje jednopoziomowa.
PRIVATE_FIELDS: frozenset[str] = frozenset({"private"})

# Pole TECHNICZNE projekcji — nie jest ani danymi gracza do pokazania, ani
# klasyfikowane jako Public/Private. Istnieje tylko po to, by projekcja widoczności
# mogła zapisać liczebności zredagowanych rąk (R4.4). Wykluczane z kontroli
# spójności klasyfikacji.
PROJECTION_FIELDS: frozenset[str] = frozenset({"hidden_card_counts"})


def classified_fields() -> frozenset[str]:
    """Zwraca sumę pól sklasyfikowanych (``PUBLIC_FIELDS`` ∪ ``PRIVATE_FIELDS``)."""
    return PUBLIC_FIELDS | PRIVATE_FIELDS


def assert_classification_complete() -> None:
    """Weryfikuje, że klasyfikacja pokrywa dokładnie pola ``PlayerState`` (R2.1, R2.5, R2.6).

    Zbiór pól modelu jest odczytywany z ``PlayerState.model_fields``, po czym
    odejmowane są ``PROJECTION_FIELDS`` (pole techniczne projekcji nie podlega
    klasyfikacji). Funkcja rzuca ``ValueError``, gdy:

    * (a) jakieś pole ``PlayerState`` nie jest sklasyfikowane — brak w sumie
      ``PUBLIC_FIELDS`` ∪ ``PRIVATE_FIELDS``;
    * (b) pole jest sklasyfikowane podwójnie — należy jednocześnie do
      ``PUBLIC_FIELDS`` i ``PRIVATE_FIELDS``;
    * (c) klasyfikacja wskazuje pole nieistniejące w modelu.

    Wołane w teście spójności (i opcjonalnie przy starcie). Przy dodaniu nowego
    pola do ``PlayerState`` bez aktualizacji klasyfikacji funkcja zgłosi błąd.
    """
    # (b) Podwójna klasyfikacja — przecięcie musi być puste.
    overlap = PUBLIC_FIELDS & PRIVATE_FIELDS
    if overlap:
        raise ValueError(
            "Fields classified twice (both Public and Private): "
            f"{sorted(overlap)}"
        )

    model_fields = frozenset(PlayerState.model_fields) - PROJECTION_FIELDS
    classified = classified_fields()

    # (c) Klasyfikacja wskazuje pole nieistniejące w modelu.
    unknown = classified - model_fields
    if unknown:
        raise ValueError(
            "Classification references fields missing from PlayerState: "
            f"{sorted(unknown)}"
        )

    # (a) Pole modelu bez klasyfikacji.
    unclassified = model_fields - classified
    if unclassified:
        raise ValueError(
            "PlayerState fields without a Public/Private classification: "
            f"{sorted(unclassified)}"
        )
