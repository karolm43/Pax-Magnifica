/**
 * Motyw menu (`assets/music/main theme.*`) na ekranie startowym: menu, lobby i kreator gry
 * (frakcje, kolory, miejsca). Montowany w `StartScreen`; odmontowanie (wejście do gry) wygasza
 * motyw. Daje też dźwięki kliknięć UI w menu (te same co w grze). Nic nie rysuje.
 */
import { useEffect } from "react";
import { playMenuTheme, stopMenuTheme } from "./music";
import { installUiSounds } from "./uiSounds";

export function MenuMusic() {
  useEffect(() => installUiSounds(), []);
  useEffect(() => {
    playMenuTheme();
    return () => stopMenuTheme();
  }, []);
  return null;
}
