"""Testy właściwościowe modeli komponentów i kontekstu błędu walidacji.

Property 4 sprawdza, że ``build_component`` nie gubi żadnych informacji z JSON:
identyfikator pochodzi z pola wskazanego przez ``CategorySpec``, surowe dane
trafiają 1:1 do ``raw``, a pola tekstowe/okno/flavor są odtwarzane z wpisu.

Property 5 sprawdza, że gdy wpis aktywnego źródła nie przechodzi walidacji
modelu, ``load_components`` zgłasza ``DataValidationError`` niosący kontekst
wpisu (kategoria, plik, identyfikator). Test buduje na ``tmp_path`` prawdziwy
katalog kategorii z wygenerowanym, niepoprawnym wpisem.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.core.component_loader import DataValidationError, load_components
from src.core.components import (
    CategorySpec,
    ComponentCategory,
    ObjectiveDef,
    build_component,
)

# Identyfikatory i proste napisy używane w generatorach.
_ids = st.text(alphabet="abcdefgh01_", min_size=1, max_size=8)
_words = st.text(alphabet="abc XYZ .,", min_size=0, max_size=20)
_sources = st.sampled_from(["base", "pok", "codex1", "thunders_edge"])

# Pole identyfikatora bywa ``alias`` (karty/cele) albo ``id`` (żetony/eksploracje).
_id_fields = st.sampled_from(["alias", "id"])
# Nazwy pól tekstowych spotykane w danych kategorii.
_text_field_names = st.sampled_from(["text", "text1", "text2", "mapText", "description"])


@st.composite
def _entries_with_spec(draw: st.DrawFn) -> tuple[dict[str, object], CategorySpec]:
    """Generuje surowy wpis wraz z pasującą ``CategorySpec`` (model ``ObjectiveDef``).

    Wpis zawsze ma poprawny ``source`` i wartość w polu identyfikatora, więc
    ``build_component`` zbuduje model bez błędu — Property 4 bada zachowanie pól.
    """
    id_field = draw(_id_fields)
    text_fields = tuple(draw(st.lists(_text_field_names, max_size=3, unique=True)))
    window_field = draw(st.sampled_from([None, "window"]))

    entry: dict[str, object] = {
        id_field: draw(_ids),
        "source": draw(_sources),
    }
    # Opcjonalne pola rozpoznawane przez ``build_component`` i ``ComponentBase``.
    if draw(st.booleans()):
        entry["name"] = draw(_words)
    if window_field is not None and draw(st.booleans()):
        entry[window_field] = draw(_words)
    if draw(st.booleans()):
        entry[draw(st.sampled_from(["flavorText", "flavourText"]))] = draw(_words)
    for field_name in text_fields:
        if draw(st.booleans()):
            entry[field_name] = draw(_words)
    # Dodatkowe pole spoza modelu — musi przetrwać w ``raw``.
    if draw(st.booleans()):
        entry["extraField"] = draw(st.integers())

    spec = CategorySpec(
        category=ComponentCategory.PUBLIC_OBJECTIVE,
        directory=Path("."),
        model=ObjectiveDef,
        id_field=id_field,
        text_fields=text_fields,
        window_field=window_field,
    )
    return entry, spec


# Feature: local-ti4-data-foundation, Property 4: Zachowanie pól i surowych danych komponentu
@settings(max_examples=200)
@given(payload=_entries_with_spec())
def test_build_component_zachowuje_pola_i_raw(
    payload: tuple[dict[str, object], CategorySpec],
) -> None:
    """``build_component`` odtwarza pola z JSON i zachowuje surowy wpis bez zmian.

    **Validates: Requirements 5.2, 5.7**
    """
    entry, spec = payload
    component = build_component(entry, spec)

    # Identyfikator pochodzi wyłącznie z pola wskazanego przez specyfikację.
    assert component.id == entry[spec.id_field]
    assert component.source == entry["source"]

    # ``raw`` to wierna kopia wpisu — żadne pole JSON nie ginie (R5.7).
    assert component.raw == entry
    assert component.raw is not entry  # kopia, nie referencja

    # Pola tekstowe: dokładnie te z ``text_fields`` obecne w JSON jako napisy.
    expected_texts = {
        name: entry[name]
        for name in spec.text_fields
        if isinstance(entry.get(name), str)
    }
    assert component.texts == expected_texts

    # Fraza okna odtwarzana tylko gdy specyfikacja ma pole okna.
    if spec.window_field is not None:
        assert component.window == entry.get(spec.window_field)
    else:
        assert component.window is None

    # Flavor text: amerykańska albo brytyjska pisownia, bez preferencji poza JSON.
    expected_flavor = entry.get("flavorText", entry.get("flavourText"))
    assert component.flavor_text == expected_flavor


# Dla Property 5: wartości pola ``points``, których pydantic nie przyjmie jako ``int``.
_invalid_points = st.one_of(
    st.lists(st.integers(), min_size=1, max_size=3),
    st.text(alphabet="xyz", min_size=1, max_size=4),
    st.dictionaries(_ids, st.integers(), min_size=1, max_size=2),
)


# Feature: local-ti4-data-foundation, Property 5: Błąd walidacji niesie kontekst wpisu
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    entry_id=_ids,
    source=_sources,
    file_stem=_ids,
    bad_points=_invalid_points,
)
def test_load_components_zglasza_kontekst_bledu_walidacji(
    tmp_path: Path,
    entry_id: str,
    source: str,
    file_stem: str,
    bad_points: object,
) -> None:
    """Niepoprawny wpis aktywnego źródła → ``DataValidationError`` z kategorią, plikiem i id.

    Buduje na ``tmp_path`` prawdziwy katalog kategorii celów publicznych z jednym
    wpisem, którego pole ``points`` łamie model (``int | None``). ``source`` jest
    kanoniczny, więc wpis przechodzi filtr i trafia do walidacji modelu.

    **Validates: Requirements 5.5**
    """
    # ``tmp_path`` jest współdzielony między przykładami Hypothesis w jednym teście,
    # więc każdy przykład dostaje własny, unikalny podkatalog kategorii.
    category_dir = tmp_path / f"public_objectives_{uuid4().hex}"
    category_dir.mkdir()
    data_file = category_dir / f"{file_stem}.json"
    entry = {
        "alias": entry_id,
        "source": source,
        "name": "Obiekt testowy",
        "points": bad_points,
    }
    data_file.write_text(json.dumps([entry]), encoding="utf-8")

    specs = {
        ComponentCategory.PUBLIC_OBJECTIVE: CategorySpec(
            category=ComponentCategory.PUBLIC_OBJECTIVE,
            directory=category_dir,
            model=ObjectiveDef,
            id_field="alias",
            text_fields=("text",),
        )
    }

    with pytest.raises(DataValidationError) as exc_info:
        load_components([source], specs=specs)

    error = exc_info.value
    # Kontekst błędu wskazuje dokładnie kategorię, plik i identyfikator wpisu (R5.5).
    assert error.category is ComponentCategory.PUBLIC_OBJECTIVE
    assert error.file == data_file
    assert error.entry_id == entry_id
    # Komunikat tekstowy także niesie ten kontekst.
    message = str(error)
    assert ComponentCategory.PUBLIC_OBJECTIVE.value in message
    assert entry_id in message
    assert str(data_file) in message
