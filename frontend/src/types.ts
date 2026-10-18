// Kontrakt danych z backendem (odpowiada schematom Pydantic w src/api/schemas.py).
// Utrzymywany ręcznie — przy zmianie DTO w backendzie zaktualizuj te typy.

export interface MapTile {
  position: string;
  system_id: string;
  q: number;
  r: number;
  s: number;
  wormholes: string[];
  anomalies: string[];
  planets: string[];
  name: string | null;
  image_url: string | null;
  is_home_slot: boolean;
  home_color: string | null;
  space_units: UnitStack[];
  planet_units: PlanetUnits[];
}

export interface UnitStack {
  player_id: string;
  base_type: string;
  count: number;
  color: string | null;
  image_url: string | null;
}

export interface PlanetUnits {
  planet_id: string;
  owner_id: string | null;
  stacks: UnitStack[];
}

export interface FactionInfo {
  id: string;
  name: string;
  home_system: string | null;
  home_planets: string[];
  starting_fleet: string | null;
  preferred_colours: string[];
}

export type EdgeKind = "adjacent" | "wormhole";

export interface MapEdge {
  a: string;
  b: string;
  kind: EdgeKind;
}

export interface MapView {
  tiles: MapTile[];
  edges: MapEdge[];
}

export interface PlayerState {
  player_id: string;
  faction: string | null;
  color: string | null;
  victory_points: number;
  trade_goods: number;
  commodities: number;
  controlled_planets: string[];
  technologies: string[];
}

export interface GameState {
  round_number: number;
  phase: string;
  active_player_id: string | null;
  players: Record<string, PlayerState>;
  systems: Record<string, unknown>;
}

export interface HistoryInfo {
  can_undo: boolean;
  can_redo: boolean;
  history_size: number;
}

export interface StateEnvelope {
  type: "state";
  state: GameState;
  history: HistoryInfo;
}
