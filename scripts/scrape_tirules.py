"""Jednorazowy parser: fragmenty HTML (.php) z repo tirules -> MD + JSON.

Wejście: katalog z plikami R_*.php / F_*.php / C_*.php pobranymi z
https://github.com/dangothemango/tirules (GPL-3.0; treść reguł (c) FFG).
Wyjście: docs/rules_tirules/<kod>.md (po jednym na temat) + tirules.json (zbiorczy).

Skrypt NIE jest częścią silnika — to narzędzie do wygenerowania statycznego
offline'owego źródła reguł. Parser oparty wyłącznie na stdlib (html.parser).
"""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

REPO_URL = "https://github.com/dangothemango/tirules"
SITE_BASE = "https://www.tirules2.com"

KATEGORIE = {"R": "rule", "F": "faction", "C": "component"}

# Luźny alias dla serializowanego JSON (narzędzie jednorazowe).
Json = dict[str, object]


# --- Model drzewa treści -------------------------------------------------


@dataclass
class ListaItem:
    """Pozycja listy (li) z zagnieżdżonymi podlistami."""

    tekst: str
    ruling: bool = False  # czy to ruling Dane (span class="ruling")
    subheading: bool = False  # śródtytuł LRR (<h2><li>...</li></h2> wewnątrz listy)
    para: bool = False  # akapit <p> wstawiony wewnątrz listy (bez myślnika)
    dzieci: list[ListaItem] = field(default_factory=list)


@dataclass
class Sekcja:
    """Sekcja h2 wewnątrz artykułu."""

    naglowek: str
    paragrafy: list[str] = field(default_factory=list)
    pozycje: list[ListaItem] = field(default_factory=list)
    lista_lrr: bool = False  # czy główna lista to ol.lrr (oficjalny LRR)


# --- Parser HTML ----------------------------------------------------------

# Inline tagi zamieniane na markdown.
INLINE_OPEN = {"b": "**", "strong": "**", "i": "*", "em": "*"}
INLINE_CLOSE = {"b": "**", "strong": "**", "i": "*", "em": "*"}


class TiruleParser(HTMLParser):
    """Parsuje jeden fragment HTML tirules do tytułu + listy sekcji."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tytul: str = ""
        self.sekcje: list[Sekcja] = []

        self._w_header = False
        self._w_h2 = False
        self._h2_w_liscie = False  # <h2> jako śródtytuł wewnątrz listy LRR
        self._p_w_liscie = False  # <p> wstawiony wewnątrz listy
        self._w_p = False
        self._buf: list[str] = []  # bufor tekstu bieżącego elementu

        # stos list: każdy wpis to lista rodzeństwa (list[ListaItem])
        self._stos_list: list[list[ListaItem]] = []
        self._stos_li: list[ListaItem] = []  # aktualnie otwarte li
        self._li_ruling = False
        self._sekcja: Sekcja | None = None
        self._pending_lrr = False  # następna ol ma klasę lrr
        self._href: str | None = None
        self._a_pominiety = False
        self._sup_start: int | None = None  # początek <sup> w buforze (przypisy)

    # -- pomocnicze --
    def _flush(self) -> str:
        t = "".join(self._buf)
        self._buf = []
        # normalizacja białych znaków
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "sup":
            self._sup_start = len(self._buf)
            return
        if tag == "a" and (self._w_h2 or self._h2_w_liscie):
            # link w nagłówku (upstream: do wiki) — sam tekst
            self._a_pominiety = True
            return
        if tag == "header":
            self._w_header = True
            self._buf = []
        elif tag == "h1":
            self._buf = []
        elif tag == "br":
            self._buf.append(" / ")
        elif tag == "h2":
            # <h2> wewnątrz otwartej listy = śródtytuł LRR (<h2><li>Costs</li></h2>),
            # NIE nowa sekcja — nie zamykamy listy, zbieramy jako etykietę grupy.
            if self._stos_list:
                self._h2_w_liscie = True
                self._buf = []
            else:
                self._zakoncz_paragraf()
                self._zamknij_wszystkie_listy()
                self._w_h2 = True
                self._buf = []
        elif tag == "p":
            # <p> wewnątrz otwartej listy (tirules wstawia akapity między <li>) —
            # NIE zamykamy listy; treść trafi jako pozycja-akapit zachowując kolejność.
            if self._stos_list:
                self._p_w_liscie = True
            else:
                self._p_w_liscie = False
            self._w_p = True
            self._buf = []
        elif tag in ("ol", "ul"):
            klasa = (a.get("class") or "")
            if "lrr" in klasa and self._sekcja is not None and not self._stos_list:
                self._sekcja.lista_lrr = True
            # nowa lista. W tirules zagnieżdżone <ol> bywają rodzeństwem <li>
            # (nie dzieckiem), więc dowiązujemy je do OSTATNIEJ pozycji rodzica.
            nowa: list[ListaItem] = []
            if self._stos_li:
                # podlista wewnątrz otwartego <li>
                self._stos_li[-1].dzieci = nowa
            elif self._stos_list and self._stos_list[-1]:
                # <ol> jako rodzeństwo: dowiąż do ostatniego li bieżącej listy
                self._stos_list[-1][-1].dzieci = nowa
            elif self._sekcja is not None:
                # lista najwyższego poziomu w sekcji. Sekcja może mieć ich kilka
                # (tirules bywa, że wstawia drugą <ol> po akapicie) — scalamy
                # pozycje w jedną listę sekcji, zachowując kolejność.
                if not self._sekcja.pozycje:
                    self._sekcja.pozycje = nowa
                else:
                    nowa = self._sekcja.pozycje
            self._stos_list.append(nowa)
        elif tag == "li":
            # <li> wewnątrz <h2> (śródtytuł LRR) — tekst zbieramy do bufora h2, nie tworzymy pozycji
            if self._h2_w_liscie:
                return
            # auto-zamknięcie poprzedniego <li> na tym samym poziomie (gdy źródło gubi </li>)
            if self._li_jest_rodzenstwem():
                self._zamknij_li()
            self._buf = []
            self._li_ruling = False
            item = ListaItem(tekst="")
            self._li_ruling = "ruling" in (a.get("class") or "")
            item.ruling = self._li_ruling
            if self._stos_list:
                self._stos_list[-1].append(item)
            self._stos_li.append(item)
        elif tag == "span":
            if "ruling" in (a.get("class") or "") and self._stos_li:
                self._stos_li[-1].ruling = True
        elif tag == "a":
            self._href = a.get("href")
            self._buf.append("[")
        elif tag in INLINE_OPEN:
            self._buf.append(INLINE_OPEN[tag])
        elif tag == "sc":
            self._buf.append("`")
        elif tag == "code":
            self._buf.append("`")

    def handle_endtag(self, tag: str) -> None:
        if tag == "sup":
            # przypisy źródłowe upstreamu (<sup>1,2</sup>) pomijamy; <sup>th</sup> zostaje
            if self._sup_start is not None:
                tekst = "".join(self._buf[self._sup_start :])
                if re.fullmatch(r"[\d,\s]*", tekst):
                    del self._buf[self._sup_start :]
                self._sup_start = None
            return
        if tag == "a" and self._a_pominiety:
            self._a_pominiety = False
            return
        if tag == "header":
            self._w_header = False
        elif tag == "h1":
            self.tytul = self._flush()
        elif tag == "h2":
            if self._h2_w_liscie:
                # śródtytuł LRR: dodaj jako pozycję-etykietę do bieżącej listy
                etykieta = self._flush()
                if etykieta and self._stos_list:
                    self._stos_list[-1].append(
                        ListaItem(tekst=etykieta, subheading=True)
                    )
                self._h2_w_liscie = False
            else:
                self._sekcja = Sekcja(naglowek=self._flush())
                self.sekcje.append(self._sekcja)
                self._w_h2 = False
        elif tag == "p":
            txt = self._flush()
            if self._p_w_liscie and self._stos_list:
                # akapit wewnątrz listy — pozycja-akapit (zachowuje kolejność, bez myślnika)
                if txt:
                    self._stos_list[-1].append(ListaItem(tekst=txt, para=True))
                self._p_w_liscie = False
                self._w_p = False
                return
            if txt and self._sekcja is not None:
                self._sekcja.paragrafy.append(txt)
            elif txt and self._sekcja is None:
                # paragraf przed pierwszym h2 -> sekcja wstępna
                if not self.sekcje or self.sekcje[0].naglowek != "":
                    self.sekcje.insert(0, Sekcja(naglowek=""))
                    self._sekcja_wstepna = self.sekcje[0]
                self.sekcje[0].paragrafy.append(txt)
            self._w_p = False
        elif tag == "li":
            if self._h2_w_liscie:
                return  # </li> w śródtytule — tekst zostaje w buforze do </h2>
            if self._stos_li:
                item = self._stos_li.pop()
                item.tekst = self._flush()
        elif tag in ("ol", "ul"):
            # domknij otwarty <li> tej listy (gdy źródło gubi </li> przed </ol>)
            if self._li_jest_rodzenstwem():
                self._zamknij_li()
            if self._stos_list:
                self._stos_list.pop()
        elif tag == "a":
            href = self._href or ""
            if href.startswith("/"):
                href = SITE_BASE + href
            self._buf.append(f"]({href})")
            self._href = None
        elif tag in INLINE_CLOSE:
            self._buf.append(INLINE_CLOSE[tag])
        elif tag in ("sc", "code"):
            self._buf.append("`")

    def handle_data(self, data: str) -> None:
        self._buf.append(data)

    def _zamknij_li(self) -> None:
        """Domyka bieżący <li> (gdy źródło gubi </li>). Flushuje tekst, zdejmuje ze stosu."""
        if self._stos_li:
            item = self._stos_li.pop()
            item.tekst = self._flush()

    def _li_jest_rodzenstwem(self) -> bool:
        """Czy otwarty <li> należy do listy na szczycie stosu (= rodzeństwo nowego <li>)."""
        return bool(
            self._stos_li
            and self._stos_list
            and self._stos_list[-1]
            and self._stos_list[-1][-1] is self._stos_li[-1]
        )

    def _zamknij_wszystkie_listy(self) -> None:
        """Domyka wszystkie otwarte <li> i listy (przy <h2> / nowej sekcji)."""
        while self._stos_li:
            self._zamknij_li()
        self._stos_list = []

    def _zakoncz_paragraf(self) -> None:
        if self._w_p:
            txt = self._flush()
            if txt and self._sekcja is not None:
                self._sekcja.paragrafy.append(txt)
            self._w_p = False


# --- Serializacja ---------------------------------------------------------


def _czysty_tekst(md: str) -> str:
    """Usuwa markdown/formatowanie do czystego tekstu (dla pola JSON)."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)  # linki -> sam tekst
    t = t.replace("**", "").replace("`", "")
    t = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", t)  # *i*
    return t.strip()


def _item_na_md(item: ListaItem, poziom: int, lrr: bool) -> list[str]:
    wciecie = "    " * poziom
    if item.subheading:
        # śródtytuł LRR — pogrubiona etykieta grupy (pusta linia dla czytelności)
        return ["", f"{wciecie}**{item.tekst}**", ""]
    if item.para:
        # akapit wstawiony w liście — bez myślnika, z pustymi liniami wokół
        return ["", f"{wciecie}{item.tekst}", ""]
    tekst = item.tekst
    if item.ruling:
        tekst = f"_[Dane ruling]_ {tekst}"
    linie = [f"{wciecie}- {tekst}"]
    for dz in item.dzieci:
        linie += _item_na_md(dz, poziom + 1, lrr)
    return linie


def _item_na_json(item: ListaItem) -> Json:
    d: Json = {"text": _czysty_tekst(item.tekst)}
    if item.subheading:
        d["subheading"] = True
    if item.para:
        d["paragraph"] = True
    if item.ruling:
        d["dane_ruling"] = True
    if item.dzieci:
        d["children"] = [_item_na_json(x) for x in item.dzieci]
    return d


def render_md(kod: str, tytul: str, sekcje: list[Sekcja], url: str) -> str:
    out: list[str] = [f"# {tytul}", ""]
    out.append(f"> Źródło: [{url}]({url}) — treść reguł © Fantasy Flight Games.")
    out.append("> Zrzut z repo tirules (GPL-3.0). Patrz `SOURCE.md`.")
    out.append("")
    for s in sekcje:
        if s.naglowek:
            out.append(f"## {s.naglowek}")
            out.append("")
        for p in s.paragrafy:
            out.append(p)
            out.append("")
        for item in s.pozycje:
            out += _item_na_md(item, 0, s.lista_lrr)
        if s.pozycje:
            out.append("")
    # sprzątanie podwójnych pustych linii na końcu
    txt = "\n".join(out).rstrip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", txt)


def sekcje_na_json(sekcje: list[Sekcja]) -> list[Json]:
    res: list[Json] = []
    for s in sekcje:
        res.append(
            {
                "heading": s.naglowek,
                "is_lrr": s.lista_lrr,
                "paragraphs": [_czysty_tekst(p) for p in s.paragrafy],
                "items": [_item_na_json(i) for i in s.pozycje],
            }
        )
    return res


# --- Main -----------------------------------------------------------------


def main() -> int:
    src_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    pliki = sorted(src_dir.glob("[RFC]_*.php"))
    topics: list[Json] = []
    zbior: dict[str, object] = {
        "source_repo": REPO_URL,
        "source_site": SITE_BASE,
        "license": "GPL-3.0 (repo); rules text (c) Fantasy Flight Games",
        "topics": topics,
    }

    for p in pliki:
        html_txt = p.read_text(encoding="utf-8")
        # wytnij include'y php
        html_txt = re.sub(r"<\?php.*?\?>", "", html_txt, flags=re.S)
        parser = TiruleParser()
        parser.feed(html_txt)

        kod = p.stem  # np. R_anomalies
        kat = KATEGORIE.get(kod[0], "other")
        url = f"{SITE_BASE}/{kod}"
        tytul = html.unescape(parser.tytul) or kod

        md = render_md(kod, tytul, parser.sekcje, url)
        (out_dir / f"{kod}.md").write_text(md, encoding="utf-8")

        topics.append(
            {
                "code": kod,
                "category": kat,
                "title": tytul,
                "url": url,
                "sections": sekcje_na_json(parser.sekcje),
            }
        )

    (out_dir / "tirules.json").write_text(
        json.dumps(zbior, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # INDEX.md — spis tematów z linkami
    etykiety = {"rule": "Reguły (R)", "faction": "Frakcje (F)", "component": "Komponenty (C)"}
    idx: list[str] = [
        "# Spis tematów — zrzut tirules2.com",
        "",
        f"Łącznie **{len(pliki)}** tematów. Źródło i licencja: [`SOURCE.md`](SOURCE.md).",
        "Dane strukturalne: [`tirules.json`](tirules.json).",
        "",
    ]
    for kat in ("rule", "faction", "component"):
        pozycje = [t for t in topics if t["category"] == kat]
        idx.append(f"## {etykiety[kat]} — {len(pozycje)}")
        idx.append("")
        for t in sorted(pozycje, key=lambda x: str(x["title"])):
            idx.append(f"- [{t['title']}]({t['code']}.md)")
        idx.append("")
    (out_dir / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")

    print(f"OK: {len(pliki)} plikow -> {out_dir}")
    print(f"  MD: {len(pliki)}  +  tirules.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
