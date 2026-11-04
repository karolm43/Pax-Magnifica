"""Punkt wejścia pakietu Audytora_Danych: ``python -m src.audit``.

Deleguje do ``src.audit.report.main`` i zwraca jego kod wyjścia (≠ 0 przy błędach
krytycznych, 0 przy samych ostrzeżeniach). Opcje: ``--write-baseline``,
``--write-manifest``, ``--json``.
"""

from __future__ import annotations

import sys

from src.audit.report import main

if __name__ == "__main__":
    sys.exit(main())
