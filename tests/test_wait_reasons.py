"""Wait reasons (RULES.md 44.5): ``core/actor.describe_wait_reasons`` - who and why, no leaks."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.bot_runner import BotRunner
from src.core import actor
from src.core.event_store import EventStore
from src.core.game_state import (
    ActiveCombat,
    AgendaPhaseState,
    AgendaStep,
    CombatStep,
    ControlType,
    ExplorationState,
    GameState,
    HeldPlay,
    InvasionPhase,
    InvasionState,
    PendingOffer,
    Phase,
    PlayerState,
    ProductionGrant,
    QueuedSecondary,
    ReactionPause,
    SetupStage,
    SetupState,
    StatusPhaseState,
    StatusStep,
    StrategyResolution,
    SystemState,
    TacticalStep,
    TimingWindow,
    WindowType,
)
from src.core.registry import StaticDataRegistry
from tests.engine import fuzz

PIDS = ("p1", "p2", "p3")


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(**changes: object) -> GameState:
    factions = dict(zip(PIDS, ("sol", "arborec", "hacan"), strict=True))
    state = GameState(
        round_number=2,
        phase=Phase.ACTION,
        active_player_id="p1",
        speaker_id="p2",
        seating_order=list(PIDS),
        players={
            pid: PlayerState(player_id=pid, faction=factions[pid], color="blue") for pid in PIDS
        },
    )
    for name, value in changes.items():
        setattr(state, name, value)
    return state


def _brief(state: GameState, registry: StaticDataRegistry | None = None) -> list[tuple[str, str]]:
    return [(r.player_id, r.reason_code) for r in actor.describe_wait_reasons(state, registry)]


def _window(kind: WindowType, queue: list[str], **context: str | int) -> TimingWindow:
    return TimingWindow(window_type=kind, queue=queue, context=dict(context))


def _combat(**changes: object) -> ActiveCombat:
    combat = ActiveCombat(kind="space", position="101", attacker="p1", defender="p2")
    for name, value in changes.items():
        setattr(combat, name, value)
    return combat


def _offer(player_id: str, *, mandatory: bool = False) -> PendingOffer:
    return PendingOffer(
        id=f"o-{player_id}",
        player_id=player_id,
        event="SECRET_EVENT",
        moment="after",
        hook_seq=0,
        label="SECRET_LABEL",
        ctx={"card": "SECRET_CARD"},
        mandatory=mandatory,
    )


def _pause() -> ReactionPause:
    return ReactionPause(
        key="k",
        event="strategic_action",
        moment="when",
        label="a strategic action is announced",
        opened_at=1.0,
        eligible=["p2", "p3"],
    )


# --- one test per situation --------------------------------------------------------------------


def test_turn_and_its_variants() -> None:
    [reason] = actor.describe_wait_reasons(_state())
    assert (reason.player_id, reason.reason_code, reason.summary) == ("p1", "turn", "taking a turn")
    assert reason.blocking

    tactical = _state(tactical_step=TacticalStep.MOVEMENT)
    assert actor.describe_wait_reasons(tactical)[0].summary == "tactical action: movement"

    done = _state()
    done.players["p1"].took_action_this_turn = True
    assert actor.describe_wait_reasons(done)[0].summary == "ending the turn"

    picking = _state(phase=Phase.STRATEGY)
    assert actor.describe_wait_reasons(picking)[0].summary == "picking a strategy card"


def test_speaker_when_everyone_passed_or_nobody_is_active() -> None:
    state = _state()
    for player in state.players.values():
        player.passed = True
    last, speaker = actor.describe_wait_reasons(state)
    # A pass does not hand on the turn: the last passer may still end it, not required.
    assert (last.player_id, last.summary, last.blocking) == ("p1", "may still end the turn", False)
    assert (speaker.player_id, speaker.reason_code, speaker.blocking) == ("p2", "speaker", True)
    assert actor.awaiting(state) == [("p2", "speaker")]
    from src.core.game_state import TurnEndWindow

    state.turn_end_window = TurnEndWindow(ended_player="p1", ended_passed=True)
    assert _brief(state) == [("p2", "speaker")]
    assert _brief(_state(active_player_id=None)) == [("p2", "speaker")]


def test_nothing_is_awaited_after_the_game_ends() -> None:
    assert actor.describe_wait_reasons(_state(winner_id="p1")) == []


def test_setup_secrets_are_simultaneous_then_speaker() -> None:
    state = _state(setup=SetupState())
    for pid in PIDS:
        state.players[pid].private.secret_candidates = ["SECRET_A", "SECRET_B"]
    assert _brief(state) == [(pid, "secret") for pid in PIDS]
    state.setup = SetupState(stage=SetupStage.CUSTODIANS)
    [reason] = actor.describe_wait_reasons(state)
    assert (reason.player_id, reason.reason_code) == ("p2", "setup")
    assert "Custodians" in reason.summary


def test_strategy_primary() -> None:
    state = _state(
        phase=Phase.ACTION,
        pending_strategy=StrategyResolution(initiative=7, owner_id="p1", step="research"),
    )
    assert _brief(state) == [("p1", "strategy")]


def test_secondary_lists_current_and_later_players(registry: StaticDataRegistry) -> None:
    state = _state(
        pending_window=_window(WindowType.STRATEGY_SECONDARY, ["p2", "p3"], initiative=7)
    )
    current, later = actor.describe_wait_reasons(state, registry)
    assert (current.player_id, current.reason_code, current.blocking) == ("p2", "secondary", True)
    assert current.summary == "following Strategy Card 7 (Technology)"
    assert (later.player_id, later.blocking) == ("p3", False)
    assert later.summary == "yet to answer Strategy Card 7 (Technology)"
    assert actor.awaiting(state) == [("p2", "secondary")]

    # A queued decision: nothing is awaited from p3 any more (that it is queued is public).
    state.secondary_queue = {"p3": QueuedSecondary(initiative=7, execute=True)}
    assert _brief(state) == [("p2", "secondary")]


def test_secondary_waiting_for_its_production() -> None:
    state = _state(
        pending_window=_window(WindowType.STRATEGY_SECONDARY, ["p2"], initiative=6),
        production_grant=ProductionGrant(player_id="p2", position="101", standalone=True),
    )
    assert _brief(state) == [("p2", "produce")]


def test_reaction_pause_and_held_play_list_every_eligible_player() -> None:
    state = _state(reaction_pause=_pause())
    assert _brief(state) == [("p2", "react"), ("p3", "react")]
    assert actor.describe_wait_reasons(state)[0].summary == (
        "may react: a strategic action is announced"
    )
    held = _state(
        held_play=HeldPlay(player_id="p1", card_id="SECRET_CARD", opened_at=1.0, eligible=["p3"])
    )
    assert _brief(held) == [("p3", "react")]


def test_hand_limit_discard(registry: StaticDataRegistry) -> None:
    from src.core import rules_hooks

    rules_hooks.bind_registry(registry)
    state = _state()
    limit = registry.hand_limits().action_cards
    assert limit is not None
    state.players["p3"].private.action_cards = ["SECRET_CARD"] * (limit + 1)
    reason, turn = actor.describe_wait_reasons(state)
    assert (reason.player_id, reason.reason_code) == ("p3", "discard")
    assert reason.summary == "discarding 1 action card over the hand limit"
    # Discarding blocks only p3's own moves: the turn player is still awaited.
    assert (turn.player_id, turn.reason_code, turn.blocking) == ("p1", "turn", True)


def test_offers_alone_and_reaction_window() -> None:
    state = _state(pending_offers=[_offer("p2"), _offer("p3", mandatory=True)])
    assert [r.summary for r in actor.describe_wait_reasons(state)] == [
        "deciding whether to use an ability",
        "making a required choice",
    ]
    assert _brief(state) == [("p2", "decide"), ("p3", "decide")]

    state.pending_window = _window(WindowType.REACTION, ["p2"])
    assert _brief(state) == [("p2", "decide"), ("p3", "decide")]

    state.pending_offers = []
    [reason] = actor.describe_wait_reasons(state)
    assert (reason.reason_code, reason.summary) == (
        "respond",
        "deciding on a timing window reaction",
    )


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        (WindowType.COMBAT_RETREAT, "retreat"),
        (WindowType.FLEET_POOL, "remove_excess"),
        (WindowType.CAPACITY, "remove_excess"),
        (WindowType.SPACE_CANNON, "space_cannon"),
    ],
)
def test_other_timing_windows(kind: WindowType, code: str) -> None:
    assert _brief(_state(pending_window=_window(kind, ["p2"]))) == [("p2", code)]


def test_space_cannon_target_assigns_the_hits() -> None:
    window = _window(WindowType.SPACE_CANNON, ["p2"], hits=2, roller="p2", target="p1")
    state = _state(
        pending_window=window,
        active_system="101",
        systems={
            "101": SystemState(
                position="101", system_id="19", space_units={"p1": {"cruiser": 3}}
            )
        },
    )
    [reason] = actor.describe_wait_reasons(state, StaticDataRegistry())
    assert (reason.player_id, reason.reason_code) == ("p1", "assign_hits")
    assert reason.summary == "assigning 2 Space Cannon hits"


def test_combat_hit_assignment() -> None:
    state = _state(
        active_combat=_combat(step=CombatStep.ASSIGN, pending_hits={"p2": 2, "p1": 1}),
        pending_window=_window(WindowType.COMBAT_ASSIGN_HITS, ["p2", "p1"]),
    )
    first, second = actor.describe_wait_reasons(state)
    assert (first.player_id, first.summary, first.blocking) == (
        "p2",
        "assigning 2 combat hits",
        True,
    )
    assert (second.player_id, second.summary, second.blocking) == (
        "p1",
        "assigning 1 combat hit",
        False,
    )


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"step": CombatStep.ROLL}, ["p1", "p2"]),
        ({"step": CombatStep.ROLL, "side_rolls": {"p1": []}}, ["p2"]),
        ({"step": CombatStep.AFB}, ["p1", "p2"]),
        ({"step": CombatStep.RETREAT, "retreating": ["p2"]}, ["p2"]),
        ({"step": CombatStep.DONE}, ["p1"]),
    ],
)
def test_combat_steps(changes: dict[str, object], expected: list[str]) -> None:
    state = _state(active_combat=_combat(**changes))
    assert _brief(state) == [(pid, "combat") for pid in expected]


def test_exploration_and_invasion() -> None:
    exploring = _state(exploration=ExplorationState(player_id="p3", position="101"))
    assert _brief(exploring) == [("p3", "explore")]

    invasion = _state(
        invasion=InvasionState(position="101", attacker="p1", phase=InvasionPhase.COMMIT)
    )
    [reason] = actor.describe_wait_reasons(invasion)
    assert reason.reason_code == "invasion"
    assert reason.summary == "invasion: committing ground forces"


def test_invasion_hits_wait_for_the_right_side() -> None:
    bombarded = InvasionState(
        position="101",
        attacker="p1",
        bombard_pending={"jord": 3},
        log=[{"phase": "BOMBARDMENT", "planet": "jord", "defender": "p2"}],
    )
    [reason] = actor.describe_wait_reasons(_state(invasion=bombarded))
    assert (reason.player_id, reason.summary) == ("p2", "assigning 3 bombardment hits")

    defense = InvasionState(
        position="101",
        attacker="p1",
        phase=InvasionPhase.SPACE_CANNON_DEFENSE,
        defense_pending={"jord": 1},
    )
    [reason] = actor.describe_wait_reasons(_state(invasion=defense))
    assert (reason.player_id, reason.summary) == ("p1", "assigning 1 Space Cannon hit")


def test_status_scoring_and_redistribution() -> None:
    state = _state(phase=Phase.STATUS, status=StatusPhaseState())
    scoring, *later = actor.describe_wait_reasons(state)
    assert (scoring.player_id, scoring.summary) == ("p1", "status phase scoring")
    assert [(r.player_id, r.reason_code, r.blocking) for r in later] == [
        ("p2", "score", False),
        ("p3", "score", False),
    ]

    state.status = StatusPhaseState(step=StatusStep.REDISTRIBUTE, done=["p2"])
    assert _brief(state) == [("p1", "redistribute"), ("p3", "redistribute")]

    state.status = StatusPhaseState(step=StatusStep.COMPLETE)
    assert _brief(state) == [("p2", "speaker")]


def test_agenda_vote_and_speaker_steps() -> None:
    state = _state(
        phase=Phase.AGENDA,
        agenda=AgendaPhaseState(step=AgendaStep.VOTE, vote_order=["p3", "p1", "p2"]),
    )
    assert _brief(state) == [("p3", "vote")]
    state.agenda = AgendaPhaseState(step=AgendaStep.TIEBREAK)
    [reason] = actor.describe_wait_reasons(state)
    assert (reason.reason_code, reason.summary) == ("speaker", "breaking the agenda tie (speaker)")


# --- visibility ---------------------------------------------------------------------------------


def _private_noise(state: GameState, tag: str) -> GameState:
    """Same public facts, different private ones: card ids, passes, prefs, queued choices."""
    noisy = state.clone()
    for pid, player in noisy.players.items():
        hand = player.private
        hand.action_cards = [f"{tag}-card-{pid}"]
        hand.secret_objectives = [f"{tag}-secret-{pid}"]
        hand.promissory_notes = [f"{tag}-note-{pid}"]
        hand.secret_candidates = [f"{tag}-candidate-{pid}"]
        hand.reaction_prefs.muted_cards = [f"{tag}-muted"]
    passed = ["p2"] if tag == "aaa" else []
    for window in (noisy.reaction_pause, noisy.held_play):
        if window is not None:
            window.passed = passed
            window.extended_by = passed
            window.auto_pass_at = {pid: 1.0 for pid in passed}
    for offer in noisy.pending_offers:
        offer.label = f"{tag}-label"
        offer.ctx = {"card": f"{tag}-ctx"}
    noisy.secondary_queue = {
        pid: QueuedSecondary(initiative=7, execute=tag == "aaa", payload={"tech": tag})
        for pid in noisy.secondary_queue
    }
    return noisy


@pytest.mark.parametrize(
    "state",
    [
        _state(reaction_pause=_pause()),
        _state(
            held_play=HeldPlay(player_id="p1", card_id="x", opened_at=1.0, eligible=["p2", "p3"])
        ),
        _state(pending_offers=[_offer("p2")]),
        _state(setup=SetupState()),
        _state(
            pending_window=_window(WindowType.STRATEGY_SECONDARY, ["p2", "p3", "p1"], initiative=7),
            secondary_queue={"p3": QueuedSecondary(initiative=7)},
        ),
    ],
    ids=["pause", "held", "offer", "setup", "secondary"],
)
def test_private_information_never_changes_or_enters_reasons(
    state: GameState, registry: StaticDataRegistry
) -> None:
    first = actor.describe_wait_reasons(_private_noise(state, "aaa"), registry)
    second = actor.describe_wait_reasons(_private_noise(state, "zzz"), registry)

    assert first == second and first
    text = repr(first) + actor.format_wait_reasons(_private_noise(state, "aaa"), registry)
    assert "aaa" not in text and "SECRET" not in text


def test_web_data_wait_reasons_are_the_same_for_every_viewer(registry: StaticDataRegistry) -> None:
    state = _state(reaction_pause=_pause(), pending_offers=[_offer("p2")])
    assert state.reaction_pause is not None
    state.reaction_pause.passed = ["p3"]
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    client = TestClient(app)

    docs = [
        client.get("/api/public/game/x/web-data", params={"viewing_player": pid}).json()
        for pid in PIDS
    ]

    assert docs[0]["waitReasons"] == docs[1]["waitReasons"] == docs[2]["waitReasons"]
    assert docs[0]["waitReasons"] == [
        {
            "playerId": pid,
            "reasonCode": "react",
            "summary": "may react: a strategic action is announced",
            "blocking": True,
        }
        for pid in ("p2", "p3")
    ]
    assert "SECRET" not in str(docs[0]["waitReasons"])


# --- diagnostics --------------------------------------------------------------------------------


def test_format_wait_reasons() -> None:
    assert actor.format_wait_reasons(_state()) == (
        "phase ACTION, round 2; p1 (sol) turn: taking a turn"
    )
    assert actor.format_wait_reasons(_state(winner_id="p1")).endswith("; nothing pending")


def test_fuzz_failure_reports_wait_reasons(
    registry: StaticDataRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fuzz, "check_invariants", lambda state: ["forced failure"])

    result = fuzz.run_game(registry, 1, rounds=2, out_dir=tmp_path)

    assert result.failure is not None
    assert result.failure.startswith("AssertionError: forced failure")
    assert result.failure.splitlines()[-1].startswith("waiting: phase ")
    assert result.failure_file is not None
    assert '"reason_code"' in Path(result.failure_file).read_text(encoding="utf-8")


def test_bot_runner_reports_a_stall_once(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    state = _state()
    for player in state.players.values():
        player.control_type = ControlType.BOT
    app = create_app(
        registry=registry, store=EventStore(":memory:"), initial_state=state, bots=True
    )
    runner: BotRunner = app.state.bot_runner
    monkeypatch.setattr("src.api.bot_runner.legal_actions", lambda obs, ctx: [])

    async def two_ticks() -> None:
        assert await runner.step() is False
        assert await runner.step() is False

    with caplog.at_level(logging.WARNING, logger="src.api.bot_runner"):
        asyncio.run(two_ticks())

    [message] = [r.getMessage() for r in caplog.records if "stalled" in r.getMessage()]
    assert "p1 (sol) turn: taking a turn" in message
