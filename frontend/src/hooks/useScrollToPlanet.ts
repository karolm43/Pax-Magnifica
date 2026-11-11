import { useEffect } from "react";
import { useAppStore } from "@/state/appStore";
import { findSearchHits, jumpToSearchHit } from "@/domains/search/searchHits";
import { searchKey } from "@/domains/search/searchKeys";

/**
 * Klik w kartę planety (pole gracza) ustawia `scrollToPlanetId` — przewijamy mapę
 * do tej planety na planszy i na chwilę ją podświetlamy, potem czyścimy żądanie,
 * żeby tę samą planetę dało się wskazać ponownie. Pozycję daje sam DOM (znacznik
 * wyszukiwarki na planecie), więc zoom i marginesy planszy liczą się same.
 */
export function useScrollToPlanet() {
  const scrollToPlanetId = useAppStore((state) => state.scrollToPlanetId);
  const setScrollToPlanetId = useAppStore((state) => state.setScrollToPlanetId);

  useEffect(() => {
    if (!scrollToPlanetId) return;
    setScrollToPlanetId(null);
    const onBoard = findSearchHits([searchKey("planet", scrollToPlanetId)], true);
    if (onBoard[0]) jumpToSearchHit(onBoard[0]);
  }, [scrollToPlanetId, setScrollToPlanetId]);
}
