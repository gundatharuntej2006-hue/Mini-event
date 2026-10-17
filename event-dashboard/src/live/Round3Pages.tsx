import {
  FormEvent,
  ReactNode,
  RefObject,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Clock3,
  Gavel,
  LayoutGrid,
  LogOut,
  Plus,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Timer,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useNavigate } from "react-router-dom";
import { LiveShell, Mark } from "./LiveShell";
import { clearSession, getSession, request } from "./eventApi";

gsap.registerPlugin(ScrollTrigger);

type Member = { id: string; name: string; played: boolean };
type Attempt = {
  id: string;
  table_number: number;
  room_number: number;
  game_name: string;
  game_mode: string;
  status: string;
  queue_position: number | null;
  participant_name: string;
  reserved_until: string | null;
  started_at: string | null;
  spun_at: string | null;
  queued_at: string | null;
  points: number | null;
  team_identifier?: string;
};
type Lot = {
  id: string;
  level: number;
  token_number: number;
  title: string;
  description: string;
  clue_text: string | null;
  status: string;
  opening_bid: number;
  highest_bid: number | null;
  you_are_highest: boolean;
  winner_team_id: string | null;
  winning_bid: number | null;
};
type Ledger = {
  delta: number;
  category: string;
  description: string;
  at: string;
};
type TeamState = {
  team_identifier: string;
  team_name: string;
  opening_points: number;
  opening_breakdown: {
    treasure_hunt: number;
    cabo: number;
    exercise: number;
    organizer_correction: number;
  } | null;
  balance: number;
  available_to_bid: number;
  members: Member[];
  ledger: Ledger[];
  attempt: Attempt | null;
  games_completed: number;
  active_devices: number;
};
type ParticipantState = {
  open: boolean;
  starts_at: string | null;
  ends_at: string | null;
  team: TeamState;
  wheel_tables: { number: number; mode: string }[];
  lots: Lot[];
};
type Table = {
  number: number;
  room: number;
  mode: string;
  game_name: string;
  max_points: number;
  enabled: boolean;
  admin: string | null;
};
type Control = {
  started: boolean;
  open: boolean;
  closed: boolean;
  starts_at: string | null;
  ends_at: string | null;
  teams: {
    team_identifier: string;
    team_name: string;
    opening_points: number;
    balance: number;
    members: number;
    played: number;
    rank: number;
    projected_qualified: boolean;
    qualified: boolean;
  }[];
  tables: Table[];
  admins: { login_id: string; display_name: string; is_active: boolean }[];
  lots: Lot[];
  qualification: {
    count: number;
    finalized: boolean;
    finalized_at: string | null;
    cutoff_tie: boolean;
    qualified_team_ids: string[];
  };
  questions: { total: number; used: number };
};
type Dealer = {
  assigned: boolean;
  started: boolean;
  number?: number;
  room?: number;
  mode?: string;
  game_name?: string;
  max_points?: number;
  attempts?: Attempt[];
};
type TableDraft = {
  number: string;
  room: string;
  mode: string;
  admin: string;
  name: string;
  max: string;
  enabled: boolean;
};
type LotDraft = { description: string; clue_text: string; opening: string };
type BankPuzzle = {
  key: string;
  title: string;
  eyebrow: string;
  story: string;
  prompt: string;
  display: string[];
  answers: string[];
  answer_label: string;
  visual_kind: string;
};
type PuzzleBank = {
  total: number;
  game_seconds: number;
  tables: {
    table_number: number;
    station_name: string;
    count: number;
    puzzles: BankPuzzle[];
  }[];
};

const points = (value: number | null | undefined) =>
  typeof value === "number"
    ? value.toLocaleString("en-IN", { maximumFractionDigits: 2 })
    : "—";
const clock = (value: string | null | undefined) =>
  value
    ? new Date(value).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "—";
const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";

function useEntrance(root: RefObject<HTMLElement>) {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const context = gsap.context(() => {
      gsap.fromTo(
        "[data-r3-reveal]",
        { autoAlpha: 0, y: 26 },
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.78,
          stagger: 0.09,
          ease: "power3.out",
        },
      );
      gsap.utils.toArray<HTMLElement>("[data-r3-scroll]").forEach((element) => {
        gsap.fromTo(
          element,
          { autoAlpha: 0.68, y: 22 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.65,
            ease: "power2.out",
            scrollTrigger: { trigger: element, start: "top 92%", once: true },
          },
        );
      });
    }, root);
    return () => context.revert();
  }, [root]);
}

function Countdown({ until }: { until: string | null | undefined }) {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    const tick = () =>
      setRemaining(
        Math.max(
          0,
          Math.ceil((new Date(until || 0).getTime() - Date.now()) / 1000),
        ),
      );
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [until]);
  return (
    <span className="r3-timer-digits" role="timer">
      {String(Math.floor(remaining / 60)).padStart(2, "0")}:
      {String(remaining % 60).padStart(2, "0")}
    </span>
  );
}

function Page({
  children,
  back,
  signout = false,
  className = "",
}: {
  children: ReactNode;
  back: string;
  signout?: boolean;
  className?: string;
}) {
  const navigate = useNavigate();
  const root = useRef<HTMLElement>(null);
  useEntrance(root);
  async function leave() {
    if (signout)
      await request("/r3-live/participant/signout", "POST", {}).catch(
        () => undefined,
      );
    clearSession();
    navigate("/login");
  }
  return (
    <LiveShell>
      <main ref={root} className={"r3-experience " + className}>
        <div className="r3-atmosphere" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
        <header className="r3-topbar" data-r3-reveal>
          <Mark />
          <div className="r3-topbar-right">
            <span className="r3-live-mark">
              <i /> ASYMPTOTES / UNDERGROUND
            </span>
            <button
              className="r3-back"
              aria-label={signout ? "Sign out" : "Back"}
              onClick={signout ? leave : () => navigate(back)}
            >
              {signout ? <LogOut size={18} /> : <ArrowLeft size={18} />}
            </button>
          </div>
        </header>
        {children}
        <footer className="r3-footer">
          <span>ASYMPTOTES · BMSIT</span>
          <span>PRIVATE EVENT NETWORK / ROUND 03</span>
        </footer>
      </main>
    </LiveShell>
  );
}

function Alert({ error, notice }: { error: string; notice: string }) {
  return (
    <>
      {error && (
        <div className="r3-alert error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="r3-alert" role="status">
          {notice}
        </div>
      )}
    </>
  );
}

function Wheel({
  tables,
  wheelRef,
  spinning,
}: {
  tables: { number: number; mode: string }[];
  wheelRef: RefObject<HTMLDivElement>;
  spinning: boolean;
}) {
  const slices =
    tables.length === 8
      ? tables
      : Array.from({ length: 8 }, (_, index) => ({
          number: index + 1,
          mode: index < 4 ? "ONLINE" : "OFFLINE",
        }));
  return (
    <div className={"r3-wheel-stage" + (spinning ? " is-spinning" : "")}>
      <div className="r3-wheel-halo" aria-hidden="true" />
      <div className="r3-wheel-pointer" aria-hidden="true" />
      <div
        className="r3-wheel"
        ref={wheelRef}
        aria-label="Eight dealer tables on the assignment wheel"
      >
        {slices.map((table, index) => (
          <span
            className="r3-wheel-number"
            key={table.number}
            style={{
              transform:
                "rotate(" +
                (index * 45 + 22.5) +
                "deg) translateY(-112px) rotate(" +
                (-index * 45 - 22.5) +
                "deg)",
            }}
          >
            {String(table.number).padStart(2, "0")}
          </span>
        ))}
        <div className="r3-wheel-core">
          <Zap size={22} />
          <small>
            THE
            <br />
            WHEEL
          </small>
        </div>
      </div>
    </div>
  );
}

function AuctionLots({
  lots,
  open,
  bid,
  setBid,
  act,
  busy,
}: {
  lots: Lot[];
  open: boolean;
  bid: Record<string, string>;
  setBid: (value: Record<string, string>) => void;
  act: (path: string, body?: unknown) => Promise<unknown>;
  busy: boolean;
}) {
  return (
    <div className="r3-lot-list">
      {lots.length ? (
        lots.map((lot) => (
          <article
            className={
              "r3-auction-lot " +
              (lot.status === "LIVE"
                ? "live"
                : lot.status === "DRAFT"
                  ? "sealed"
                  : "")
            }
            key={lot.id}
            data-r3-scroll
          >
            <div className="r3-lot-header">
              <span className="r3-kicker">
                LOT {String(lot.level).padStart(2, "0")}.{lot.token_number} /
                CASE INTELLIGENCE
              </span>
              <span className={"r3-state-pill " + lot.status.toLowerCase()}>
                {lot.status === "LIVE"
                  ? "● BIDDING LIVE"
                  : lot.status === "DRAFT"
                    ? "SEALED"
                    : lot.status}
              </span>
            </div>
            <div className="r3-lot-body">
              <div className="r3-lot-emblem">
                <Gavel size={30} />
                <small>LEVEL {lot.level}</small>
              </div>
              <div>
                <h3>{lot.title}</h3>
                <p>{lot.description}</p>
              </div>
            </div>
            {lot.clue_text && (
              <div className="r3-won-clue">
                <Sparkles size={16} />
                <div>
                  <b>CLAIMED INTELLIGENCE</b>
                  <p>{lot.clue_text}</p>
                </div>
              </div>
            )}
            {lot.status === "DRAFT" ? (
              <div className="r3-sealed-note">
                <Sparkles size={16} /> Unseal time is known only to the
                auctioneer.
              </div>
            ) : (
              <div className="r3-bid-bar">
                <div>
                  <small>CURRENT BID</small>
                  <strong>{points(lot.highest_bid ?? lot.opening_bid)}</strong>
                </div>
                <div>
                  <small>STATUS</small>
                  <strong>
                    {lot.you_are_highest
                      ? "YOU LEAD"
                      : lot.status === "CLOSED"
                        ? "SETTLED"
                        : "OPEN FLOOR"}
                  </strong>
                </div>
              </div>
            )}
            {lot.status === "LIVE" && (
              <form
                className="r3-bid-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void act("/r3-live/participant/lots/" + lot.id + "/bid", {
                    amount: Number(bid[lot.id]),
                  });
                }}
              >
                <label className="r3-sr-only" htmlFor={"bid-" + lot.id}>
                  Your bid for {lot.title}
                </label>
                <input
                  id={"bid-" + lot.id}
                  type="number"
                  min={Math.max(lot.opening_bid, (lot.highest_bid ?? 0) + 1)}
                  step="1"
                  value={bid[lot.id] || ""}
                  onChange={(event) =>
                    setBid({ ...bid, [lot.id]: event.target.value })
                  }
                  placeholder="Your offer"
                />
                <button className="r3-button peach" disabled={busy || !open}>
                  Place bid <ArrowUpRight size={16} />
                </button>
              </form>
            )}
          </article>
        ))
      ) : (
        <div className="r3-empty">
          <Gavel size={28} />
          <h3>The floor is quiet.</h3>
          <p>
            The auctioneer can release five case-clue lots at any time. Stay
            alert while your team plays.
          </p>
        </div>
      )}
    </div>
  );
}

export function Round3ParticipantPage() {
  const navigate = useNavigate();
  const [state, setState] = useState<ParticipantState | null>(null);
  const [mode, setMode] = useState<"GAMES" | "AUCTION">("GAMES");
  const [member, setMember] = useState("");
  const [bid, setBid] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [spinning, setSpinning] = useState(false);
  const wheelRef = useRef<HTMLDivElement>(null);
  const rotation = useRef(0);
  const load = (silent = false) =>
    request<ParticipantState>("/r3-live/participant/state")
      .then(setState)
      .catch((problem) => {
        if (!silent) setError(errorText(problem));
      });
  useEffect(() => {
    if (getSession()?.role !== "PARTICIPANT") {
      navigate("/login", { replace: true });
      return;
    }
    void load();
    const timer = window.setInterval(() => void load(true), 5000);
    return () => window.clearInterval(timer);
  }, []);
  async function act(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await request<unknown>(
        path,
        "POST",
        body === undefined ? {} : body,
      );
      setNotice(
        path.includes("/bid")
          ? "Bid accepted. Your held balance has been updated."
          : path.includes("/queue")
            ? "Queue position secured."
            : "Updated.",
      );
      await load(true);
      return result;
    } catch (problem) {
      setError(errorText(problem));
      return null;
    } finally {
      setBusy(false);
    }
  }
  async function spin() {
    if (!member || !state?.open || busy || spinning) return;
    setBusy(true);
    setSpinning(true);
    setError("");
    setNotice("");
    try {
      // The server records the click immediately; the reveal animation never determines queue order.
      const attempt = await request<Attempt>(
        "/r3-live/participant/spin",
        "POST",
        { participant_id: member },
      );
      const index = Math.max(
        0,
        state.wheel_tables.findIndex(
          (table) => table.number === attempt.table_number,
        ),
      );
      const target =
        rotation.current +
        1800 +
        ((360 - (index * 45 + 22.5) - (rotation.current % 360) + 360) % 360);
      if (
        wheelRef.current &&
        !window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ) {
        await new Promise<void>((resolve) =>
          gsap.to(wheelRef.current, {
            rotation: target,
            duration: 3.2,
            ease: "power4.out",
            onComplete: resolve,
          }),
        );
      }
      rotation.current = target;
      setNotice(
        "Table " +
          attempt.table_number +
          " assigned at " +
          clock(attempt.spun_at) +
          ". Show this result to your dealer.",
      );
      await load(true);
    } catch (problem) {
      setError(errorText(problem));
    } finally {
      setSpinning(false);
      setBusy(false);
    }
  }
  const team = state?.team;
  const activeLots =
    state?.lots.filter((lot) => lot.status === "LIVE").length || 0;
  return (
    <Page back="/play" signout className="r3-participant">
      <section className="r3-hero" data-r3-reveal>
        <div className="r3-hero-copy">
          <span className="r3-kicker">
            <Radio size={14} /> ROUND 03 / PRIVATE ACCESS
          </span>
          <h1>
            The <em>Underground.</em>
          </h1>
          <p>One team. Two arenas. Every decision moves the balance.</p>
          <div className="r3-identity">
            {team?.team_identifier || "TEAM"} <span>/</span>{" "}
            {team?.team_name || "Loading your access…"}
          </div>
        </div>
        <div className="r3-hero-clock">
          <small>
            {state?.open
              ? "MARKET CLOSES IN"
              : state?.starts_at
                ? "MARKET CLOSED"
                : "AWAITING OPEN"}
          </small>
          {state?.open ? (
            <Countdown until={state.ends_at} />
          ) : (
            <strong>30:00</strong>
          )}
          <span>
            {state?.open
              ? "Games started before closing receive their full 75 seconds."
              : "Your balance and dealer games unlock when the round begins."}
          </span>
        </div>
      </section>
      <div className="r3-ticker" aria-hidden="true">
        <div>
          AUCTION FLOOR OPEN WHEN RELEASED <span>✦</span> EIGHT DEALER STATIONS{" "}
          <span>✦</span> FIRST COME, FIRST SERVED <span>✦</span> THREE DEVICES
          PER TEAM <span>✦</span> AUCTION FLOOR OPEN WHEN RELEASED{" "}
          <span>✦</span> EIGHT DEALER STATIONS <span>✦</span>
        </div>
      </div>
      <Alert error={error} notice={notice} />
      <section className="r3-metrics" data-r3-reveal>
        <div>
          <Wallet size={18} />
          <small>TEAM BALANCE</small>
          <strong>{points(team?.balance)}</strong>
          <span>Private to your team</span>
        </div>
        <div>
          <Gavel size={18} />
          <small>AVAILABLE TO BID</small>
          <strong>{points(team?.available_to_bid)}</strong>
          <span>Leading bids are reserved</span>
        </div>
        <div>
          <Users size={18} />
          <small>GAMES COMPLETED</small>
          <strong>
            {team?.games_completed ?? 0}
            <i> / {team?.members.length ?? 5}</i>
          </strong>
          <span>Each member plays once</span>
        </div>
        <div>
          <Radio size={18} />
          <small>ACTIVE LOGINS</small>
          <strong>
            {team?.active_devices ?? 0}
            <i> / 3</i>
          </strong>
          <span>Sign out to free a slot</span>
        </div>
      </section>
      <div className="r3-participant-layout">
        <div className="r3-workspace">
          <nav className="r3-tabs" aria-label="Round 3 mode" data-r3-reveal>
            <button
              className={mode === "GAMES" ? "selected" : ""}
              onClick={() => setMode("GAMES")}
            >
              <Zap size={18} /> Dealer games <span>8 stations</span>
            </button>
            <button
              className={mode === "AUCTION" ? "selected" : ""}
              onClick={() => setMode("AUCTION")}
            >
              <Gavel size={18} /> Auction floor <span>{activeLots} live</span>
            </button>
          </nav>
          {!state?.open && (
            <div className="r3-notice">
              <Timer size={18} />
              <p>
                {state?.starts_at
                  ? "The 30-minute window has closed. An already-started game can still finish within its own 75 seconds."
                  : "The super admin has not opened the 30-minute window yet. You can explore the interface while you wait."}
              </p>
            </div>
          )}
          {mode === "GAMES" ? (
            <section className="r3-game-grid" data-r3-reveal>
              <div className="r3-wheel-card">
                <div className="r3-section-head">
                  <span className="r3-kicker">THE DEALER CIRCUIT / 01</span>
                  <h2>Spin for a station.</h2>
                  <p>
                    Select one teammate. The server timestamps your click,
                    assigns an available game, then reveals your result.
                  </p>
                </div>
                <Wheel
                  tables={state?.wheel_tables || []}
                  wheelRef={wheelRef}
                  spinning={spinning}
                />
                <button
                  className="r3-button peach r3-spin-button"
                  disabled={!state?.open || busy || !member || !!team?.attempt}
                  onClick={() => void spin()}
                >
                  {spinning ? "Finding your dealer…" : "Spin the wheel"}{" "}
                  <Zap size={18} />
                </button>
                <small className="r3-fineprint">
                  One active team turn across all three logins. Busy station?
                  Join its queue or cancel and spin again.
                </small>
              </div>
              <div className="r3-player-card">
                <div className="r3-section-head">
                  <span className="r3-kicker">SELECT OPERATIVE / 02</span>
                  <h2>Your five players.</h2>
                  <p>
                    Every member needs one scored dealer game. Choose the person
                    at the screen before spinning.
                  </p>
                </div>
                <div className="r3-player-list">
                  {team?.members.map((person, index) => (
                    <label
                      className={
                        "r3-player " +
                        (person.played ? "done" : "") +
                        (member === person.id ? " chosen" : "")
                      }
                      key={person.id}
                    >
                      <input
                        type="radio"
                        name="r3-player"
                        checked={member === person.id}
                        disabled={
                          person.played || !state?.open || !!team.attempt
                        }
                        onChange={() => setMember(person.id)}
                      />
                      <b>{String(index + 1).padStart(2, "0")}</b>
                      <span>{person.name}</span>
                      <small>
                        {person.played
                          ? "COMPLETED"
                          : member === person.id
                            ? "SELECTED"
                            : "READY"}
                      </small>
                    </label>
                  ))}
                </div>
                <div className="r3-rule-strip">
                  <Clock3 size={18} />
                  <span>
                    75 seconds per game. Results are validated automatically.
                  </span>
                </div>
              </div>
            </section>
          ) : (
            <section className="r3-auction-board" data-r3-reveal>
              <div className="r3-section-head">
                <span className="r3-kicker">
                  PREMIUM CASE INTELLIGENCE / LIVE FLOOR
                </span>
                <h2>Clues go to the bold.</h2>
                <p>
                  Three Level 1 and two Level 2 clue tokens can be released at
                  any moment. Only a winning bid is charged. The final-round
                  code is not for sale.
                </p>
              </div>
              <AuctionLots
                lots={state?.lots || []}
                open={!!state?.open}
                bid={bid}
                setBid={setBid}
                act={act}
                busy={busy}
              />
            </section>
          )}
          {team?.attempt && !spinning && (
            <section className="r3-assignment" aria-live="polite">
              <div>
                <span className="r3-kicker">YOUR CURRENT ASSIGNMENT</span>
                <h2>
                  Room {team.attempt.room_number} <span>/</span> Table{" "}
                  {team.attempt.table_number}
                </h2>
                <p>
                  {team.attempt.game_name} · {team.attempt.game_mode} ·{" "}
                  {team.attempt.participant_name}
                </p>
                <small>
                  Wheel request logged {clock(team.attempt.spun_at)}
                </small>
              </div>
              <div className="r3-assignment-status">
                <strong>{team.attempt.status}</strong>
                {team.attempt.status === "QUEUED" && (
                  <p>
                    Queue position #{team.attempt.queue_position}. Keep this
                    screen open.
                  </p>
                )}
                {team.attempt.status === "OFFERED" && (
                  <p>This station is busy. Join the queue or spin again.</p>
                )}
                {team.attempt.status === "RESERVED" && (
                  <p>
                    Show this screen to the dealer before{" "}
                    {clock(team.attempt.reserved_until)}.
                  </p>
                )}
                {team.attempt.status === "ACTIVE" && (
                  <p>
                    Game time left:{" "}
                    <Countdown
                      until={
                        team.attempt.started_at
                          ? new Date(
                              new Date(team.attempt.started_at).getTime() +
                                75000,
                            ).toISOString()
                          : null
                      }
                    />
                  </p>
                )}
                <div className="r3-inline-actions">
                  {team.attempt.status === "OFFERED" && (
                    <button
                      className="r3-button peach"
                      disabled={busy || !state?.open}
                      onClick={() => void act("/r3-live/participant/queue")}
                    >
                      Join queue
                    </button>
                  )}
                  {team.attempt.status !== "ACTIVE" && (
                    <button
                      className="r3-button ghost"
                      disabled={busy}
                      onClick={() => void act("/r3-live/participant/cancel")}
                    >
                      Cancel / re-spin
                    </button>
                  )}
                </div>
              </div>
            </section>
          )}
        </div>
        <aside className="r3-side">
          <section className="r3-side-card" data-r3-reveal>
            <span className="r3-kicker">YOUR PRIVATE LEDGER</span>
            <h2>Where the points go.</h2>
            <p>
              Opening balance {points(team?.opening_points)}. Every dealer
              result and winning bid is recorded here.
            </p>
            {team?.opening_breakdown && (
              <>
                <div className="r3-ledger-line">
                  <span>Treasure Hunt</span>
                  <b>+{points(team.opening_breakdown.treasure_hunt)}</b>
                </div>
                <div className="r3-ledger-line">
                  <span>Cabo</span>
                  <b>+{points(team.opening_breakdown.cabo)}</b>
                </div>
                {team.opening_breakdown.exercise !== 0 && (
                  <div className="r3-ledger-line">
                    <span>Exercise activities</span>
                    <b>+{points(team.opening_breakdown.exercise)}</b>
                  </div>
                )}
                {team.opening_breakdown.organizer_correction !== 0 && (
                  <div className="r3-ledger-line">
                    <span>Opening correction</span>
                    <b>{points(team.opening_breakdown.organizer_correction)}</b>
                  </div>
                )}
              </>
            )}
            {team?.ledger.map((entry, index) => (
              <div className="r3-ledger-line" key={entry.at + index}>
                <span>
                  {entry.description}
                  <small>
                    {entry.category} · {clock(entry.at)}
                  </small>
                </span>
                <b className={entry.delta < 0 ? "debit" : ""}>
                  {entry.delta > 0 ? "+" : ""}
                  {points(entry.delta)}
                </b>
              </div>
            ))}
          </section>
          <section className="r3-side-card r3-side-live">
            <Radio size={22} />
            <span className="r3-kicker">FLOOR SIGNAL</span>
            <h3>
              {activeLots
                ? activeLots +
                  " live clue " +
                  (activeLots === 1 ? "lot" : "lots")
                : "Awaiting the first lot."}
            </h3>
            <p>
              Watch the auction while your teammate prepares for the dealer.
              Your own balance is never shown to other teams.
            </p>
            <button
              className="r3-text-button"
              onClick={() => {
                setMode("AUCTION");
                window.scrollTo({ top: 400, behavior: "smooth" });
              }}
            >
              Go to auction <ArrowUpRight size={15} />
            </button>
          </section>
        </aside>
      </div>
    </Page>
  );
}

export function Round3SuperPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<Control | null>(null);
  const [selected, setSelected] = useState<TeamState | null>(null);
  const [section, setSection] = useState<
    "OVERVIEW" | "DEALERS" | "PUZZLES" | "HANDOFF" | "AUCTION" | "TEAMS"
  >("OVERVIEW");
  const [bank, setBank] = useState<PuzzleBank | null>(null);
  const [bankTable, setBankTable] = useState(1);
  const [bankQuery, setBankQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [pointsDraft, setPointsDraft] = useState<Record<string, string>>({});
  const [tablesDraft, setTablesDraft] = useState<Record<number, TableDraft>>(
    {},
  );
  const [lotsDraft, setLotsDraft] = useState<Record<string, LotDraft>>({});
  const [newAdmin, setNewAdmin] = useState({
    login_id: "",
    display_name: "",
    password: "",
  });
  const [correction, setCorrection] = useState({
    team_identifier: "",
    delta: "",
    reason: "",
  });
  const [qualifyingCount, setQualifyingCount] = useState("6");
  const load = (reset = false) =>
    request<Control>("/r3-live/control/overview")
      .then((item) => {
        setData(item);
        if (reset) {
          setQualifyingCount(String(item.qualification.count));
          setPointsDraft(
            Object.fromEntries(
              item.teams.map((team) => [
                team.team_identifier,
                String(team.opening_points),
              ]),
            ),
          );
          setTablesDraft(
            Object.fromEntries(
              item.tables.map((table) => [
                table.number,
                {
                  number: String(table.number),
                  room: String(table.room),
                  mode: table.mode,
                  admin: table.admin || "",
                  name: table.game_name,
                  max: String(table.max_points),
                  enabled: table.enabled,
                },
              ]),
            ),
          );
          setLotsDraft(
            Object.fromEntries(
              item.lots.map((lot) => [
                lot.id,
                {
                  description: lot.description,
                  clue_text: lot.clue_text || "",
                  opening: String(lot.opening_bid),
                },
              ]),
            ),
          );
        }
      })
      .catch((problem) => setError(errorText(problem)));
  useEffect(() => {
    if (getSession()?.role !== "SUPER_ADMIN") {
      navigate("/login", { replace: true });
      return;
    }
    void load(true);
    const timer = window.setInterval(() => void load(), 8000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (section !== "PUZZLES" || bank) return;
    request<PuzzleBank>("/r3-live/control/puzzle-bank")
      .then(setBank)
      .catch((problem) => setError(errorText(problem)));
  }, [section, bank]);
  async function act(path: string, body?: unknown, success = "Saved.") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(path, "POST", body || {});
      setNotice(success);
      await load(true);
      return true;
    } catch (problem) {
      setError(errorText(problem));
      return false;
    } finally {
      setBusy(false);
    }
  }
  const liveCount =
    data?.lots.filter((lot) => lot.status === "LIVE").length || 0;
  const readyCount = data?.tables.filter((table) => table.enabled).length || 0;
  const nav = [
    ["OVERVIEW", "Command desk", LayoutGrid],
    ["DEALERS", "Puzzle stations", Radio],
    ["PUZZLES", "Question bank", Sparkles],
    ["HANDOFF", "Laptop handoff", Users],
    ["AUCTION", "Auction control", Gavel],
    ["TEAMS", "Team ledger", Wallet],
  ] as const;
  return (
    <Page back="/control" className="r3-super">
      <section className="r3-hero r3-super-hero" data-r3-reveal>
        <div>
          <span className="r3-kicker">
            <ShieldCheck size={14} /> SUPER ADMIN / ROUND 03
          </span>
          <h1>
            Market <em>command.</em>
          </h1>
          <p>
            Eight automated puzzle laptops. Thirteen teams. One 30-minute
            window. Answers, timers and points are enforced by the server.
          </p>
        </div>
        <div className="r3-super-timer">
          <small>
            {data?.open
              ? "WINDOW CLOSES IN"
              : data?.started
                ? data.closed
                  ? "WINDOW CLOSED"
                  : "TIME ENDED · SETTLE ROUND"
                : "READY TO CONFIGURE"}
          </small>
          {data?.open ? (
            <Countdown until={data.ends_at} />
          ) : (
            <strong>{data?.started ? "00:00" : "30:00"}</strong>
          )}
          <div className="r3-inline-actions">
            <button className="r3-button ghost" onClick={() => void load()}>
              <RefreshCw size={16} /> Refresh
            </button>
            {!data?.started && (
              <button
                className="r3-button peach"
                disabled={busy || readyCount !== 8}
                onClick={() => {
                  if (
                    window.confirm(
                      "Open Round 3 for all 13 teams for 30 minutes?",
                    )
                  )
                    void act("/r3-live/control/start", {}, "Round 3 is live.");
                }}
              >
                Open market
              </button>
            )}
            {data?.open && (
              <button
                className="r3-button danger"
                disabled={busy}
                onClick={() => {
                  if (
                    window.confirm(
                      "Close the market early? Live auction lots must be settled first. Active puzzles keep their 75-second limit.",
                    )
                  )
                    void act(
                      "/r3-live/control/close",
                      {},
                      "The market is closed.",
                    );
                }}
              >
                Close early
              </button>
            )}
            {data?.started && !data.open && !data.closed && (
              <button
                className="r3-button danger"
                disabled={busy}
                onClick={() => {
                  if (
                    window.confirm(
                      "Settle and close Round 3? Live auction lots must be settled first. Any game already started keeps its full 75 seconds.",
                    )
                  )
                    void act(
                      "/r3-live/control/close",
                      {},
                      "Round 3 is settled and closed.",
                    );
                }}
              >
                Close &amp; settle
              </button>
            )}
          </div>
        </div>
      </section>
      <Alert error={error} notice={notice} />
      <section className="r3-metrics r3-super-metrics" data-r3-reveal>
        <div>
          <Users size={18} />
          <small>QUALIFIED TEAMS</small>
          <strong>{data?.teams.length ?? "—"}</strong>
          <span>Private field</span>
        </div>
        <div>
          <Radio size={18} />
          <small>STATIONS READY</small>
          <strong>
            {readyCount}
            <i> / 8</i>
          </strong>
          <span>Automated laptops</span>
        </div>
        <div>
          <Gavel size={18} />
          <small>LIVE AUCTION LOTS</small>
          <strong>{liveCount}</strong>
          <span>Five total clue tokens</span>
        </div>
        <div>
          <Clock3 size={18} />
          <small>MARKET STATUS</small>
          <strong className="r3-metric-word">
            {data?.open
              ? "LIVE"
              : data?.closed
                ? "CLOSED"
                : data?.started
                  ? "SETTLE"
                  : "SETUP"}
          </strong>
          <span>Puzzles and auction together</span>
        </div>
      </section>
      <div className="r3-console">
        <nav className="r3-console-nav" aria-label="Round 3 control sections">
          {nav.map(([key, label, Icon]) => (
            <button
              key={key}
              className={section === key ? "selected" : ""}
              onClick={() => setSection(key)}
            >
              <Icon size={19} />
              <span>{label}</span>
              <ArrowUpRight size={14} />
            </button>
          ))}
          <div className="r3-console-nav-note">
            <i /> All changes are server-authoritative. Participants only see
            their own balance.
          </div>
        </nav>
        <div className="r3-console-body">
          {section === "OVERVIEW" && (
            <>
              <div className="r3-section-head">
                <span className="r3-kicker">
                  FLOOR OVERVIEW / LIVE OPERATIONS
                </span>
                <h2>Everything in motion.</h2>
                <p>
                  Verify points and station laptops before opening. Timers,
                  answers and awards are automatic; corrections remain audited.
                </p>
              </div>
              <div className="r3-overview-cards">
                <button onClick={() => setSection("DEALERS")}>
                  <Radio size={26} />
                  <b>Puzzle stations</b>
                  <span>{readyCount} of 8 laptops ready</span>
                  <ArrowUpRight size={16} />
                </button>
                <button onClick={() => setSection("AUCTION")}>
                  <Gavel size={26} />
                  <b>Auction floor</b>
                  <span>{liveCount} lots live now</span>
                  <ArrowUpRight size={16} />
                </button>
                <button onClick={() => setSection("PUZZLES")}>
                  <Sparkles size={26} />
                  <b>Question bank</b>
                  <span>
                    {data?.questions.used ?? 0}/{data?.questions.total ?? 275}{" "}
                    permanently used · 75 seconds
                  </span>
                  <ArrowUpRight size={16} />
                </button>
                <button onClick={() => setSection("TEAMS")}>
                  <Wallet size={26} />
                  <b>Team accounts</b>
                  <span>13 private point ledgers</span>
                  <ArrowUpRight size={16} />
                </button>
              </div>
              <div className="r3-panel-box">
                <span className="r3-kicker">PRIVATE / SUPER ADMIN ONLY</span>
                <h3>Provisional ranking</h3>
                <p>
                  The later legal-round gate also needs the ODD ECHO code. This
                  list does not unlock it.
                </p>
                {[...(data?.teams || [])]
                  .sort((a, b) => a.rank - b.rank)
                  .map((team) => (
                    <div
                      className={
                        "r3-ranking-row " +
                        (team.projected_qualified ? "projected" : "")
                      }
                      key={team.team_identifier}
                    >
                      <b>{String(team.rank).padStart(2, "0")}</b>
                      <span>
                        {team.team_name}
                        <small>
                          {team.team_identifier} · {team.played}/{team.members}{" "}
                          played{team.projected_qualified ? " · projected qualifier" : ""}
                        </small>
                      </span>
                      <strong>{points(team.balance)}</strong>
                    </div>
                  ))}
              </div>
              <div className="r3-panel-box r3-qualification-control">
                <span className="r3-kicker">ROUND 4 FIELD CONTROL</span>
                <h3>Choose how many teams qualify.</h3>
                <p>
                  The top teams are projected from the final private balance.
                  A tie across the cutoff blocks locking until you resolve it.
                </p>
                <div className="r3-qualification-actions">
                  <label>
                    Qualifying teams
                    <input
                      type="number"
                      min="1"
                      max="13"
                      disabled={data?.qualification.finalized}
                      value={qualifyingCount}
                      onChange={(event) => setQualifyingCount(event.target.value)}
                    />
                  </label>
                  <button
                    className="r3-button peach"
                    disabled={busy || data?.qualification.finalized}
                    onClick={() =>
                      void act(
                        "/r3-live/control/qualification-count",
                        { qualifying_count: Number(qualifyingCount) },
                        "Qualification count saved.",
                      )
                    }
                  >
                    Save count
                  </button>
                  <button
                    className="r3-button danger"
                    disabled={
                      busy ||
                      !data?.started ||
                      !data?.closed ||
                      data?.qualification.finalized ||
                      data?.qualification.cutoff_tie
                    }
                    onClick={() => {
                      if (
                        window.confirm(
                          `Lock the top ${data?.qualification.count ?? 0} teams for Round 4? This cannot be changed from the event screen.`,
                        )
                      )
                        void act(
                          "/r3-live/control/qualifications/finalize",
                          {},
                          "Round 4 qualifiers locked.",
                        );
                    }}
                  >
                    Lock qualifiers
                  </button>
                </div>
                {data?.qualification.cutoff_tie && (
                  <p className="r3-cutoff-warning">
                    Tie detected across the cutoff. Use an audited balance
                    correction or change the number before locking.
                  </p>
                )}
                {data?.qualification.finalized && (
                  <p className="r3-lock-confirmation">
                    Locked: {data.qualification.qualified_team_ids.join(", ")}
                  </p>
                )}
              </div>
            </>
          )}
          {section === "PUZZLES" && (
            <>
              <div className="r3-section-head">
                <span className="r3-kicker">PRIVATE / ANSWER VAULT</span>
                <h2>{bank?.total ?? "275"} puzzles, ready.</h2>
                <p>
                  Only super admins can open this catalogue. Participant and
                  station browsers never receive an answer until the server has
                  validated their locked submission.
                </p>
              </div>
              <div className="r3-bank-toolbar">
                <div className="r3-bank-tabs">
                  {bank?.tables.map((table) => (
                    <button
                      key={table.table_number}
                      className={
                        bankTable === table.table_number ? "active" : ""
                      }
                      onClick={() => setBankTable(table.table_number)}
                    >
                      <b>{String(table.table_number).padStart(2, "0")}</b>
                      <span>{table.station_name}</span>
                      <small>{table.count}</small>
                    </button>
                  ))}
                </div>
                <label className="r3-bank-search">
                  <Search size={17} />
                  <input
                    value={bankQuery}
                    onChange={(event) => setBankQuery(event.target.value)}
                    placeholder="Search question, ID or answer"
                  />
                </label>
              </div>
              {!bank ? (
                <div className="r3-empty">
                  <RefreshCw size={28} />
                  <h3>Opening the private vault…</h3>
                </div>
              ) : (
                <div className="r3-bank-list">
                  {bank.tables
                    .find((table) => table.table_number === bankTable)
                    ?.puzzles.filter((puzzle) => {
                      const query = bankQuery.trim().toLowerCase();
                      return (
                        !query ||
                        [
                          puzzle.key,
                          puzzle.title,
                          puzzle.prompt,
                          ...puzzle.display,
                          ...puzzle.answers,
                        ]
                          .join(" ")
                          .toLowerCase()
                          .includes(query)
                      );
                    })
                    .map((puzzle) => (
                      <details className="r3-bank-card" key={puzzle.key}>
                        <summary>
                          <span>{puzzle.key}</span>
                          <b>{puzzle.title}</b>
                          <small>{puzzle.eyebrow}</small>
                          <ArrowUpRight size={15} />
                        </summary>
                        <div>
                          <p>{puzzle.story}</p>
                          <ul>
                            {puzzle.display.map((line, index) => (
                              <li key={index}>{line}</li>
                            ))}
                          </ul>
                          <h4>{puzzle.prompt}</h4>
                          <aside>
                            <small>
                              ACCEPTED ANSWER
                              {puzzle.answers.length > 1 ? "S" : ""}
                            </small>
                            <strong>{puzzle.answers.join(" / ")}</strong>
                          </aside>
                        </div>
                      </details>
                    ))}
                </div>
              )}
            </>
          )}
          {section === "DEALERS" && (
            <>
              <div className="r3-section-head">
                <span className="r3-kicker">
                  PUZZLE LAPTOPS / CONFIGURATION
                </span>
                <h2>Build the automated floor.</h2>
                <p>
                  Each admin account stays signed in on one laptop. Set its
                  room, point award and display name; teams enter their arrival
                  code and the system handles everything else.
                </p>
              </div>
              <div className="r3-dealer-grid">
                {data?.tables.map((table) => {
                  const draft = tablesDraft[table.number];
                  return (
                    <form
                      className="r3-dealer-card"
                      key={table.number}
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (draft)
                          void act(
                            "/r3-live/control/tables/" + table.number,
                            {
                              table_number: Number(draft.number),
                              room_number: Number(draft.room),
                              game_mode: "ONLINE",
                              admin_login_id: draft.admin,
                              game_name: draft.name,
                              max_points: Number(draft.max),
                              is_enabled: draft.enabled,
                            },
                            "Table " + draft.number + " updated.",
                          );
                      }}
                    >
                      <div className="r3-card-title">
                        <span>
                          STATION {String(table.number).padStart(2, "0")}
                        </span>
                        <span
                          className={
                            "r3-state-pill " +
                            (table.enabled ? "live" : "draft")
                          }
                        >
                          {table.enabled ? "READY" : "SETUP"}
                        </span>
                      </div>
                      <div className="r3-dealer-fields">
                        <label>
                          Table number
                          <input
                            type="number"
                            min="1"
                            max="99"
                            disabled={data.started}
                            value={draft?.number || ""}
                            onChange={(event) =>
                              setTablesDraft((current) => ({
                                ...current,
                                [table.number]: {
                                  ...current[table.number],
                                  number: event.target.value,
                                },
                              }))
                            }
                          />
                        </label>
                        <label>
                          Room number
                          <input
                            type="number"
                            min="1"
                            max="9999"
                            disabled={data.started}
                            value={draft?.room || ""}
                            onChange={(event) =>
                              setTablesDraft((current) => ({
                                ...current,
                                [table.number]: {
                                  ...current[table.number],
                                  room: event.target.value,
                                },
                              }))
                            }
                          />
                        </label>
                        <label>
                          Station mode
                          <input disabled value="Automated laptop" readOnly />
                        </label>
                        <label>
                          Laptop account
                          <select
                            disabled={data.started}
                            value={draft?.admin || ""}
                            onChange={(event) =>
                              setTablesDraft((current) => ({
                                ...current,
                                [table.number]: {
                                  ...current[table.number],
                                  admin: event.target.value,
                                },
                              }))
                            }
                          >
                            <option value="">Assign account</option>
                            {data.admins
                              .filter((admin) => admin.is_active)
                              .map((admin) => (
                                <option
                                  key={admin.login_id}
                                  value={admin.login_id}
                                >
                                  {admin.login_id} · {admin.display_name}
                                </option>
                              ))}
                          </select>
                        </label>
                        <label className="r3-full">
                          Station name
                          <input
                            disabled={data.started}
                            minLength={3}
                            value={draft?.name || ""}
                            onChange={(event) =>
                              setTablesDraft((current) => ({
                                ...current,
                                [table.number]: {
                                  ...current[table.number],
                                  name: event.target.value,
                                },
                              }))
                            }
                          />
                        </label>
                        <label>
                          Points for correct answer
                          <input
                            type="number"
                            min="1"
                            max="100"
                            disabled={data.started}
                            value={draft?.max || ""}
                            onChange={(event) =>
                              setTablesDraft((current) => ({
                                ...current,
                                [table.number]: {
                                  ...current[table.number],
                                  max: event.target.value,
                                },
                              }))
                            }
                          />
                        </label>
                        <label className="r3-toggle">
                          <input
                            type="checkbox"
                            disabled={data.started}
                            checked={!!draft?.enabled}
                            onChange={(event) =>
                              setTablesDraft((current) => ({
                                ...current,
                                [table.number]: {
                                  ...current[table.number],
                                  enabled: event.target.checked,
                                },
                              }))
                            }
                          />{" "}
                          Enable station
                        </label>
                      </div>
                      <button
                        className="r3-button peach"
                        disabled={busy || data.started}
                      >
                        Save station
                      </button>
                    </form>
                  );
                })}
              </div>
              <form
                className="r3-panel-box r3-add-admin"
                onSubmit={async (event) => {
                  event.preventDefault();
                  if (
                    await act(
                      "/r3-live/control/admins",
                      newAdmin,
                      "Laptop account created. Assign it to a station.",
                    )
                  )
                    setNewAdmin({
                      login_id: "",
                      display_name: "",
                      password: "",
                    });
                }}
              >
                <span className="r3-kicker">
                  <Plus size={15} /> LAPTOP ACCESS
                </span>
                <h3>Add another station account</h3>
                <p>
                  Use an ID such as ADMIN09. This login is only a kiosk
                  identity; no person needs to score or operate it.
                </p>
                <div className="r3-admin-fields">
                  <label>
                    Admin ID
                    <input
                      required
                      pattern="ADMIN[0-9]{2,3}"
                      placeholder="ADMIN09"
                      disabled={data?.started}
                      value={newAdmin.login_id}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          login_id: event.target.value.toUpperCase(),
                        })
                      }
                    />
                  </label>
                  <label>
                    Display name
                    <input
                      required
                      minLength={2}
                      disabled={data?.started}
                      value={newAdmin.display_name}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          display_name: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Initial password
                    <input
                      required
                      minLength={8}
                      type="password"
                      disabled={data?.started}
                      value={newAdmin.password}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          password: event.target.value,
                        })
                      }
                    />
                  </label>
                  <button
                    className="r3-button ghost"
                    disabled={busy || data?.started}
                  >
                    Create account
                  </button>
                </div>
              </form>
            </>
          )}
          {section === "AUCTION" && (
            <>
              <div className="r3-section-head">
                <span className="r3-kicker">AUCTIONEER / CONTROL DESK</span>
                <h2>Release intelligence.</h2>
                <p>
                  Configure a public teaser and winner-only clue. Release lots
                  during the live 30-minute window; settle each one to charge
                  the winner.
                </p>
              </div>
              <div className="r3-lot-editor-grid">
                {data?.lots.map((lot) => {
                  const draft = lotsDraft[lot.id];
                  return (
                    <form
                      className="r3-panel-box r3-lot-editor"
                      key={lot.id}
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (draft)
                          void act(
                            "/r3-live/control/lots/" + lot.id + "/configure",
                            {
                              opening_bid: Number(draft.opening),
                              description: draft.description,
                              clue_text: draft.clue_text,
                            },
                            "Clue saved.",
                          );
                      }}
                    >
                      <div className="r3-card-title">
                        <span>
                          LEVEL {lot.level} · TOKEN {lot.token_number}
                        </span>
                        <span
                          className={
                            "r3-state-pill " + lot.status.toLowerCase()
                          }
                        >
                          {lot.status}
                        </span>
                      </div>
                      <h3>{lot.title}</h3>
                      <p>
                        Current high: {points(lot.highest_bid)} · Winner:{" "}
                        {lot.winner_team_id || "None yet"}
                      </p>
                      <label>
                        Public teaser
                        <input
                          disabled={lot.status !== "DRAFT"}
                          value={draft?.description || ""}
                          onChange={(event) =>
                            setLotsDraft((current) => ({
                              ...current,
                              [lot.id]: {
                                ...current[lot.id],
                                description: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                      <label>
                        Winner-only clue
                        <textarea
                          disabled={lot.status !== "DRAFT"}
                          value={draft?.clue_text || ""}
                          onChange={(event) =>
                            setLotsDraft((current) => ({
                              ...current,
                              [lot.id]: {
                                ...current[lot.id],
                                clue_text: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                      <label>
                        Opening bid
                        <input
                          type="number"
                          min="0"
                          disabled={lot.status !== "DRAFT"}
                          value={draft?.opening || ""}
                          onChange={(event) =>
                            setLotsDraft((current) => ({
                              ...current,
                              [lot.id]: {
                                ...current[lot.id],
                                opening: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                      <div className="r3-inline-actions">
                        {lot.status === "DRAFT" && (
                          <>
                            <button className="r3-button ghost" disabled={busy}>
                              Save clue
                            </button>
                            <button
                              type="button"
                              className="r3-button peach"
                              disabled={!data.open || busy}
                              onClick={() =>
                                void act(
                                  "/r3-live/control/lots/" + lot.id + "/open",
                                  {},
                                  "Lot released.",
                                )
                              }
                            >
                              Release now
                            </button>
                          </>
                        )}
                        {lot.status === "LIVE" && (
                          <button
                            type="button"
                            className="r3-button peach"
                            disabled={busy}
                            onClick={() => {
                              if (
                                window.confirm(
                                  "Close " +
                                    lot.title +
                                    " and charge the winning team?",
                                )
                              )
                                void act(
                                  "/r3-live/control/lots/" + lot.id + "/close",
                                  {},
                                  "Lot settled.",
                                );
                            }}
                          >
                            Close and settle
                          </button>
                        )}
                      </div>
                    </form>
                  );
                })}
              </div>
            </>
          )}
          {section === "TEAMS" && (
            <>
              <div className="r3-section-head">
                <span className="r3-kicker">
                  PRIVATE LEDGER / THIRTEEN TEAMS
                </span>
                <h2>Every point accounted for.</h2>
                <p>
                  Verify opening figures before start. During the round, use a
                  reasoned correction; the ledger records every adjustment.
                </p>
              </div>
              <div className="r3-team-grid">
                {data?.teams.map((team) => (
                  <form
                    className="r3-team-row"
                    key={team.team_identifier}
                    onSubmit={(event) => {
                      event.preventDefault();
                      void act(
                        "/r3-live/control/teams/opening-points",
                        {
                          team_identifier: team.team_identifier,
                          points: Number(pointsDraft[team.team_identifier]),
                        },
                        "Opening points updated.",
                      );
                    }}
                  >
                    <div>
                      <b>{team.team_identifier}</b>
                      <span>{team.team_name}</span>
                      <small>
                        {team.played}/{team.members} played
                      </small>
                    </div>
                    <label>
                      Opening points
                      <input
                        type="number"
                        min="0"
                        disabled={data.started}
                        value={pointsDraft[team.team_identifier] ?? ""}
                        onChange={(event) =>
                          setPointsDraft((current) => ({
                            ...current,
                            [team.team_identifier]: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <strong>{points(team.balance)}</strong>
                    <div className="r3-inline-actions">
                      {!data.started && (
                        <button className="r3-button ghost" disabled={busy}>
                          Save
                        </button>
                      )}
                      <button
                        type="button"
                        className="r3-button ghost"
                        onClick={() =>
                          void request<TeamState>(
                            "/r3-live/control/teams/" + team.team_identifier,
                          )
                            .then(setSelected)
                            .catch((problem) => setError(errorText(problem)))
                        }
                      >
                        Inspect
                      </button>
                    </div>
                  </form>
                ))}
              </div>
              {selected && (
                <div className="r3-panel-box r3-inspect">
                  <div className="r3-card-title">
                    <span>
                      {selected.team_identifier} · {selected.team_name}
                    </span>
                    <button
                      className="r3-text-button"
                      onClick={() => setSelected(null)}
                    >
                      Close
                    </button>
                  </div>
                  <h3>{points(selected.balance)} points</h3>
                  <p>
                    {selected.games_completed}/{selected.members.length} members
                    played · {selected.active_devices}/3 active devices.
                  </p>
                  {selected.ledger.map((entry, index) => (
                    <div className="r3-ledger-line" key={entry.at + index}>
                      <span>
                        {entry.description}
                        <small>
                          {entry.category} · {clock(entry.at)}
                        </small>
                      </span>
                      <b className={entry.delta < 0 ? "debit" : ""}>
                        {entry.delta > 0 ? "+" : ""}
                        {points(entry.delta)}
                      </b>
                    </div>
                  ))}
                </div>
              )}
              <form
                className="r3-panel-box r3-adjust"
                onSubmit={async (event: FormEvent) => {
                  event.preventDefault();
                  if (
                    await act(
                      "/r3-live/control/teams/adjust",
                      { ...correction, delta: Number(correction.delta) },
                      "Audited point correction saved.",
                    )
                  )
                    setCorrection({
                      team_identifier: "",
                      delta: "",
                      reason: "",
                    });
                }}
              >
                <span className="r3-kicker">AUDITED SUPER ADMIN ACTION</span>
                <h3>Correct a live balance</h3>
                <p>
                  Positive points credit a team; negative points deduct. A
                  reason is saved in their private ledger.
                </p>
                <div className="r3-admin-fields">
                  <label>
                    Team
                    <select
                      required
                      disabled={!data?.started || busy}
                      value={correction.team_identifier}
                      onChange={(event) =>
                        setCorrection({
                          ...correction,
                          team_identifier: event.target.value,
                        })
                      }
                    >
                      <option value="">Choose team</option>
                      {data?.teams.map((team) => (
                        <option
                          key={team.team_identifier}
                          value={team.team_identifier}
                        >
                          {team.team_identifier} · {team.team_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Points ±
                    <input
                      required
                      type="number"
                      step="0.01"
                      disabled={!data?.started || busy}
                      value={correction.delta}
                      onChange={(event) =>
                        setCorrection({
                          ...correction,
                          delta: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Reason
                    <input
                      required
                      minLength={5}
                      disabled={!data?.started || busy}
                      value={correction.reason}
                      onChange={(event) =>
                        setCorrection({
                          ...correction,
                          reason: event.target.value,
                        })
                      }
                    />
                  </label>
                  <button
                    className="r3-button peach"
                    disabled={!data?.started || busy}
                  >
                    Record correction
                  </button>
                </div>
              </form>
            </>
          )}
          {section === "HANDOFF" && (
            <>
              <div className="r3-section-head">
                <span className="r3-kicker">LIVE STAFF OPERATIONS</span>
                <h2>Keep the floor moving.</h2>
                <p>
                  Replace a dealer or move a station to another room without
                  changing its game or table number. The old dealer loses access
                  and the new dealer's station updates automatically.
                </p>
              </div>
              <div className="r3-dealer-grid">
                {data?.tables.map((table) => (
                  <form
                    className="r3-dealer-card"
                    key={table.number}
                    onSubmit={(event) => {
                      event.preventDefault();
                      const draft = tablesDraft[table.number];
                      if (draft)
                        void act(
                          "/r3-live/control/tables/" + table.number + "/dealer",
                          {
                            admin_login_id: draft.admin,
                            room_number: Number(draft.room),
                          },
                          "Table " + table.number + " handoff saved.",
                        );
                    }}
                  >
                    <div className="r3-card-title">
                      <span>
                        TABLE {String(table.number).padStart(2, "0")} /{" "}
                        {table.game_name}
                      </span>
                      <span className="r3-state-pill">{table.mode}</span>
                    </div>
                    <p>
                      Current dealer: {table.admin || "Unassigned"} · Room{" "}
                      {table.room}
                    </p>
                    <div className="r3-dealer-fields">
                      <label>
                        Dealer admin
                        <select
                          required
                          value={tablesDraft[table.number]?.admin || ""}
                          onChange={(event) =>
                            setTablesDraft((current) => ({
                              ...current,
                              [table.number]: {
                                ...current[table.number],
                                admin: event.target.value,
                              },
                            }))
                          }
                        >
                          <option value="">Select active admin</option>
                          {data.admins
                            .filter((admin) => admin.is_active)
                            .map((admin) => (
                              <option
                                key={admin.login_id}
                                value={admin.login_id}
                              >
                                {admin.login_id} · {admin.display_name}
                              </option>
                            ))}
                        </select>
                      </label>
                      <label>
                        Room number
                        <input
                          required
                          type="number"
                          min="1"
                          max="9999"
                          value={tablesDraft[table.number]?.room || ""}
                          onChange={(event) =>
                            setTablesDraft((current) => ({
                              ...current,
                              [table.number]: {
                                ...current[table.number],
                                room: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                    </div>
                    <button className="r3-button peach" disabled={busy}>
                      Save live assignment
                    </button>
                  </form>
                ))}
              </div>
              <form
                className="r3-panel-box r3-add-admin"
                onSubmit={async (event) => {
                  event.preventDefault();
                  if (
                    await act(
                      "/r3-live/control/admins",
                      newAdmin,
                      "Dealer admin created. Assign them above.",
                    )
                  )
                    setNewAdmin({
                      login_id: "",
                      display_name: "",
                      password: "",
                    });
                }}
              >
                <span className="r3-kicker">
                  <Plus size={15} /> RESERVE STAFF
                </span>
                <h3>Add an admin at any time</h3>
                <p>
                  A new dealer gets no table access until you assign them above.
                  Use the account page later to change their initial password.
                </p>
                <div className="r3-admin-fields">
                  <label>
                    Admin ID
                    <input
                      required
                      pattern="ADMIN[0-9]{2,3}"
                      placeholder="ADMIN09"
                      value={newAdmin.login_id}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          login_id: event.target.value.toUpperCase(),
                        })
                      }
                    />
                  </label>
                  <label>
                    Display name
                    <input
                      required
                      minLength={2}
                      value={newAdmin.display_name}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          display_name: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Initial password
                    <input
                      required
                      minLength={8}
                      type="password"
                      value={newAdmin.password}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          password: event.target.value,
                        })
                      }
                    />
                  </label>
                  <button className="r3-button ghost" disabled={busy}>
                    Create reserve admin
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </Page>
  );
}

export function Round3AdminPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<Dealer | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const load = (silent = false) =>
    request<Dealer>("/r3-live/admin/table")
      .then(setData)
      .catch((problem) => {
        if (!silent) setError(errorText(problem));
      });
  useEffect(() => {
    if (getSession()?.role !== "ADMIN") {
      navigate("/login", { replace: true });
      return;
    }
    void load();
    const timer = window.setInterval(() => void load(true), 4000);
    return () => window.clearInterval(timer);
  }, []);
  async function act(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(path, "POST", body || {});
      setNotice("Dealer result recorded on the team ledger.");
      await load(true);
    } catch (problem) {
      setError(errorText(problem));
      await load(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Page back="/station" className="r3-admin">
      <section className="r3-hero" data-r3-reveal>
        <div>
          <span className="r3-kicker">
            <Radio size={14} /> DEALER ACCESS / ROUND 03
          </span>
          <h1>
            Table <em>{data?.number || "—"}.</em>
          </h1>
          <p>
            {data?.assigned
              ? "Room " + data.room + " · " + data.mode + " · " + data.game_name
              : "Awaiting your station assignment from the super admin."}
          </p>
        </div>
        <div className="r3-hero-clock">
          <small>YOUR ROLE</small>
          <strong>DEALER</strong>
          <span>
            Start the first reserved player, score objectively, and release the
            table.
          </span>
        </div>
      </section>
      <Alert error={error} notice={notice} />
      <section className="r3-panel-box r3-dealer-board" data-r3-reveal>
        <div className="r3-section-head">
          <span className="r3-kicker">FIRST COME, FIRST SERVED</span>
          <h2>Your station queue.</h2>
          <p>
            Verify the named player and table on their phone. A game started
            before the market deadline receives its complete 75 seconds, even if
            the market closes.
          </p>
        </div>
        <button className="r3-button ghost" onClick={() => void load()}>
          <RefreshCw size={16} /> Refresh station
        </button>
        {data?.attempts?.length ? (
          data.attempts.map((attempt) => (
            <article
              className={"r3-dealer-turn " + attempt.status.toLowerCase()}
              key={attempt.id}
            >
              <div>
                <span className="r3-kicker">
                  {attempt.status} · TABLE {attempt.table_number}
                </span>
                <h3>{attempt.participant_name}</h3>
                <p>
                  {attempt.team_identifier} · request logged{" "}
                  {clock(attempt.spun_at)}
                </p>
                {attempt.status === "QUEUED" && (
                  <small>
                    Queue position #{attempt.queue_position} · joined{" "}
                    {clock(attempt.queued_at)}
                  </small>
                )}
              </div>
              <div className="r3-dealer-turn-action">
                {attempt.status === "RESERVED" && (
                  <button
                    className="r3-button peach"
                    disabled={busy}
                    onClick={() =>
                      void act(
                        "/r3-live/admin/attempts/" + attempt.id + "/start",
                      )
                    }
                  >
                    Start 75-second game <Timer size={16} />
                  </button>
                )}
                {attempt.status === "ACTIVE" && (
                  <form
                    onSubmit={(event: FormEvent) => {
                      event.preventDefault();
                      void act(
                        "/r3-live/admin/attempts/" + attempt.id + "/finish",
                        {
                          points: Number(scores[attempt.id]),
                          note: notes[attempt.id],
                        },
                      );
                    }}
                  >
                    <span>
                      GAME CLOCK{" "}
                      <Countdown
                        until={
                          attempt.started_at
                            ? new Date(
                                new Date(attempt.started_at).getTime() + 75000,
                              ).toISOString()
                            : null
                        }
                      />
                    </span>
                    <label>
                      Points earned / max {data.max_points}
                      <input
                        required
                        type="number"
                        min="0"
                        max={data.max_points}
                        value={scores[attempt.id] || ""}
                        onChange={(event) =>
                          setScores({
                            ...scores,
                            [attempt.id]: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      Outcome note
                      <input
                        required
                        minLength={3}
                        maxLength={500}
                        placeholder="Brief objective result"
                        value={notes[attempt.id] || ""}
                        onChange={(event) =>
                          setNotes({
                            ...notes,
                            [attempt.id]: event.target.value,
                          })
                        }
                      />
                    </label>
                    <button className="r3-button peach" disabled={busy}>
                      Score & release
                    </button>
                  </form>
                )}
              </div>
            </article>
          ))
        ) : (
          <div className="r3-empty">
            <Users size={28} />
            <h3>No one in line yet.</h3>
            <p>Your station updates automatically every four seconds.</p>
          </div>
        )}
      </section>
    </Page>
  );
}
