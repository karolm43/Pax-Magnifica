"""Testy fazy strategii (Etap E2) — czyste funkcje ``strategy_phase``.

Reguły: RULES.md 13 (wybór karty = transfer TG z karty do gracza; akumulacja +1 TG
na niewybranych kartach; oznaczenie zagranej). Dane kart z rejestru (zestaw PoK, 8 kart).
"""

from __future__ import annotations

import pytest

from src.core import strategy_phase
from src.core.game_state import GameState, PlayerState
from src.core.models import StrategyCardDef
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    """Stan z 3 graczami, jawną kolejnością miejsc i mówcą p1.

    Po wprowadzeniu ``Pick_Count`` (RULES.md 13) ``pick_strategy_card`` waliduje
    kolejność (musi wybierać bieżący picker = mówca na start) oraz liczbę graczy
    (3–8). Dlatego fikstura ma 3 graczy, ``seating_order`` i ``speaker_id`` — picker
    jest deterministyczny (p1 pierwszy). Przy 3 graczach ``Pick_Count = 2``.
    """
    return GameState(
        seating_order=["p1", "p2", "p3"],
        speaker_id="p1",
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1"),
            "p2": PlayerState(player_id="p2"),
            "p3": PlayerState(player_id="p3"),
        },
    )


def test_available_initiatives_pok_set(registry: StaticDataRegistry) -> None:
    # Domyślny zestaw PoK ma 8 kart o inicjatywach 1..8.
    assert strategy_phase.available_initiatives(registry) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_pick_assigns_card_and_sets_initiative(
    registry: StaticDataRegistry,
) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 1)
    assert state.players["p1"].strategy_cards == [1]
    assert 1 in strategy_phase.picked_initiatives(state)


def test_pick_transfers_trade_goods_from_card(
    registry: StaticDataRegistry,
) -> None:
    # Na karcie inicjatywy 5 leżą 2 TG — po wyborze gracz je dostaje, karta → 0.
    base = _state()
    base.strategy_card_tg = {5: 2}
    base.players["p1"].trade_goods = 1
    state = strategy_phase.pick_strategy_card(base, registry, "p1", 5)
    assert state.players["p1"].trade_goods == 3  # 1 + 2 z karty
    assert state.strategy_card_tg[5] == 0


def test_pick_rejects_already_picked(registry: StaticDataRegistry) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 3)
    with pytest.raises(ValueError, match="już wybrana"):
        strategy_phase.pick_strategy_card(state, registry, "p2", 3)


def test_pick_rejects_card_outside_set(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="nie jest w zestawie"):
        strategy_phase.pick_strategy_card(_state(), registry, "p1", 9)


def test_pick_rejects_unknown_player(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="Nieznany gracz"):
        strategy_phase.pick_strategy_card(_state(), registry, "ghost", 1)


def test_play_marks_exhausted(registry: StaticDataRegistry) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 2)
    played = strategy_phase.play_strategy_card(state, "p1", 2)
    assert 2 in played.players["p1"].exhausted_strategy_cards


def test_play_is_idempotent(registry: StaticDataRegistry) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 2)
    once = strategy_phase.play_strategy_card(state, "p1", 2)
    twice = strategy_phase.play_strategy_card(once, "p1", 2)
    assert twice.players["p1"].exhausted_strategy_cards == [2]


def test_play_rejects_card_not_owned(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="nie posiada karty"):
        strategy_phase.play_strategy_card(_state(), "p1", 4)


def test_accumulate_adds_one_tg_to_unpicked(
    registry: StaticDataRegistry,
) -> None:
    # 3 graczy, Pick_Count=2: akumulacja wymaga ZAKOŃCZONEGO wyboru (guard R7.5).
    # p1, p2, p3 biorą po 2 karty (1–6); karty 7 i 8 zostają niewybrane.
    state = _state()  # speaker p1, kolejność p1, p2, p3
    for player_id, inits in (("p1", (1, 2)), ("p2", (3, 4)), ("p3", (5, 6))):
        for initiative in inits:
            state = strategy_phase.pick_strategy_card(
                state, registry, player_id, initiative
            )
    acc = strategy_phase.accumulate_unpicked_tg(state, registry)
    # Wybrane karty 1..6 bez TG; niewybrane 7, 8 dostają +1.
    for init in [1, 2, 3, 4, 5, 6]:
        assert acc.strategy_card_tg.get(init, 0) == 0
    for init in [7, 8]:
        assert acc.strategy_card_tg[init] == 1
    # Powtórna akumulacja (bez nowego wyboru) rośnie dalej.
    acc2 = strategy_phase.accumulate_unpicked_tg(acc, registry)
    assert acc2.strategy_card_tg[7] == 2


def test_reset_returns_cards_to_pool_keeps_tg(
    registry: StaticDataRegistry,
) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 1)
    state = strategy_phase.play_strategy_card(state, "p1", 1)
    state.strategy_card_tg = {4: 3}
    reset = strategy_phase.reset_strategy_cards(state)
    assert reset.players["p1"].strategy_cards == []
    assert reset.players["p1"].exhausted_strategy_cards == []
    # Trade goods na kartach NIE są czyszczone (akumulują się między rundami).
    assert reset.strategy_card_tg == {4: 3}


def test_pick_does_not_mutate_input(registry: StaticDataRegistry) -> None:
    base = _state()
    strategy_phase.pick_strategy_card(base, registry, "p1", 1)
    assert base.players["p1"].strategy_cards == []  # wejście nietknięte


def _seated_state() -> GameState:
    """Stan z 3 graczami, jawną kolejnością miejsc i mówcą p2 (RULES.md 24)."""
    return GameState(
        seating_order=["p1", "p2", "p3"],
        speaker_id="p2",
        players={
            "p1": PlayerState(player_id="p1"),
            "p2": PlayerState(player_id="p2"),
            "p3": PlayerState(player_id="p3"),
        },
    )


def test_speaker_order_starts_from_speaker() -> None:
    # Mówca p2 → kolejność wyboru p2, p3, p1 (zegarowo od mówcy).
    state = _seated_state()
    assert strategy_phase.speaker_order(state) == ["p2", "p3", "p1"]


def test_speaker_order_fallback_without_seating() -> None:
    # Bez seating_order: kolejność po id, ale wciąż od mówcy, gdy znany.
    state = GameState(
        speaker_id="p2",
        players={
            "p1": PlayerState(player_id="p1"),
            "p2": PlayerState(player_id="p2"),
            "p3": PlayerState(player_id="p3"),
        },
    )
    assert strategy_phase.speaker_order(state) == ["p2", "p3", "p1"]


def test_next_picker_starts_with_speaker() -> None:
    assert strategy_phase.next_strategy_picker(_seated_state()) == "p2"


def test_pick_advances_active_in_speaker_order(
    registry: StaticDataRegistry,
) -> None:
    # 3 graczy → Pick_Count=2 (RULES.md 13): każdy gracz musi zebrać DWIE karty.
    # ``next_strategy_picker`` zwraca PIERWSZEGO w speaker order poniżej Pick_Count,
    # więc bieżący gracz dobiera obie swoje karty, zanim kolej przejdzie dalej
    # (p2, p2, p3, p3, p1, p1 — druga runda „od mówcy" realizuje się naturalnie).
    state = _seated_state()  # speaker p2, kolejność p2, p3, p1
    state.active_player_id = "p2"
    after = strategy_phase.pick_strategy_card(state, registry, "p2", 1)
    assert after.active_player_id == "p2"  # p2 ma 1 < 2 → wciąż p2
    after = strategy_phase.pick_strategy_card(after, registry, "p2", 4)
    assert after.active_player_id == "p3"  # p2 ma komplet → kolej na p3
    after = strategy_phase.pick_strategy_card(after, registry, "p3", 2)
    assert after.active_player_id == "p3"
    after = strategy_phase.pick_strategy_card(after, registry, "p3", 5)
    assert after.active_player_id == "p1"
    after = strategy_phase.pick_strategy_card(after, registry, "p1", 3)
    assert after.active_player_id == "p1"
    # Ostatnia karta — wszyscy mają po 2 → brak kolejnego wybierającego.
    after = strategy_phase.pick_strategy_card(after, registry, "p1", 6)
    assert after.active_player_id is None


def test_reset_sets_active_to_speaker(registry: StaticDataRegistry) -> None:
    # Po rozdaniu kart i resecie faza strategii wraca do wyboru od mówcy.
    state = _seated_state()
    state = strategy_phase.pick_strategy_card(state, registry, "p2", 1)
    reset = strategy_phase.reset_strategy_cards(state)
    assert reset.active_player_id == "p2"  # mówca znów wybiera pierwszy


# --- validate_strategy_card_set (Task 2.17, Requirement 6.1, 6.2) ----------


def _card(initiative: int) -> object:
    """Minimalna atrapa karty z polem ``initiative`` (do testów walidacji)."""
    from src.core.models import StrategyCardDef

    return StrategyCardDef(
        id=f"sc{initiative}",
        name=f"Card {initiative}",
        source="pok",
        initiative=initiative,
    )


class _FakeRegistry:
    """Atrapa rejestru zwracająca ustaloną listę kart z ``strategy_card_set``."""

    def __init__(self, cards: list[object]) -> None:
        self._cards = cards

    def strategy_card_set(self, set_alias: str = "pok") -> list[object]:
        return self._cards


def test_validate_set_returns_eight_cards_for_pok(
    registry: StaticDataRegistry,
) -> None:
    # Prawdziwy zestaw PoK jest spójny: 8 kart, inicjatywy 1..8, bez duplikatów.
    cards = strategy_phase.validate_strategy_card_set(registry)
    assert len(cards) == 8
    assert sorted(c.initiative for c in cards) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_validate_canonical_te_set_is_complete() -> None:
    """Kanoniczny zestaw TE (Thunder's Edge włączony) przechodzi walidację:
    8 kart z kompletem pól, a Construction/Warfare to warianty te4/te6 (RULES.md 14).
    """
    registry = StaticDataRegistry(
        enabled_sources=["base", "pok", "codex1", "codex2", "codex3", "codex4", "thunders_edge"]
    )
    cards = strategy_phase.validate_strategy_card_set(registry)
    assert len(cards) == 8
    ids = [c.id for c in cards]
    assert "te4construction" in ids
    assert "te6warfare" in ids


def test_validate_set_rejects_wrong_count() -> None:
    fake = _FakeRegistry([_card(i) for i in range(1, 8)])  # tylko 7 kart
    with pytest.raises(ValueError, match="Niespójny zestaw kart"):
        strategy_phase.validate_strategy_card_set(fake)  # type: ignore[arg-type]


def test_validate_set_rejects_initiative_out_of_range() -> None:
    cards = [_card(i) for i in range(1, 8)] + [_card(9)]  # 8 kart, ale 9 poza 1..8
    fake = _FakeRegistry(cards)
    with pytest.raises(ValueError, match="poza zakresem"):
        strategy_phase.validate_strategy_card_set(fake)  # type: ignore[arg-type]


def test_validate_set_rejects_duplicate_initiative() -> None:
    cards = [_card(i) for i in range(1, 8)] + [_card(1)]  # 8 kart, duplikat 1
    fake = _FakeRegistry(cards)
    with pytest.raises(ValueError, match="zduplikowane"):
        strategy_phase.validate_strategy_card_set(fake)  # type: ignore[arg-type]


# --- Testy brzegowe refaktoryzacji po przeglądzie semantycznym (znalezisko #7) ---


def test_ensure_complete_rejects_seating_players_mismatch() -> None:
    """Rozjazd seating_order↔players (znalezisko #1): gracz spoza niepustego
    ``seating_order`` (realna ścieżka God-Mode) → czytelny ValueError z
    ``ensure_strategy_complete`` ZANIM dojdzie do ``strict_initiative_order``.
    """
    state = GameState(
        seating_order=["p1", "p2"],  # p3 celowo poza listą miejsc
        speaker_id="p1",
        players={
            "p1": PlayerState(player_id="p1", strategy_cards=[1, 2]),
            "p2": PlayerState(player_id="p2", strategy_cards=[3, 4]),
            "p3": PlayerState(player_id="p3", strategy_cards=[5, 6]),
        },
    )
    with pytest.raises(ValueError, match="nie pokrywa się z graczami"):
        strategy_phase.ensure_strategy_complete(state)


def test_ensure_complete_allows_empty_seating_order(
    registry: StaticDataRegistry,
) -> None:
    """Puste ``seating_order`` jest OK: ``speaker_order`` używa ``sorted(players)``,
    więc kompletny, poprawny set 3–8 graczy NIE rzuca (regresja po #1).
    """
    state = GameState(
        speaker_id="p1",
        players={
            "p1": PlayerState(player_id="p1", strategy_cards=[1, 2]),
            "p2": PlayerState(player_id="p2", strategy_cards=[3, 4]),
            "p3": PlayerState(player_id="p3", strategy_cards=[5, 6]),
        },
    )
    strategy_phase.ensure_strategy_complete(state)  # nie rzuca


def test_accumulate_rejects_wrong_player_count(
    registry: StaticDataRegistry,
) -> None:
    """Liczba graczy spoza 3–8 (znalezisko #2/#3): ``accumulate_unpicked_tg`` na
    stanie 2-osobowym RZUCA (zabezpiecza ścieżkę /round/next), zamiast cicho
    przepuścić akumulację. Dawny guard na ``next_strategy_picker`` by przepuścił.
    """
    state = GameState(
        seating_order=["p1", "p2"],
        speaker_id="p1",
        players={
            "p1": PlayerState(player_id="p1"),
            "p2": PlayerState(player_id="p2"),
        },
    )
    with pytest.raises(ValueError, match="Nieprawidłowa liczba graczy"):
        strategy_phase.accumulate_unpicked_tg(state, registry)


def test_accumulate_incomplete_pick_keeps_message(
    registry: StaticDataRegistry,
) -> None:
    """Niekompletny wybór przy poprawnej liczbie graczy → komunikat akumulacji
    pozostaje bez zmian (kontrakt R7.5).
    """
    state = _state()  # 3 graczy, nikt nie wybrał kart
    with pytest.raises(ValueError, match="faza strategii niezakończona"):
        strategy_phase.accumulate_unpicked_tg(state, registry)


def _full_card(initiative: int) -> StrategyCardDef:
    """Karta z KOMPLETEM pól (nazwa/primary/secondary/kolor) — do testu #4."""
    return StrategyCardDef(
        id=f"sc{initiative}",
        name=f"Card {initiative}",
        source="pok",
        initiative=initiative,
        primaryTexts=["primary"],
        secondaryTexts=["secondary"],
        colourHexCode="#ffffff",
    )


def test_validate_set_rejects_missing_card_field() -> None:
    """Komplet pól karty (R6.4, przeniesiony do core — #4): karta bez nazwy →
    ValueError z ``validate_strategy_card_set`` (dawniej tylko w routerze).
    """
    cards: list[object] = [_full_card(i) for i in range(1, 8)]
    blank = _full_card(8)
    blank.name = ""  # brak nazwy — łamie komplet pól
    cards.append(blank)
    fake = _FakeRegistry(cards)
    with pytest.raises(ValueError, match="brak pola nazwa"):
        strategy_phase.validate_strategy_card_set(fake)  # type: ignore[arg-type]
