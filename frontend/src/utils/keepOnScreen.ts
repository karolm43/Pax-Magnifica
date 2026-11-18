/**
 * Przesunięcie okna przeciąganego za uchwyt, przycięte tak, żeby okno zostało CAŁE na ekranie
 * (każde przeciągane okno: pływające ``Modal``, stół kart strategii; ``useDraggablePanel`` ma
 * własne przycinanie). ``rect`` = prostokąt okna w chwili chwycenia, ``dx/dy`` = ruch kursora od
 * tej chwili. Okno większe od ekranu może się przesuwać tylko tak, by któraś krawędź była widać.
 */
export function clampDragDelta(
  rect: { left: number; top: number; right: number; bottom: number },
  dx: number,
  dy: number,
  margin = 4,
): { dx: number; dy: number } {
  const range = (low: number, high: number, v: number) =>
    Math.min(Math.max(v, Math.min(low, high)), Math.max(low, high));
  return {
    dx: range(margin - rect.left, window.innerWidth - margin - rect.right, dx),
    dy: range(margin - rect.top, window.innerHeight - margin - rect.bottom, dy),
  };
}
