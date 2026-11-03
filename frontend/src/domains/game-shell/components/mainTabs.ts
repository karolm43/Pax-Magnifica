import type { ComponentType } from "react";
import {
  IconLayoutGrid,
  IconMap,
  IconTarget,
  IconUser,
  IconUsers,
} from "@tabler/icons-react";

type Breakpoint = "xs" | "sm" | "md" | "lg" | "xl";

type MainTabValue = "map" | "objectives" | "general" | "player" | "players";

type MainTabConfig = {
  value: MainTabValue;
  label: string;
  Icon: ComponentType<{ size?: number }>;
  visibleFrom?: Breakpoint;
  hideOnMobile?: boolean;
};

export const MAIN_TAB_CONFIGS: MainTabConfig[] = [
  {
    value: "map",
    label: "Map",
    Icon: IconMap,
    visibleFrom: "sm",
  },
  {
    value: "objectives",
    label: "Objectives",
    Icon: IconTarget,
    visibleFrom: "sm",
  },
  {
    value: "general",
    label: "General",
    Icon: IconLayoutGrid,
    visibleFrom: "sm",
  },
  {
    // Zakładka „Player" (liczba pojedyncza, R12.6) — aktywny gracz z pełnymi
    // rękami i kontrolkami akcji (Player_Tab, zadanie 13.2).
    value: "player",
    label: "Player",
    Icon: IconUser,
    visibleFrom: "sm",
  },
  {
    // Zakładka „Players" (liczba mnoga, R12.6) — przegląd wszystkich graczy.
    value: "players",
    label: "Players",
    Icon: IconUsers,
    visibleFrom: "sm",
  },
];
