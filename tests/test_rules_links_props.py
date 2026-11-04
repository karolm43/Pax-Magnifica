"""Testy właściwościowe powiązań komponentów z tematami zrzutu reguł.

Weryfikują ``RulesTopicIndex.match`` z ``src/core/rules_links.py``:
dopasowanie jest deterministyczne, zwraca wyłącznie tematy z indeksu i nie
zależy od wielkości liter ani znaków niealfanumerycznych w nazwie.
"""

from __future__ import annotations

import string

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.rules_links import _CODE_PREFIX, RulesTopic, RulesTopicIndex, normalize


def _match_keys(topics: list[RulesTopic]) -> set[str]:
    """Zbiór kluczy, pod którymi indeks rejestruje tematy (mirror ``__init__``).

    Klucze: znormalizowany tytuł, kod i kod bez prefiksu kategorialnego
    (``_CODE_PREFIX`` — pojedyncza wielka litera + ``_``). Puste klucze pomijane.
    """
    keys: set[str] = set()
    for topic in topics:
        for raw in (topic.title, topic.code, _CODE_PREFIX.sub("", topic.code)):
            key = normalize(raw)
            if key:
                keys.add(key)
    return keys

# Generator kodów tematów: krótki napis alfanumeryczny z opcjonalnym prefiksem
# kategorialnym (np. "C_action_cards"), by pokryć normalizację prefiksu.
_code_body = st.text(alphabet=string.ascii_letters + string.digits + "_", min_size=1, max_size=12)
_codes = st.builds(
    lambda prefix, body: f"{prefix}{body}" if prefix else body,
    st.sampled_from(["", "C_", "F_", "R_"]),
    _code_body,
)
_categories = st.sampled_from(["rule", "faction", "component"])
# Tytuły: dowolny tekst z literami, cyframi, spacjami i interpunkcją, by
# normalizacja (casefold + usunięcie znaków niealfanumerycznych) miała co robić.
_titles = st.text(
    alphabet=string.ascii_letters + string.digits + " -'/.()",
    min_size=1,
    max_size=24,
)


@st.composite
def _topics(draw: st.DrawFn) -> list[RulesTopic]:
    """Lista tematów o UNIKALNYCH kodach (indeks kluczuje po kodzie)."""
    n = draw(st.integers(min_value=0, max_value=8))
    codes: list[str] = []
    seen: set[str] = set()
    for _ in range(n):
        code = draw(_codes)
        if code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return [
        RulesTopic(code=code, category=draw(_categories), title=draw(_titles)) for code in codes
    ]


def _apply_case(text: str, flags: tuple[bool, ...]) -> str:
    """Nakłada wzorzec wielkości liter: ``True`` -> wielka, ``False`` -> mała."""
    return "".join(c.upper() if f else c.lower() for c, f in zip(text, flags, strict=True))


def _scramble_case(text: str) -> st.SearchStrategy[str]:
    """Zwraca strategię generującą wariant ``text`` z losową wielkością liter."""
    return st.tuples(*(st.booleans() for _ in text)).map(lambda flags: _apply_case(text, flags))


# Feature: local-ti4-data-foundation, Property 16: Powiązanie z tematami reguł
# jest deterministyczne i zawarte w indeksie.
@settings(max_examples=100)
@given(topics=_topics(), names=st.lists(st.text(max_size=30), max_size=5))
def test_match_zwraca_podzbior_indeksu(topics: list[RulesTopic], names: list[str]) -> None:
    """**Validates: Requirements 10.1, 10.2, 10.3**

    Wynik ``match`` jest podzbiorem tematów indeksu, nie zawiera duplikatów,
    a brak trafienia daje pustą listę bez wyjątku (R10.1, R10.3).
    """
    index = RulesTopicIndex(topics)
    index_codes = {t.code for t in topics}

    result = index.match(*names)

    # Wyłącznie tematy z indeksu (R10.1).
    assert all(topic in topics for topic in result)
    assert {topic.code for topic in result} <= index_codes
    # Bez duplikatów.
    codes = [topic.code for topic in result]
    assert len(codes) == len(set(codes))
    # Pusta lista, gdy żadna nazwa nie pasuje (R10.3) — bez wyjątku.
    keys = _match_keys(topics)
    if not any(normalize(name) in keys for name in names if normalize(name)):
        assert result == []


# Feature: local-ti4-data-foundation, Property 16: dopasowanie jest deterministyczne
# i niewrażliwe na wielkość liter oraz znaki niealfanumeryczne (R10.2).
@settings(max_examples=100)
@given(data=st.data(), topics=_topics())
def test_match_po_tytule_niewrazliwe_na_normalizacje(
    data: st.DataObject, topics: list[RulesTopic]
) -> None:
    """**Validates: Requirements 10.1, 10.2**

    Dopasowanie po tytule tematu nie zależy od wielkości liter ani wstawionych
    znaków niealfanumerycznych w nazwie komponentu.
    """
    # Potrzebny temat o niepustym kluczu normalizacji, by dało się trafić.
    candidates = [t for t in topics if normalize(t.title)]
    if not candidates:
        return
    topic = data.draw(st.sampled_from(candidates))
    index = RulesTopicIndex(topics)

    # Wariant nazwy: tytuł z losową wielkością liter i wstawionymi separatorami.
    scrambled = data.draw(_scramble_case(topic.title))
    noise = data.draw(st.sampled_from(["", " ", "-", "__", " / "]))
    name_variant = noise.join(scrambled)

    baseline = index.match(topic.title)
    variant = index.match(name_variant)

    # Determinizm: ponowne wywołanie daje ten sam wynik.
    assert index.match(name_variant) == variant
    # Niewrażliwość na normalizację: ten sam zestaw kodów co dla czystego tytułu.
    assert {t.code for t in variant} == {t.code for t in baseline}
    # Trafiony temat musi być w wyniku (klucz niepusty).
    assert topic.code in {t.code for t in variant}


# Feature: local-ti4-data-foundation, Property 16: nazwa bez trafienia daje pustą
# listę bez wyjątku (R10.3).
@settings(max_examples=100)
@given(topics=_topics(), name=st.text(max_size=40))
def test_match_bez_trafienia_zwraca_puste(topics: list[RulesTopic], name: str) -> None:
    """**Validates: Requirements 10.3**"""
    index = RulesTopicIndex(topics)
    key = normalize(name)

    result = index.match(name)

    if not key or key not in _match_keys(topics):
        assert result == []
