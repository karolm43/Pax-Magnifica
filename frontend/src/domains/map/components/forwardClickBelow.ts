import type React from "react";

/**
 * Element nad mapą (żeton, punkt nad nadrukiem wormhole) nie może blokować klikania w system:
 * klik jest PRZEKAZYWANY pierwszemu elementowi pod kursorem, który nie jest tym elementem
 * (planeta / cel heksa — zaznaczenie, aktywacja). Prawy klik bąbelkuje sam do menu kafelka.
 */
export function forwardClickBelow(e: React.MouseEvent<HTMLElement>) {
  e.stopPropagation();
  const el = e.currentTarget;
  const under = document
    .elementsFromPoint(e.clientX, e.clientY)
    .find((node) => !el.contains(node));
  under?.dispatchEvent(
    new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      clientX: e.clientX,
      clientY: e.clientY,
    }),
  );
}
