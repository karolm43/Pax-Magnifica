"""Testy przykładowe raportu Audytora_Danych (``src/audit/report.py``).

Pokrywają: wykrywanie wpisów podejrzanych strukturalnie na ``tmp_path`` (R4.5),
rozróżnienie błąd krytyczny / ostrzeżenie w ``exit_code`` (R3.4, R12.2) oraz to, że
``build_report`` + ``render_text`` na realnym rejestrze zawierają wszystkie sekcje
raportu z R12.1.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.audit.assets_manifest import ManifestDiff
from src.audit.report import (
    AuditReport,
    AuditScans,
    ExternalUrlHit,
    SuspiciousEntry,
    build_report,
    collect_scans,
    detect_suspicious,
    exit_code,
    render_text,
    write_baseline,
)
from src.core.components import CategorySpec, ComponentCategory, TokenDef
from src.core.registry import StaticDataRegistry

# --- Wykrywanie wpisów podejrzanych (strukturalnie, R4.5) ----------------


def _write_entries(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_detect_suspicious_wykrywa_zrodlo_kanoniczne_w_pliku_o_nietypowej_nazwie(
    tmp_path: Path,
) -> None:
    """Wpis kanoniczny w pliku o nazwie spoza znanych źródeł i kategorii = podejrzany."""
    directory = tmp_path / "tokens"
    directory.mkdir()
    # Plik o nazwie homebrew ("theodisi") z wpisem źródła kanonicznego -> podejrzany.
    _write_entries(directory / "theodisi.json", [{"id": "foo", "source": "codex1"}])
    # Plik o nazwie znanego źródła ("pok") -> NIE podejrzany.
    _write_entries(directory / "pok.json", [{"id": "bar", "source": "pok"}])
    # Plik o nazwie kategorii ("tokens") -> NIE podejrzany.
    _write_entries(directory / "tokens.json", [{"id": "baz", "source": "base"}])
    # Wpis homebrew (źródło niekanoniczne) w pliku homebrew -> NIE podejrzany.
    _write_entries(directory / "ds.json", [{"id": "qux", "source": "ds"}])

    spec = CategorySpec(
        ComponentCategory.TOKEN, directory, TokenDef, id_field="id"
    )
    result = detect_suspicious(
        specs={ComponentCategory.TOKEN: spec},
        known={"base", "pok", "codex1"},
    )

    assert result == [SuspiciousEntry(ComponentCategory.TOKEN, "foo", "codex1", "theodisi")]


def test_detect_suspicious_pusty_gdy_wszystkie_pliki_normalne(tmp_path: Path) -> None:
    """Brak wpisów podejrzanych, gdy nazwy plików to źródła lub kategoria."""
    directory = tmp_path / "tokens"
    directory.mkdir()
    _write_entries(directory / "base.json", [{"id": "a", "source": "base"}])
    _write_entries(directory / "tokens.json", [{"id": "b", "source": "pok"}])

    spec = CategorySpec(ComponentCategory.TOKEN, directory, TokenDef, id_field="id")
    assert detect_suspicious(
        specs={ComponentCategory.TOKEN: spec}, known={"base", "pok"}
    ) == []


# --- Kod wyjścia: krytyczne vs ostrzeżenia (R3.4, R12.2) -----------------


def test_exit_code_zero_dla_samych_ostrzezen() -> None:
    """Same ostrzeżenia (podejrzane, unclassified, luki, bez noty) nie zmieniają kodu 0."""
    report = AuditReport(
        suspicious=[SuspiciousEntry(ComponentCategory.TOKEN, "x", "base", "foo")],
        gaps_to_confirm=[],
        no_rules_note=[],
    )
    assert exit_code(report) == 0
    assert report.has_critical is False


def test_exit_code_niezerowy_dla_nierozwiazanej_referencji() -> None:
    assert exit_code(AuditReport(unresolved=["system x: brak planet ['y']"])) == 1


def test_exit_code_niezerowy_dla_brakujacego_pliku_manifestu() -> None:
    report = AuditReport(
        manifest=ManifestDiff(missing=frozenset({"units/a.png"}), unused=frozenset())
    )
    assert exit_code(report) == 1


def test_exit_code_niezerowy_dla_zewnetrznego_url() -> None:
    report = AuditReport(external_urls=[ExternalUrlHit("index.html", 1, "https://x.example/a")])
    assert exit_code(report) == 1


def test_exit_code_niezerowy_dla_bledu_walidacji() -> None:
    assert exit_code(AuditReport(validation_error="boom")) == 1


def test_manifest_unused_nie_jest_krytyczny() -> None:
    """Pliki nieużywane (na dysku, brak w manifeście) są ostrzeżeniem, nie błędem."""
    report = AuditReport(manifest=ManifestDiff(missing=frozenset(), unused=frozenset({"x.png"})))
    assert exit_code(report) == 0


# --- Realny rejestr: wszystkie sekcje raportu (R12.1) --------------------


def test_build_report_i_render_text_na_realnym_rejestrze() -> None:
    """``build_report`` + ``render_text`` zawierają wszystkie sekcje raportu (R12.1)."""
    registry = StaticDataRegistry()
    report = build_report(registry, collect_scans(registry))

    # Liczby komponentów zgadzają się z katalogiem.
    assert report.counts == registry.catalog.counts()
    assert report.counts[ComponentCategory.ACTION_CARD]  # karty akcji są niepuste

    text = render_text(report)
    for section in (
        "Liczby komponentów",
        "Pominięte wpisy",
        "Wpisy bez źródła",
        "Kolizje id",
        "Wpisy podejrzane",
        "Luki źródeł kanonicznych",
        "Nierozwiązane referencje",
        "Specyfikacje czasowe 'unclassified'",
        "Pokrycie efektów",
        "Komponenty bez noty reguł",
        "Osierocone statusy efektów",
        "Manifest grafik",
        "Zewnętrzne URL",
        "Różnice danych wbudowanych we frontend",
        "Wynik:",
    ):
        assert section in text, f"Brak sekcji w raporcie: {section}"


def test_build_report_jest_czysty_wzgledem_pustych_skanow() -> None:
    """Bez skanów (puste I/O) raport nie ma błędów krytycznych pochodzących z dysku."""
    registry = StaticDataRegistry()
    report = build_report(registry, AuditScans())
    # Pusty manifest i brak URL -> jedyne potencjalne błędy to walidacja (brak).
    assert report.manifest.is_empty
    assert report.external_urls == []
    assert report.unresolved == []
    assert exit_code(report) == 0


def test_write_baseline_zapisuje_liczby_z_raportu(tmp_path: Path) -> None:
    """``write_baseline`` zapisuje ``counts`` w kształcie kategoria -> źródło -> liczba."""
    registry = StaticDataRegistry()
    report = build_report(registry, AuditScans())
    out = tmp_path / "baseline_counts.json"
    write_baseline(report, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    expected = {
        category.value: dict(sorted(report.counts[category].items()))
        for category in report.counts
    }
    assert data == expected
