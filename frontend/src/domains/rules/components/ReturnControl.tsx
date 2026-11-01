/**
 * Kontrolka powrotu przeglądarki Zasad (Rules_Browser, Req 1.3/1.4, 10.3–10.6).
 *
 * Wyznacza cel powrotu przez `useReturnTarget` (zależny od kontekstu otwarcia:
 * z menu głównego → `/` „Menu główne"; z panelu gry → `/game` „Wróć do gry")
 * i renderuje widoczny przycisk, który na aktywację nawiguje `react-router` do
 * `target.path`. Etykieta przycisku to `target.label`.
 *
 * Powrót do panelu gry to zwykła zmiana trasy klienta — NIE invaliduje cache
 * web-data ani nie resetuje stanu rozgrywki (Req 10.4). Wszystkie elementy
 * wizualne pochodzą wyłącznie z design systemu (`@/ds`).
 */

import { useNavigate } from "react-router-dom";
import { IconArrowLeft } from "@tabler/icons-react";
import { Button } from "@/ds";
import { useReturnTarget } from "@/domains/rules/hooks/useReturnTarget";

/**
 * Renderuje przycisk powrotu kierujący do celu z `useReturnTarget`.
 *
 * Bezstanowy; montowany w układzie strony (`RulesBrowserPage`, zadanie 10.1).
 */
export function ReturnControl() {
  const navigate = useNavigate();
  const target = useReturnTarget();

  return (
    <Button
      variant="subtle"
      size="sm"
      leftSection={<IconArrowLeft size={16} aria-hidden="true" />}
      onClick={() => navigate(target.path)}
    >
      {target.label}
    </Button>
  );
}
