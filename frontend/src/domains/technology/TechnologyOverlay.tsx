import { useMemo, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import {
  IconArrowLeft,
  IconArrowsExchange,
  IconBolt,
  IconCheck,
  IconCpu,
  IconEye,
  IconLock,
  IconMinus,
  IconPlus,
  IconSparkles,
  IconX,
} from "@tabler/icons-react";
import { getTechData } from "@/entities/lookup/tech";
import { getBreakthroughData } from "@/entities/lookup/breakthroughs";
import { Tooltip } from "@/ds";
import { TechCard } from "@/domains/cards/components/TechCard/TechCard";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import {
  AIDA_SKIP,
  COLOR_HUE,
  COLOR_ICON,
  COLUMNS,
  autoPay,
  compoundChoices,
  autoSkips,
  layoutColumns,
  otherTechs,
  remainingAfter,
  tier,
  totalMissing,
  unitUpgrades,
  type BreakthroughInfo,
  type ResearchOptions,
  type TechColor,
  type TechRow,
} from "./techModel";
import styles from "./TechnologyOverlay.module.css";

/*
 * OKNO BADANIA TECHNOLOGII (RULES.md 49) - pełny ekran, w stylu okna produkcji.
 * [pasek: tytuł, kolory posiadane, koszt, „pokaż planszę"]
 * [drzewo: 4 kolumny kolorów × poziomy prerekwizytów + połączenia | ulepszenia jednostek]
 * [panel: wybrana technologia, prerekwizyty, specjalności planet do wyczerpania, płatność]
 * [dok: zbadane w tej akcji | rezygnacja | Research].
 * Silnik waliduje wszystko (`plan_research`); UI tylko podpowiada i dobiera automatycznie.
 */

export type TechnologyOverlayProps = {
  options: ResearchOptions;
  title: string;
  subtitle: string;
  /** Kolor gracza jako składowe RGB oddzielone spacjami (`rgb(var(--att-rgb) / a)`). */
  playerRgb: string;
  playerName: string;
  faction?: string | null;
  busy: boolean;
  /** Etykieta przycisku rezygnacji (np. „Don't research"); brak = brak przycisku. */
  declineLabel?: string;
  onDecline?: () => void;
  onBack?: () => void;
  onResearch: (payload: ResearchPayload) => void;
};

export type ResearchPayload = {
  tech: string;
  skips: string[];
  planets: string[];
  trade_goods: number;
  /** Specialist Compounds: planeta ze specjalnością płaci zamiast zasobów. */
  compound_planet?: string;
};

const STATUS_LABEL: Record<TechRow["status"], string> = {
  owned: "Owned",
  exhausted: "Owned · exhausted",
  available: "Can research",
  skippable: "Needs a specialty",
  locked: "Locked",
};

const COLOR_NAME: Record<TechColor, string> = {
  PROPULSION: "propulsion",
  BIOTIC: "biotic",
  CYBERNETIC: "cybernetic",
  WARFARE: "warfare",
};

function Pips({ colors, size = 14 }: { colors: TechColor[]; size?: number }) {
  if (colors.length === 0)
    return <span className={styles.noPrereq}>no prerequisites</span>;
  return (
    <span className={styles.pips}>
      {colors.map((c, i) => (
        <img
          key={`${c}-${i}`}
          src={COLOR_ICON[c]}
          alt={COLOR_NAME[c]}
          width={size}
          height={size}
        />
      ))}
    </span>
  );
}

function TechTile({
  row,
  selected,
  onPath,
  onSelect,
}: {
  row: TechRow;
  selected: boolean;
  onPath: boolean;
  onSelect: () => void;
}) {
  const hue = row.color ? COLOR_HUE[row.color] : "170 178 196";
  const owned = row.status === "owned" || row.status === "exhausted";
  const missingCount = totalMissing(row.missing);
  return (
    // Najechanie pokazuje tę samą kartę technologii co w panelach graczy (TechCard).
    <Tooltip
      label={<TechCard techId={row.id} />}
      openDelay={350}
      position="right"
      offset={10}
      multiline
      className={styles.techTooltip}
      events={{ hover: true, focus: true, touch: false }}
    >
      <button
        type="button"
        className={styles.tile}
        style={{ "--tc": hue } as CSSProperties}
        data-status={row.status}
        data-selected={selected || undefined}
        data-path={onPath || undefined}
        onClick={onSelect}
        aria-label={`${row.name} - ${STATUS_LABEL[row.status]}`}
      >
        <span className={styles.tileTop}>
          {row.faction ? (
            <span className={styles.tileFaction}>
              <CircularFactionIcon faction={row.faction} size={16} />
            </span>
          ) : null}
          <span className={styles.tileName}>{row.name}</span>
          <span className={styles.tileState}>
            {owned ? (
              <IconCheck size={14} aria-hidden="true" />
            ) : row.status === "locked" ? (
              <IconLock size={13} aria-hidden="true" />
            ) : row.status === "skippable" ? (
              <IconSparkles size={13} aria-hidden="true" />
            ) : null}
          </span>
        </span>
        <span className={styles.tileBottom}>
          <Pips colors={row.prerequisites} size={13} />
          {!owned && missingCount > 0 ? (
            <span className={styles.tileMissing}>-{missingCount}</span>
          ) : null}
        </span>
      </button>
    </Tooltip>
  );
}

export function TechnologyOverlay(props: TechnologyOverlayProps) {
  const { options, busy } = props;
  const [hidden, setHidden] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skips, setSkips] = useState<string[]>([]);
  const [payment, setPayment] = useState<{
    planets: string[];
    tradeGoods: number;
  } | null>(null);
  const [compound, setCompound] = useState<string | null>(null);

  const grid = useMemo(() => layoutColumns(options.tree), [options.tree]);
  const upgrades = useMemo(() => unitUpgrades(options.tree), [options.tree]);
  const others = useMemo(() => otherTechs(options.tree), [options.tree]);
  const selected = options.tree.find((r) => r.id === selectedId) ?? null;
  const researchable =
    selected != null &&
    (selected.status === "available" || selected.status === "skippable");

  const select = (row: TechRow) => {
    setSelectedId(row.id);
    const auto = autoSkips(row, options);
    const nextSkips = row.status === "skippable" ? auto.skips : [];
    setSkips(nextSkips);
    setPayment(null); // płatność liczona automatycznie, dopóki gracz nie zmieni ręcznie
    setCompound(null);
  };

  const left = selected ? remainingAfter(selected, skips, options) : {};
  const stillMissing = selected ? totalMissing(left) : 0;
  const pay =
    payment ??
    autoPay(options.planets, skips, options.tradeGoods, options.cost);
  const paid =
    pay.planets.reduce((s, id) => s + (options.planets[id] ?? 0), 0) +
    pay.tradeGoods;
  const compoundOptions = compoundChoices(selected, options, skips);
  const compoundUsed = compound != null && compoundOptions.includes(compound);
  const short = compoundUsed ? 0 : Math.max(0, options.cost - paid);
  const canResearch =
    researchable && stillMissing === 0 && short === 0 && !busy;

  const togglePlanetSkip = (planet: string) =>
    setSkips((cur) =>
      cur.includes(planet) ? cur.filter((p) => p !== planet) : [...cur, planet],
    );
  const togglePay = (planet: string) => {
    const base = pay;
    setPayment({
      ...base,
      planets: base.planets.includes(planet)
        ? base.planets.filter((p) => p !== planet)
        : [...base.planets, planet],
    });
  };
  const stepTg = (delta: number) =>
    setPayment({
      ...pay,
      tradeGoods: Math.max(
        0,
        Math.min(options.tradeGoods, pay.tradeGoods + delta),
      ),
    });

  // Ścieżka: posiadane technologie, które spełniają prerekwizyty wybranej.
  const pathColors = new Set(selected?.prerequisites ?? []);
  const onPath = (row: TechRow) =>
    selected != null &&
    row.id !== selected.id &&
    (row.status === "owned" || row.status === "exhausted") &&
    row.color != null &&
    pathColors.has(row.color);

  const ownedCount = (c: TechColor) => options.ownedColors[c] ?? 0;
  const synergyPair = options.breakthrough?.synergy ?? [];
  const synergyActive = options.breakthrough?.active === true;
  const specialtyPlanets = Object.keys(options.specialties);
  const payPlanets = Object.keys(options.planets)
    .filter((id) => !skips.includes(id))
    .sort(
      (a, b) =>
        (options.planets[b] ?? 0) - (options.planets[a] ?? 0) ||
        a.localeCompare(b),
    );

  if (hidden) {
    return createPortal(
      <button
        type="button"
        className={styles.returnPill}
        onClick={() => setHidden(false)}
      >
        <IconCpu size={16} aria-hidden="true" />
        Open technology research
      </button>,
      document.body,
    );
  }

  const selectedText = selected ? getTechData(selected.id)?.text : undefined;

  return createPortal(
    <div
      className={styles.overlay}
      // Okno pełnoekranowe: dok ręki zwija się do paska, a okno rezerwuje pod nim miejsce.
      data-fullscreen-overlay=""
      style={{ "--att-rgb": props.playerRgb } as CSSProperties}
      role="dialog"
      aria-label="Technology research"
    >
      <div className={styles.backdrop} aria-hidden="true" />

      <header className={styles.topBar}>
        <div className={styles.title}>
          <IconCpu size={20} aria-hidden="true" />
          {props.title}
          <small>{props.subtitle}</small>
        </div>
        <div className={styles.topStats}>
          {COLUMNS.map((c) => (
            <span
              key={c.color}
              className={styles.stat}
              style={{ "--tc": c.hue } as CSSProperties}
              data-kind="color"
            >
              <img src={c.icon} alt="" width={14} height={14} />{" "}
              <b>{ownedCount(c.color)}</b> {c.label}
            </span>
          ))}
          {options.cost > 0 ? (
            <span className={styles.stat} data-kind="cost">
              Cost <b>{options.cost}</b> resources
            </span>
          ) : (
            <span className={styles.stat} data-kind="free">
              <b>Free</b> research
            </span>
          )}
        </div>
        {/* Psychoarchaeology, AI Development Algorithm - wpływają na badanie. */}
        <ActiveTechs context="technology" faction={props.faction} />
        <div className={styles.topActions}>
          <span className={styles.player}>
            {props.faction ? (
              <CircularFactionIcon faction={props.faction} size={22} />
            ) : null}
            {props.playerName}
          </span>
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => setHidden(true)}
          >
            <IconEye size={15} aria-hidden="true" /> Show board
          </button>
        </div>
      </header>

      {options.researched.length > 0 ? (
        <p className={styles.notice}>
          <IconCheck size={14} aria-hidden="true" /> Researched this action:{" "}
          <b>
            {options.researched
              .map((id) => getTechData(id)?.name ?? id)
              .join(", ")}
          </b>
        </p>
      ) : null}

      <div className={styles.grid}>
        <section className={styles.panel} aria-label="Technology tree">
          <div className={styles.tree}>
            {COLUMNS.map((c) => (
              <div
                key={c.color}
                className={styles.column}
                style={{ "--tc": c.hue } as CSSProperties}
              >
                <div className={styles.columnHead}>
                  <img src={c.icon} alt="" width={22} height={22} />
                  <span>{c.label}</span>
                  {synergyPair.includes(c.color) ? (
                    <span
                      className={styles.synergyBadge}
                      data-active={synergyActive || undefined}
                      title={
                        synergyActive
                          ? "Breakthrough synergy: these two colours count as each other"
                          : "Breakthrough synergy - locked"
                      }
                    >
                      <IconArrowsExchange size={12} aria-hidden="true" />
                    </span>
                  ) : null}
                  <b>{ownedCount(c.color)}</b>
                </div>
                {grid[c.color].map((cell, level) => (
                  <div key={level} className={styles.levelWrap}>
                    {level > 0 ? (
                      <span
                        className={styles.connector}
                        data-lit={ownedCount(c.color) >= level || undefined}
                        data-path={
                          (selected?.color === c.color &&
                            tier(selected) >= level) ||
                          undefined
                        }
                        aria-hidden="true"
                      />
                    ) : null}
                    <div className={styles.level}>
                      <span className={styles.levelTag}>
                        {level === 0 ? "base" : `${level}×`}
                      </span>
                      {cell.length === 0 ? (
                        <span className={styles.levelEmpty} />
                      ) : (
                        cell.map((row) => (
                          <TechTile
                            key={row.id}
                            row={row}
                            selected={row.id === selectedId}
                            onPath={onPath(row)}
                            onSelect={() => select(row)}
                          />
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {options.breakthrough ? (
            <BreakthroughSlot info={options.breakthrough} />
          ) : null}

          <h4>Unit upgrades</h4>
          <div className={styles.upgrades}>
            {upgrades.map((row) => (
              <TechTile
                key={row.id}
                row={row}
                selected={row.id === selectedId}
                onPath={false}
                onSelect={() => select(row)}
              />
            ))}
          </div>
          {others.length > 0 ? (
            <>
              <h4>Other</h4>
              <div className={styles.upgrades}>
                {others.map((row) => (
                  <TechTile
                    key={row.id}
                    row={row}
                    selected={row.id === selectedId}
                    onPath={false}
                    onSelect={() => select(row)}
                  />
                ))}
              </div>
            </>
          ) : null}
          <div className={styles.legend}>
            <span data-status="owned">owned</span>
            <span data-status="available">can research</span>
            <span data-status="skippable">needs a specialty planet</span>
            <span data-status="locked">locked</span>
          </div>
        </section>

        <section className={styles.panel} aria-label="Selected technology">
          {selected == null ? (
            <div className={styles.placeholder}>
              <IconCpu size={36} aria-hidden="true" />
              <p>Pick a technology in the tree.</p>
              <small>
                Glowing tiles can be researched now; sparkling ones need a
                planet with a matching technology specialty.
              </small>
            </div>
          ) : (
            <>
              <h3
                style={
                  {
                    "--tc": selected.color
                      ? COLOR_HUE[selected.color]
                      : "170 178 196",
                  } as CSSProperties
                }
              >
                {selected.name}
              </h3>
              <p className={styles.detailMeta}>
                {selected.unitUpgrade
                  ? "Unit upgrade"
                  : selected.color
                    ? COLOR_NAME[selected.color]
                    : "Technology"}
                {selected.faction ? " · faction technology" : ""} ·{" "}
                {STATUS_LABEL[selected.status]}
              </p>
              {selectedText ? (
                <p className={styles.detailText}>{selectedText}</p>
              ) : null}

              <h4>Prerequisites</h4>
              <PrereqList row={selected} options={options} left={left} />

              {!researchable ? null : (
                <>
                  {specialtyPlanets.length > 0 ||
                  (selected.unitUpgrade && options.aida) ? (
                    <>
                      <h4>Ignore prerequisites</h4>
                      <p className={styles.small}>
                        Exhaust a ready planet with a technology specialty to
                        ignore one matching symbol.
                      </p>
                      <div className={styles.planets}>
                        {specialtyPlanets.map((id) => {
                          const useful =
                            skips.includes(id) ||
                            (options.specialties[id] ?? []).some(
                              (c) => (left[c] ?? 0) > 0,
                            );
                          return (
                            <div className={styles.planetSlot} key={id}>
                              <PlanetCard
                                planetId={id}
                                picked={skips.includes(id)}
                                onPick={
                                  busy || !useful
                                    ? undefined
                                    : () => togglePlanetSkip(id)
                                }
                              />
                              <small>
                                <Pips
                                  colors={options.specialties[id] ?? []}
                                  size={12}
                                />
                              </small>
                            </div>
                          );
                        })}
                      </div>
                      {selected.unitUpgrade && options.aida ? (
                        <button
                          type="button"
                          className={styles.toggle}
                          data-on={skips.includes(AIDA_SKIP) || undefined}
                          disabled={busy}
                          onClick={() =>
                            setSkips((cur) =>
                              cur.includes(AIDA_SKIP)
                                ? cur.filter((s) => s !== AIDA_SKIP)
                                : [...cur, AIDA_SKIP],
                            )
                          }
                        >
                          <IconBolt size={14} aria-hidden="true" /> Exhaust AI
                          Development Algorithm (ignore any 1)
                        </button>
                      ) : null}
                    </>
                  ) : null}

                  {compoundOptions.length > 0 ? (
                    <>
                      <h4>Specialist Compounds · pay with a specialty planet</h4>
                      <div className={styles.planets}>
                        {compoundOptions.map((id) => (
                          <div className={styles.planetSlot} key={id}>
                            <PlanetCard
                              planetId={id}
                              picked={compound === id}
                              onPick={
                                busy
                                  ? undefined
                                  : () => setCompound((cur) => (cur === id ? null : id))
                              }
                            />
                            <small>instead of resources</small>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}

                  {options.cost > 0 && !compoundUsed ? (
                    <>
                      {options.discount > 0 ? (
                        <p className={styles.payLine}>
                          Doctor Sucaban: cost reduced by <b>{options.discount}</b>
                        </p>
                      ) : null}
                      <h4>
                        Pay {options.cost} resources
                        <button
                          type="button"
                          className={styles.linkBtn}
                          onClick={() => setPayment(null)}
                          disabled={payment == null}
                        >
                          <IconSparkles size={12} aria-hidden="true" /> Auto
                        </button>
                      </h4>
                      <div className={styles.planets}>
                        {payPlanets.length === 0 ? (
                          <span className={styles.empty}>
                            No ready planets.
                          </span>
                        ) : (
                          payPlanets.map((id) => (
                            <div className={styles.planetSlot} key={id}>
                              <PlanetCard
                                planetId={id}
                                picked={pay.planets.includes(id)}
                                onPick={busy ? undefined : () => togglePay(id)}
                              />
                              <small>{options.planets[id]} res</small>
                            </div>
                          ))
                        )}
                      </div>
                      <div className={styles.tgRow}>
                        <span className={styles.tgLabel}>
                          <img
                            className={styles.tgIcon}
                            src="/tg.png"
                            alt=""
                            aria-hidden="true"
                          />
                          Trade goods
                        </span>
                        <button
                          type="button"
                          className={styles.stepBtn}
                          disabled={busy || pay.tradeGoods <= 0}
                          onClick={() => stepTg(-1)}
                          aria-label="Spend fewer trade goods"
                        >
                          <IconMinus size={16} />
                        </button>
                        <b className={styles.stepVal}>{pay.tradeGoods}</b>
                        <button
                          type="button"
                          className={styles.stepBtn}
                          disabled={
                            busy || pay.tradeGoods >= options.tradeGoods
                          }
                          onClick={() => stepTg(1)}
                          aria-label="Spend more trade goods"
                        >
                          <IconPlus size={16} />
                        </button>
                        <small>of {options.tradeGoods}</small>
                      </div>
                      <p
                        className={styles.payLine}
                        data-bad={short > 0 || undefined}
                      >
                        Paying <b>{paid}</b> of <b>{options.cost}</b>
                        {short > 0
                          ? ` - ${short} short`
                          : paid > options.cost
                            ? ` (+${paid - options.cost} wasted)`
                            : ""}
                      </p>
                    </>
                  ) : null}
                </>
              )}
            </>
          )}
        </section>
      </div>

      <footer className={styles.dock}>
        <div className={styles.dockInfo}>
          {selected ? (
            <>
              <b>{selected.name}</b>
              <small>
                {!researchable
                  ? STATUS_LABEL[selected.status]
                  : stillMissing > 0
                    ? `${stillMissing} prerequisite(s) still missing`
                    : short > 0
                      ? `${short} resource(s) short`
                      : "Ready to research"}
              </small>
            </>
          ) : (
            <small>No technology selected</small>
          )}
        </div>
        <div className={styles.dockActions}>
          {props.onBack ? (
            <button
              type="button"
              className={styles.ghostBtn}
              disabled={busy}
              onClick={props.onBack}
            >
              <IconArrowLeft size={14} aria-hidden="true" /> Back
            </button>
          ) : null}
          {props.declineLabel && props.onDecline ? (
            <button
              type="button"
              className={styles.ghostBtn}
              disabled={busy}
              onClick={props.onDecline}
            >
              <IconX size={14} aria-hidden="true" /> {props.declineLabel}
            </button>
          ) : null}
          <button
            type="button"
            className={styles.primaryBtn}
            disabled={!canResearch}
            onClick={() =>
              selected &&
              props.onResearch({
                tech: selected.id,
                skips,
                planets: options.cost > 0 && !compoundUsed ? pay.planets : [],
                trade_goods: options.cost > 0 && !compoundUsed ? pay.tradeGoods : 0,
                ...(compoundUsed && compound ? { compound_planet: compound } : {}),
              })
            }
          >
            <IconCpu size={15} aria-hidden="true" />
            {selected ? `Research ${selected.name}` : "Research"}
          </button>
        </div>
      </footer>
    </div>,
    document.body,
  );
}

/** Lista symboli prerekwizytów wybranej technologii: spełniony / pominięty / brakuje. */
function PrereqList({
  row,
  options,
  left,
}: {
  row: TechRow;
  options: ResearchOptions;
  left: Partial<Record<TechColor, number>>;
}) {
  if (row.prerequisites.length === 0) {
    return <p className={styles.small}>No prerequisites.</p>;
  }
  const counts = new Map<TechColor, number>();
  for (const c of row.prerequisites) counts.set(c, (counts.get(c) ?? 0) + 1);
  return (
    <ul className={styles.prereqs}>
      {[...counts.entries()].map(([color, need]) => {
        const missing = row.missing[color] ?? 0;
        const stillLeft = Math.max(0, left[color] ?? 0);
        const skipped = missing - stillLeft;
        const have = Math.min(need, options.ownedColors[color] ?? 0);
        // Reszta spełniona technologią drugiego koloru pary synergii przełomu.
        const viaSynergy = Math.max(0, need - have - missing);
        return (
          <li key={color} style={{ "--tc": COLOR_HUE[color] } as CSSProperties}>
            <img src={COLOR_ICON[color]} alt="" width={16} height={16} />
            <span>
              {need}× {COLOR_NAME[color]}
            </span>
            <span className={styles.prereqState}>
              {have > 0 ? <em data-ok>{have} owned</em> : null}
              {viaSynergy > 0 ? (
                <em data-synergy>{viaSynergy} via synergy</em>
              ) : null}
              {skipped > 0 ? <em data-skip>{skipped} via specialty</em> : null}
              {stillLeft > 0 ? <em data-bad>{stillLeft} missing</em> : null}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Miejsce na PRZEŁOM frakcji (Thunder's Edge). Pokazany zawsze; zablokowany jest wyszarzony
 * i NIE działa. Odblokowany daje synergię dwóch kolorów: posiadane technologie i
 * specjalności planet jednego koloru pary liczą się jako drugi (R_synergy) - silnik
 * uwzględnia to w prerekwizytach i skipach.
 */
function BreakthroughSlot({ info }: { info: BreakthroughInfo }) {
  const text = getBreakthroughData(info.id)?.text;
  const [a, b] = info.synergy;
  const state = info.active ? "active" : info.unlocked ? "noSynergy" : "locked";
  return (
    <div className={styles.breakthrough} data-state={state}>
      <div className={styles.btHead}>
        <span className={styles.btLabel}>Breakthrough</span>
        <b>{info.name}</b>
        <span className={styles.btStatus}>
          {info.active ? (
            <>
              <IconCheck size={13} aria-hidden="true" /> Synergy active
            </>
          ) : info.unlocked ? (
            "No colour synergy"
          ) : (
            <>
              <IconLock size={13} aria-hidden="true" /> Locked - not in effect
            </>
          )}
        </span>
      </div>
      {a && b ? (
        <div className={styles.btSynergy}>
          <span style={{ "--tc": COLOR_HUE[a] } as CSSProperties}>
            <img src={COLOR_ICON[a]} alt="" width={18} height={18} />{" "}
            {COLOR_NAME[a]}
          </span>
          <IconArrowsExchange size={18} aria-hidden="true" />
          <span style={{ "--tc": COLOR_HUE[b] } as CSSProperties}>
            <img src={COLOR_ICON[b]} alt="" width={18} height={18} />{" "}
            {COLOR_NAME[b]}
          </span>
          <small>
            {info.active
              ? "Your technologies and planet specialties of either colour count as the other when researching."
              : "Unlock the breakthrough to treat these colours as each other when researching."}
          </small>
        </div>
      ) : null}
      {text ? <p className={styles.btText}>{text}</p> : null}
    </div>
  );
}
