/**
 * Engine nozzles per ship type, shared by the battle overlay and the map flight replay:
 * offsets across the hull axis (fraction of the ship size), flame length (fraction of the
 * ship size) and thickness (px). War sun has none (it emerges from a wormhole); fighters none.
 */
export const ENGINES: Record<
  string,
  { offsets: number[]; length: number; height: number }
> = {
  dd: { offsets: [0], length: 0.22, height: 5 },
  ca: { offsets: [-0.05, 0.05], length: 0.22, height: 4 },
  cv: { offsets: [-0.12, -0.04, 0.04, 0.12], length: 0.16, height: 3 },
  dn: { offsets: [-0.07, 0.07], length: 0.3, height: 6 },
  fs: { offsets: [-0.1, 0, 0.1], length: 0.34, height: 7 },
};
