import { toPng } from "html-to-image";

/*
 * Zrzut tego, co gracz widzi — render DOM-u do PNG w przeglądarce (html-to-image). Grafiki
 * idą z tego samego originu (`/static`), więc canvas nie jest „skażony" CORS-em. Elementy
 * z `data-bug-report-ignore` (sam przycisk zgłoszenia, okno) są pomijane. Sceny WebGL bez
 * `preserveDrawingBuffer` (kostki 3D) mogą wyjść puste — reszta widoku jest kompletna.
 *
 * `pixelRatio` ograniczony do 1,5: na ekranach HiDPI pełna gęstość dawała pliki po
 * kilkadziesiąt MB i długi zrzut, a do raportu wystarcza czytelny obraz.
 */
const MAX_PIXEL_RATIO = 1.5;

function keepNode(node: HTMLElement): boolean {
  return !(node instanceof HTMLElement && node.dataset?.bugReportIgnore !== undefined);
}

export async function captureScreenshot(): Promise<string | null> {
  try {
    return await toPng(document.body, {
      width: window.innerWidth,
      height: window.innerHeight,
      pixelRatio: Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO),
      backgroundColor: getComputedStyle(document.body).backgroundColor || "#000",
      cacheBust: false,
      filter: keepNode,
    });
  } catch (err) {
    // Brak zrzutu nie blokuje zgłoszenia — opis i stan gry i tak trafią do hosta.
    console.warn("[bug-report] screenshot failed", err);
    return null;
  }
}
