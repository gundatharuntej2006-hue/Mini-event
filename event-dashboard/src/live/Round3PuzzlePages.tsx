import {
  CSSProperties,
  FormEvent,
  ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Gavel,
  KeyRound,
  LockKeyhole,
  LogOut,
  MapPin,
  Radio,
  RefreshCw,
  Sparkles,
  Timer,
  Users,
  Volume2,
  Wallet,
  XCircle,
  Zap,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { LiveShell, Mark } from "./LiveShell";
import { clearSession, getSession, request } from "./eventApi";

type Member = {
  id: string;
  name: string;
  played: boolean;
  games_completed: number;
};
type Puzzle = {
  key: string;
  title: string;
  eyebrow: string;
  story: string;
  prompt: string;
  display: string[];
  options: string[];
  answer_label: string;
  visual_kind:
    | "logic"
    | "pattern"
    | "word"
    | "spatial"
    | "deduction"
    | "observation"
    | "sequence"
    | "quick";
};
type Attempt = {
  id: string;
  table_number: number;
  room_number: number;
  game_name: string;
  game_mode: string;
  status: "RESERVED" | "ACTIVE" | "COMPLETE";
  participant_id: string;
  participant_name: string;
  reserved_until: string | null;
  started_at: string | null;
  spun_at: string | null;
  points: number | null;
  correct?: boolean | null;
  access_code?: string;
  access_code_revealed?: boolean;
  team_identifier?: string;
  puzzle?: Puzzle | null;
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
};
type Ledger = {
  delta: number;
  category: string;
  description: string;
  at: string;
};
type Team = {
  team_identifier: string;
  team_name: string;
  opening_points: number;
  balance: number;
  available_to_bid: number;
  members: Member[];
  ledger: Ledger[];
  attempts: Attempt[];
  games_completed: number;
  active_devices: number;
};
type ParticipantState = {
  open: boolean;
  starts_at: string | null;
  ends_at: string | null;
  team: Team;
  lots: Lot[];
};
type StationState = {
  assigned: boolean;
  started: boolean;
  number?: number;
  room?: number;
  game_name?: string;
  max_points?: number;
  attempts?: Attempt[];
};

const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
const points = (value: number | null | undefined) =>
  typeof value === "number"
    ? value.toLocaleString("en-IN", { maximumFractionDigits: 2 })
    : "—";

function playAuctionBell() {
  const AudioContextClass =
    window.AudioContext ||
    (window as typeof window & { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;
  if (!AudioContextClass) return;
  const context = new AudioContextClass();
  const now = context.currentTime;
  [660, 990, 1320].forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, now);
    gain.gain.setValueAtTime(0.0001, now + index * 0.04);
    gain.gain.exponentialRampToValueAtTime(0.18 / (index + 1), now + 0.025 + index * 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.15 + index * 0.08);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(now + index * 0.04);
    oscillator.stop(now + 1.3 + index * 0.08);
  });
  window.setTimeout(() => void context.close(), 1700);
}

function speakAuctionRelease(title: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const message = new SpeechSynthesisUtterance(
    `Attention. Auction item released. ${title}. Bidding is now open.`,
  );
  message.rate = 0.88;
  message.pitch = 0.82;
  message.volume = 1;
  window.speechSynthesis.speak(message);
}

function Countdown({
  until,
  onEnd,
}: {
  until: string | null | undefined;
  onEnd?: () => void;
}) {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    let ended = false;
    const tick = () => {
      const next = Math.max(
        0,
        Math.ceil((new Date(until || 0).getTime() - Date.now()) / 1000),
      );
      setRemaining(next);
      if (!next && !ended) {
        ended = true;
        onEnd?.();
      }
    };
    tick();
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [until]);
  return (
    <span className={remaining <= 10 ? "puzzle-clock danger" : "puzzle-clock"}>
      {String(Math.floor(remaining / 60)).padStart(2, "0")}:
      {String(remaining % 60).padStart(2, "0")}
    </span>
  );
}

function Shell({
  children,
  signout = false,
  back = "/station",
}: {
  children: ReactNode;
  signout?: boolean;
  back?: string;
}) {
  const navigate = useNavigate();
  const leave = async () => {
    if (signout)
      await request("/r3-live/participant/signout", "POST", {}).catch(
        () => undefined,
      );
    clearSession();
    navigate("/login");
  };
  return (
    <LiveShell>
      <main className="puzzle-app">
        <div className="puzzle-noise" aria-hidden="true" />
        <header className="puzzle-topbar">
          <Mark />
          <span>
            <i /> ROUND 03 / AUTOMATED FLOOR
          </span>
          <button
            onClick={signout ? leave : () => navigate(back)}
            aria-label={signout ? "Sign out" : "Back"}
          >
            {signout ? <LogOut size={18} /> : <ArrowLeft size={18} />}
          </button>
        </header>
        {children}
      </main>
    </LiveShell>
  );
}

type DemoPuzzle = Puzzle & { answers: string[]; quirky?: boolean };
type DemoBank = {
  total: number;
  game_seconds: number;
  tables: { table_number: number; station_name: string; puzzles: DemoPuzzle[] }[];
};

export function Round3PuzzleDemoPage() {
  const navigate = useNavigate();
  const [bank, setBank] = useState<DemoBank | null>(null);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState("");
  const [deadline, setDeadline] = useState<string | null>(null);
  const [result, setResult] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (getSession()?.role !== "SUPER_ADMIN") {
      navigate("/login", { replace: true });
      return;
    }
    request<DemoBank>("/r3-live/control/puzzle-bank")
      .then(setBank)
      .catch((problem) => setError(errorText(problem)));
  }, []);
  const puzzles = useMemo(
    () => bank?.tables.flatMap((table) => table.puzzles) || [],
    [bank],
  );
  const puzzle = puzzles[index % Math.max(1, puzzles.length)];
  const start = (next = index) => {
    setIndex(next % Math.max(1, puzzles.length));
    setSelected("");
    setResult(null);
    setDeadline(new Date(Date.now() + 75000).toISOString());
  };
  const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");
  return (
    <Shell back="/round3/control">
      <section className="station-header">
        <div>
          <span className="puzzle-kicker"><Sparkles size={14} /> SAFE ORGANIZER DEMO</span>
          <h1>Practice <em>station</em></h1>
          <p>No points, attempts, question usage, or live queues are saved here.</p>
        </div>
        <div><small>QUESTION BANK</small><strong>{bank?.total || "—"}</strong></div>
      </section>
      <Alert error={error} notice={result === true ? "Correct — demo only." : result === false ? "Incorrect or timed out — demo only." : ""} />
      {!puzzle || !deadline ? (
        <section className="station-wait">
          <Sparkles />
          <h2>Run a harmless practice session.</h2>
          <p>This previews the real 75-second MCQ flow without touching production scores.</p>
          <button disabled={!puzzles.length} onClick={() => start(0)}>Start demo</button>
        </section>
      ) : (
        <section className="station-puzzle">
          <header>
            <div><span>{puzzle.eyebrow}</span><h2>{puzzle.title}</h2></div>
            <div><small>DEMO TIME</small><Countdown until={deadline} onEnd={() => setResult(false)} /></div>
          </header>
          <div className="puzzle-brief">
            <p>{puzzle.story}</p>
            <PuzzleVisual puzzle={puzzle} />
            <div className="puzzle-display">{puzzle.display.map((line, lineIndex) => <div key={lineIndex}><span>{String(lineIndex + 1).padStart(2, "0")}</span><b>{line}</b></div>)}</div>
            <h3>{puzzle.prompt}</h3>
          </div>
          <div className="answer-lock">
            <div className="answer-options" role="radiogroup">{puzzle.options.map((option, optionIndex) => <button key={option} type="button" role="radio" aria-checked={selected === option} className={selected === option ? "selected" : ""} disabled={result !== null} onClick={() => setSelected(option)}><span>{String.fromCharCode(65 + optionIndex)}</span><b>{option}</b></button>)}</div>
            {result === null ? <button disabled={!selected} onClick={() => setResult(puzzle.answers.some((answer) => normalize(answer) === normalize(selected)))}>Lock demo option <LockKeyhole size={19} /></button> : <button onClick={() => start(index + 1)}>Next demo question <RefreshCw size={18} /></button>}
          </div>
        </section>
      )}
      <footer className="puzzle-footer">DEMO ONLY <span>ZERO DATABASE WRITES</span></footer>
    </Shell>
  );
}

function Alert({ error, notice }: { error: string; notice: string }) {
  return (
    <>
      {error && (
        <div className="puzzle-alert error">
          <XCircle size={18} />
          {error}
        </div>
      )}
      {notice && (
        <div className="puzzle-alert">
          <CheckCircle2 size={18} />
          {notice}
        </div>
      )}
    </>
  );
}

const visualCopy: Record<
  Puzzle["visual_kind"],
  { glyph: string; label: string; cue: string }
> = {
  logic: { glyph: "IF / THEN", label: "Truth matrix", cue: "Test each claim" },
  pattern: {
    glyph: "◼ ○ △",
    label: "Pattern engine",
    cue: "Find the movement",
  },
  word: { glyph: "A ↔ Z", label: "Word scanner", cue: "Read between lines" },
  spatial: { glyph: "N ↑", label: "Spatial map", cue: "Track every move" },
  deduction: {
    glyph: "∑ ?",
    label: "Evidence desk",
    cue: "Use only the facts",
  },
  observation: {
    glyph: "[ SCAN ]",
    label: "Detail scanner",
    cue: "Notice the outlier",
  },
  sequence: {
    glyph: "01 → 02",
    label: "Sequence signal",
    cue: "Predict the next beat",
  },
  quick: { glyph: "!", label: "Trapdoor", cue: "Read before reacting" },
};

function PuzzleVisual({ puzzle }: { puzzle: Puzzle }) {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const copy = visualCopy[puzzle.visual_kind] || visualCopy.logic;
  const style = {
    "--puzzle-rx": `${tilt.y}deg`,
    "--puzzle-ry": `${tilt.x}deg`,
  } as CSSProperties;

  return (
    <div
      className={`puzzle-visual ${puzzle.visual_kind}`}
      style={style}
      onPointerMove={(event) => {
        const box = event.currentTarget.getBoundingClientRect();
        setTilt({
          x: ((event.clientX - box.left) / box.width - 0.5) * 8,
          y: -((event.clientY - box.top) / box.height - 0.5) * 8,
        });
      }}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
    >
      <div className="visual-grid" aria-hidden="true" />
      <div className="visual-orbit" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </div>
      <div className="visual-core">
        <small>{copy.cue}</small>
        <strong>{copy.glyph}</strong>
        <span>{copy.label}</span>
      </div>
      <b>TOUCH / MOVE TO INSPECT</b>
    </div>
  );
}

export function Round3PuzzleParticipantPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<ParticipantState | null>(null);
  const [member, setMember] = useState("");
  const [view, setView] = useState<"MISSIONS" | "AUCTION">("MISSIONS");
  const [bid, setBid] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [auctionAudio, setAuctionAudio] = useState(
    () => window.localStorage.getItem("r3-auction-audio") === "on",
  );
  const previousLotStatus = useRef<Map<string, string> | null>(null);
  const load = (quiet = false) =>
    request<ParticipantState>("/r3-live/participant/state")
      .then(setData)
      .catch((problem) => {
        if (!quiet) setError(errorText(problem));
      });
  useEffect(() => {
    if (getSession()?.role !== "PARTICIPANT") {
      navigate("/login", { replace: true });
      return;
    }
    void load();
    const timer = window.setInterval(() => void load(true), 2500);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!data?.lots) return;
    const current = new Map(data.lots.map((lot) => [lot.id, lot.status]));
    if (previousLotStatus.current && auctionAudio) {
      const released = data.lots.filter(
        (lot) =>
          lot.status === "LIVE" &&
          previousLotStatus.current?.get(lot.id) !== "LIVE",
      );
      released.forEach((lot, index) => {
        window.setTimeout(() => {
          playAuctionBell();
          window.setTimeout(() => speakAuctionRelease(lot.title), 850);
        }, index * 2600);
      });
    }
    previousLotStatus.current = current;
  }, [data?.lots, auctionAudio]);
  async function post(path: string, body?: unknown, success = "Updated.") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await request<Attempt>(path, "POST", body ?? {});
      setNotice(success);
      await load(true);
      return result;
    } catch (problem) {
      setError(errorText(problem));
      return null;
    } finally {
      setBusy(false);
    }
  }
  async function assign() {
    if (!member) return;
    const result = await post("/r3-live/participant/assign", {
      participant_id: member,
    });
    if (result)
      setNotice(
        `Table ${result.table_number} is reserved. Take ${result.participant_name} to Room ${result.room_number}, then send the three-digit code from this screen.`,
      );
  }
  const team = data?.team;
  const active = team?.attempts || [];
  return (
    <Shell signout>
      <section className="puzzle-hero">
        <div>
          <span className="puzzle-kicker">
            <Radio size={14} /> THE PUZZLE CIRCUIT
          </span>
          <h1>
            Move fast.
            <br />
            <em>Think sideways.</em>
          </h1>
          <p>
            Pick a teammate and receive the best available station
            automatically. The laptop does the rest.
          </p>
          <b>
            {team?.team_identifier || "TEAM"} / {team?.team_name || "Loading…"}
          </b>
        </div>
        <div className="puzzle-round-clock">
          <small>FLOOR CLOSES IN</small>
          {data?.open ? (
            <Countdown until={data.ends_at} />
          ) : (
            <strong>30:00</strong>
          )}
          <span>
            Any puzzle started before closing keeps its full 75 seconds.
          </span>
        </div>
      </section>
      <Alert error={error} notice={notice} />
      <section className="puzzle-stats">
        <div>
          <Wallet />
          <span>
            <small>PRIVATE BALANCE</small>
            <b>{points(team?.balance)}</b>
          </span>
        </div>
        <div>
          <Zap />
          <span>
            <small>PUZZLES PLAYED</small>
            <b>{team?.games_completed ?? 0}</b>
          </span>
        </div>
        <div>
          <Users />
          <span>
            <small>LIVE ASSIGNMENTS</small>
            <b>{active.length} / 2</b>
          </span>
        </div>
        <div>
          <Gavel />
          <span>
            <small>AVAILABLE TO BID</small>
            <b>{points(team?.available_to_bid)}</b>
          </span>
        </div>
      </section>
      <nav className="puzzle-tabs">
        <button
          className={view === "MISSIONS" ? "active" : ""}
          onClick={() => setView("MISSIONS")}
        >
          <Zap size={17} /> Puzzle circuit
        </button>
        <button
          className={view === "AUCTION" ? "active" : ""}
          onClick={() => setView("AUCTION")}
        >
          <Gavel size={17} /> Clue auction
        </button>
        <button
          className={auctionAudio ? "audio-on" : ""}
          onClick={() => {
            const enabled = !auctionAudio;
            setAuctionAudio(enabled);
            window.localStorage.setItem(
              "r3-auction-audio",
              enabled ? "on" : "off",
            );
            if (enabled) {
              playAuctionBell();
              window.setTimeout(
                () => speakAuctionRelease("Audio alerts enabled"),
                650,
              );
            } else if ("speechSynthesis" in window) {
              window.speechSynthesis.cancel();
            }
          }}
          title="Browsers require one tap before auction audio can play"
        >
          <Volume2 size={17} /> {auctionAudio ? "Audio on" : "Enable audio"}
        </button>
      </nav>
      {view === "MISSIONS" ? (
        <div className="puzzle-participant-grid">
          <section className="puzzle-panel assign-panel">
            <span className="puzzle-kicker">01 / SELECT OPERATIVE</span>
            <h2>Who is playing next?</h2>
            <p>
              More attempts can earn more points. A player must complete two
              different tables before returning to the same one.
            </p>
            <div className="operative-grid">
              {team?.members.map((person) => (
                <button
                  key={person.id}
                  className={member === person.id ? "selected" : ""}
                  disabled={
                    !data?.open ||
                    active.some((item) => item.participant_id === person.id)
                  }
                  onClick={() => setMember(person.id)}
                >
                  <span>{person.name.slice(0, 1).toUpperCase()}</span>
                  <b>{person.name}</b>
                  <small>
                    {active.some((item) => item.participant_id === person.id)
                      ? "ON A MISSION"
                      : `${person.games_completed} PLAYED`}
                  </small>
                </button>
              ))}
            </div>
            <button
              className="puzzle-primary"
              disabled={!member || !data?.open || busy || active.length >= 2}
              onClick={() => void assign()}
            >
              {busy ? "Scanning stations…" : "Assign an available table"}{" "}
              <MapPin size={18} />
            </button>
            <small className="answer-note">
              Up to three team devices may stay logged in, but only two players
              can hold table assignments at the same time.
            </small>
            <div className="cooldown-rule">
              <LockKeyhole size={19} />
              <span>
                <b>Automatic fairness lock</b> Your team completes one different
                table—and the same player completes two—before a repeat.
              </span>
            </div>
          </section>
          <section className="puzzle-panel mission-panel">
            <span className="puzzle-kicker">02 / LIVE MISSIONS</span>
            <h2>Go to your stations.</h2>
            <p>
              When the player reaches the assigned table, press Send code. The
              three-digit code then appears on that table laptop. The question
              stays hidden until the station confirms the player.
            </p>
            {active.length ? (
              <div className="mission-list">
                {active.map((item) => (
                  <article key={item.id} className={item.status.toLowerCase()}>
                    <div className="mission-room">
                      <small>ROOM</small>
                      <strong>
                        {String(item.room_number).padStart(2, "0")}
                      </strong>
                    </div>
                    <div>
                      <span>
                        {item.status === "ACTIVE"
                          ? "PUZZLE RUNNING"
                          : "STATION RESERVED"}
                      </span>
                      <h3>
                        Table {item.table_number} · {item.participant_name}
                      </h3>
                      <p>{item.game_name}</p>
                      {item.status === "RESERVED" ? (
                        <div className="arrival-code">
                          <KeyRound size={18} />
                          <small>
                            {item.access_code ? "CODE SENT TO TABLE" : "PLAYER AT TABLE?"}
                          </small>
                          {item.access_code ? (
                            <b>{item.access_code}</b>
                          ) : (
                            <button
                              className="puzzle-primary"
                              disabled={busy}
                              onClick={() =>
                                void post(
                                  `/r3-live/participant/attempts/${item.id}/reveal-code`,
                                  {},
                                  `Code sent to Table ${item.table_number}.`,
                                )
                              }
                            >
                              Send 3-digit code
                            </button>
                          )}
                        </div>
                      ) : (
                        <div className="live-timer">
                          <Timer size={18} /> Time left{" "}
                          <Countdown
                            until={
                              item.started_at
                                ? new Date(
                                    new Date(item.started_at).getTime() + 75000,
                                  ).toISOString()
                                : null
                            }
                          />
                        </div>
                      )}
                    </div>
                    {item.status === "RESERVED" && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          void post(
                            `/r3-live/participant/attempts/${item.id}/cancel`,
                            {},
                            "Reservation cancelled.",
                          )
                        }
                      >
                        Cancel
                      </button>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="puzzle-empty">
                <MapPin />
                <h3>No live assignment.</h3>
                <p>
                  Select a teammate and the system will find an eligible free
                  station.
                </p>
              </div>
            )}
          </section>
        </div>
      ) : (
        <section className="puzzle-auction">
          <div className="puzzle-section-heading">
            <span className="puzzle-kicker">OPTIONAL / LIVE INTELLIGENCE</span>
            <h2>Bid while your teammates solve.</h2>
            <p>
              Winning clues can help in the legal round. Only the winning bid is
              charged.
            </p>
          </div>
          <div className="auction-grid">
            {data?.lots.map((lot) => (
              <article key={lot.id} className={lot.status.toLowerCase()}>
                <span>
                  LEVEL {lot.level} · TOKEN {lot.token_number}
                </span>
                <h3>{lot.title}</h3>
                <p>{lot.description}</p>
                {lot.clue_text && (
                  <div className="won-intel">
                    <Sparkles size={17} />
                    {lot.clue_text}
                  </div>
                )}
                <div className="auction-price">
                  <small>{lot.status}</small>
                  <b>{points(lot.highest_bid ?? lot.opening_bid)}</b>
                </div>
                {lot.status === "LIVE" && (
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      void post(
                        `/r3-live/participant/lots/${lot.id}/bid`,
                        { amount: Number(bid[lot.id]) },
                        "Bid accepted.",
                      );
                    }}
                  >
                    <input
                      type="number"
                      min={(lot.highest_bid ?? lot.opening_bid) + 1}
                      value={bid[lot.id] || ""}
                      onChange={(event) =>
                        setBid({ ...bid, [lot.id]: event.target.value })
                      }
                      placeholder="Your bid"
                    />
                    <button disabled={busy}>Bid</button>
                  </form>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
      <footer className="puzzle-footer">
        ASYMPTOTES · BMSIT <span>SERVER-TIMED / SERVER-SCORED</span>
      </footer>
    </Shell>
  );
}

export function Round3PuzzleStationPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<StationState | null>(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState<{
    correct: boolean;
    awarded: number;
  } | null>(null);
  const load = (quiet = false) =>
    request<StationState>("/r3-live/admin/table")
      .then(setData)
      .catch((problem) => {
        if (!quiet) setError(errorText(problem));
      });
  useEffect(() => {
    if (getSession()?.role !== "ADMIN") {
      navigate("/login", { replace: true });
      return;
    }
    void load();
    const timer = window.setInterval(() => void load(true), 1500);
    return () => window.clearInterval(timer);
  }, []);
  const attempt = data?.attempts?.[0];
  useEffect(() => {
    setAnswer("");
  }, [attempt?.id]);
  const deadline = useMemo(
    () =>
      attempt?.started_at
        ? new Date(new Date(attempt.started_at).getTime() + 75000).toISOString()
        : null,
    [attempt?.started_at],
  );
  async function unlock() {
    if (!attempt?.access_code) return;
    setBusy(true);
    setError("");
    try {
      await request(`/r3-live/admin/attempts/${attempt.id}/unlock`, "POST", {
        access_code: attempt.access_code,
      });
      await load();
    } catch (problem) {
      setError(errorText(problem));
    } finally {
      setBusy(false);
    }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!attempt) return;
    setBusy(true);
    setError("");
    try {
      const response = await request<{ correct: boolean; awarded: number }>(
        `/r3-live/admin/attempts/${attempt.id}/answer`,
        "POST",
        { answer },
      );
      setResult(response);
      setNotice(
        response.correct
          ? `Correct. ${points(response.awarded)} points added automatically.`
          : "Answer locked. No points awarded this time.",
      );
      setAnswer("");
      await load(true);
    } catch (problem) {
      setError(errorText(problem));
      await load(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell>
      <section className="station-header">
        <div>
          <span className="puzzle-kicker">
            <Radio size={14} /> SELF-SERVICE PUZZLE STATION
          </span>
          <h1>
            Table <em>{data?.number || "—"}</em>
          </h1>
          <p>
            Room {data?.room || "—"} ·{" "}
            {data?.game_name || "Awaiting configuration"}
          </p>
        </div>
        <div>
          <small>POINTS FOR A CORRECT LOCK</small>
          <strong>+{points(data?.max_points)}</strong>
        </div>
      </section>
      <Alert error={error} notice={notice} />
      {!data?.assigned ? (
        <section className="station-wait">
          <LockKeyhole />
          <h2>This laptop has no station.</h2>
          <p>Ask the super admin to assign this admin account to a table.</p>
        </section>
      ) : result ? (
        <section
          className={
            result.correct ? "station-result correct" : "station-result wrong"
          }
        >
          {result.correct ? <CheckCircle2 /> : <XCircle />}
          <span>{result.correct ? "ANSWER ACCEPTED" : "ANSWER LOCKED"}</span>
          <h2>
            {result.correct ? `+${points(result.awarded)} points` : "0 points"}
          </h2>
          <p>
            The result is already in the team ledger. This station will clear
            for the next assignment.
          </p>
          <button
            onClick={() => {
              setResult(null);
              setNotice("");
              void load();
            }}
          >
            Ready for next team
          </button>
        </section>
      ) : !attempt ? (
        <section className="station-wait">
          <div className="radar">
            <i />
            <i />
            <Radio />
          </div>
          <h2>Station ready.</h2>
          <p>
            The assignment engine is finding eligible teams automatically. Leave
            this screen open.
          </p>
          <button onClick={() => void load()}>
            <RefreshCw size={17} /> Refresh now
          </button>
        </section>
      ) : attempt.status === "RESERVED" ? (
        <section className="station-arrival">
          <div>
            <span className="puzzle-kicker">RESERVATION FOUND</span>
            <h2>{attempt.team_identifier}</h2>
            <p>
              {attempt.participant_name} · Table {attempt.table_number}
            </p>
          </div>
          {attempt.access_code ? (
            <div className="station-code-confirm">
              <small>CODE SENT BY PLAYER</small>
              <strong>{attempt.access_code}</strong>
              <button disabled={busy} onClick={() => void unlock()}>
                {busy ? "Starting…" : "Confirm player & start 75s"}{" "}
                <KeyRound size={18} />
              </button>
            </div>
          ) : (
            <div className="station-code-wait">
              <div className="radar"><i /><i /><Radio /></div>
              <h3>Waiting for the player to send the code.</h3>
              <p>The code stays hidden here until they press Send code on their team device.</p>
            </div>
          )}
          <small>The question is sealed and the timer has not started.</small>
        </section>
      ) : (
        <section className="station-puzzle">
          <header>
            <div>
              <span>{attempt.puzzle?.eyebrow}</span>
              <h2>{attempt.puzzle?.title}</h2>
            </div>
            <div>
              <small>TIME REMAINING</small>
              <Countdown
                until={deadline}
                onEnd={() => window.setTimeout(() => void load(), 600)}
              />
            </div>
          </header>
          <div className="puzzle-brief">
            <p>{attempt.puzzle?.story}</p>
            {attempt.puzzle && <PuzzleVisual puzzle={attempt.puzzle} />}
            <div className="puzzle-display">
              {attempt.puzzle?.display.map((line, index) => (
                <div key={index} tabIndex={0}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <b>{line}</b>
                </div>
              ))}
            </div>
            <h3>{attempt.puzzle?.prompt}</h3>
          </div>
          <form className="answer-lock" onSubmit={submit}>
            <div
              className="answer-options"
              role="radiogroup"
              aria-label={attempt.puzzle?.answer_label || "Choose one answer"}
            >
              {attempt.puzzle?.options.map((option, index) => (
                <button
                  key={option}
                  type="button"
                  role="radio"
                  aria-checked={answer === option}
                  className={answer === option ? "selected" : ""}
                  disabled={busy}
                  onClick={() => setAnswer(option)}
                >
                  <span>{String.fromCharCode(65 + index)}</span>
                  <b>{option}</b>
                </button>
              ))}
            </div>
            <button disabled={busy || !answer.trim()}>
              Lock selected option <LockKeyhole size={19} />
            </button>
          </form>
          <small className="answer-note">
            Tap one option, check it once, then lock it. One submission records
            the result and points automatically.
          </small>
        </section>
      )}
      <footer className="puzzle-footer">
        TABLE {data?.number || "—"} · AUTOMATED{" "}
        <span>NO DEALER INPUT REQUIRED</span>
      </footer>
    </Shell>
  );
}
