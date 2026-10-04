import React from "react";
import { api, tokenStore } from "./api.js";

/* ---------------------------------- brand ---------------------------------- */

function ShieldMark({ size = 40 }) {
  // Original mark: a shield outline holding soundwave bars.
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <path
        d="M24 3 6 10v13c0 11.5 7.4 19.4 18 22 10.6-2.6 18-10.5 18-22V10L24 3Z"
        stroke="#FFB020"
        strokeWidth="3"
        fill="rgba(255,176,32,0.08)"
      />
      {[14, 19, 24, 29, 34].map((x, i) => {
        const h = [10, 18, 24, 15, 9][i];
        return (
          <rect key={x} x={x - 1.6} y={24 - h / 2} width="3.2" height={h} rx="1.6" fill="#35E0B0" />
        );
      })}
    </svg>
  );
}

function BandPill({ band }) {
  const labels = {
    likely_match: "Likely match",
    review: "Needs review",
    no_match: "No match",
  };
  return <span className={`pill pill-${band}`}>{labels[band] || band}</span>;
}

function ScoreBar({ score }) {
  const pct = Math.max(0, Math.min(100, score * 100));
  const cls = score >= 0.7 ? "bar-high" : score >= 0.55 ? "bar-mid" : "bar-low";
  return (
    <div className="scorebar">
      <div className={`scorebar-fill ${cls}`} style={{ width: `${pct}%` }} />
      <span className="scorebar-num">{score.toFixed(3)}</span>
    </div>
  );
}

function Waveform({ file }) {
  const ref = React.useRef(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    if (!file) return;
    setFailed(false);
    let cancelled = false;
    let ctx = null;
    (async () => {
      try {
        const AC = window.AudioContext || window.webkitAudioContext;
        ctx = new AC();
        const buf = await file.arrayBuffer();
        const audio = await ctx.decodeAudioData(buf);
        if (cancelled) return;
        const data = audio.getChannelData(0);
        const canvas = ref.current;
        if (!canvas) return;
        const g = canvas.getContext("2d");
        const W = canvas.width;
        const H = canvas.height;
        g.clearRect(0, 0, W, H);
        const bars = 120;
        const step = Math.floor(data.length / bars);
        g.fillStyle = "#35E0B0";
        for (let i = 0; i < bars; i++) {
          let peak = 0;
          const start = i * step;
          for (let j = start; j < start + step; j += 8) {
            const v = Math.abs(data[j] || 0);
            if (v > peak) peak = v;
          }
          const h = Math.max(2, peak * H * 0.92);
          const x = (i / bars) * W;
          g.fillRect(x, (H - h) / 2, W / bars - 1.5, h);
        }
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (ctx) ctx.close().catch(() => {});
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [file]);

  if (!file || failed) return null;
  return <canvas ref={ref} className="waveform" width={620} height={72} />;
}

function Dropzone({ file, setFile, accept, hint }) {
  const inputRef = React.useRef(null);
  const [drag, setDrag] = React.useState(false);
  return (
    <div
      className={`dropzone${drag ? " drag" : ""}${file ? " has-file" : ""}`}
      onClick={() => inputRef.current && inputRef.current.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files && e.dataTransfer.files[0];
        if (f) setFile(f);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => setFile(e.target.files[0] || null)}
      />
      {file ? (
        <div className="dz-file">
          <div className="dz-name">{file.name}</div>
          <div className="dz-size">{(file.size / 1048576).toFixed(1)} MB</div>
          <Waveform file={file} />
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              setFile(null);
            }}
          >
            Remove
          </button>
        </div>
      ) : (
        <div className="dz-empty">
          <div className="dz-icon">♪</div>
          <div>
            <strong>Drop an audio file here</strong> or click to browse
          </div>
          <div className="muted small">{hint}</div>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------- auth ----------------------------------- */

function AuthView({ onAuthed }) {
  const [mode, setMode] = React.useState("login");
  const [email, setEmail] = React.useState("");
  const [artistName, setArtistName] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res =
        mode === "login"
          ? await api.login(email.trim(), password)
          : await api.signup(email.trim(), artistName.trim(), password);
      tokenStore.set(res.access_token);
      const user = await api.me();
      onAuthed(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-brand">
        <ShieldMark size={64} />
        <h1>Voice-Clone Shield</h1>
        <p className="tagline">Your voice is your identity. We keep it yours.</p>
        <ul className="auth-points">
          <li>Enroll your voiceprint from a clean vocal recording</li>
          <li>Check any suspect clip for an AI clone of your voice</li>
          <li>Download an evidence pack for takedown filings</li>
        </ul>
        <p className="muted small pilot-note">
          India-first pilot · Built for indie artists · Early access free during the pilot
        </p>
      </div>
      <form className="auth-card card" onSubmit={submit}>
        <div className="auth-tabs">
          {(["login", "signup"]).map((m) => (
            <button
              key={m}
              type="button"
              className={`tab${mode === m ? " active" : ""}`}
              onClick={() => {
                setMode(m);
                setError("");
              }}
            >
              {m === "login" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>
        {mode === "signup" && (
          <label>
            Artist / stage name
            <input
              required
              value={artistName}
              onChange={(e) => setArtistName(e.target.value)}
              placeholder="e.g. Ananya Rao"
            />
          </label>
        )}
        <label>
          Password{mode === "signup" ? " (min 8 characters)" : ""}
          <input
            type="password"
            required
            minLength={mode === "signup" ? 8 : 1}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="btn btn-primary btn-block" disabled={busy} type="submit">
          {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
    </div>
  );
}

/* --------------------------------- views ----------------------------------- */

function DashboardView({ refreshKey, go }) {
  const [stats, setStats] = React.useState({ vps: 0, checks: 0, flagged: 0 });
  const [recent, setRecent] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    (async () => {
      try {
        const [vps, checks] = await Promise.all([api.listVoiceprints(), api.listChecks()]);
        setStats({
          vps: vps.length,
          checks: checks.length,
          flagged: checks.filter((c) => c.verdict === "likely_match").length,
        });
        setRecent(checks.slice(0, 5));
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshKey]);

  if (loading) return <div className="muted">Loading…</div>;

  return (
    <div>
      <div className="stat-row">
        <div className="card stat">
          <div className="stat-num">{stats.vps}</div>
          <div className="stat-label">Voiceprints enrolled</div>
        </div>
        <div className="card stat">
          <div className="stat-num">{stats.checks}</div>
          <div className="stat-label">Clips checked</div>
        </div>
        <div className="card stat stat-alert">
          <div className="stat-num">{stats.flagged}</div>
          <div className="stat-label">Likely matches flagged</div>
        </div>
      </div>

      {stats.vps === 0 && (
        <div className="card cta">
          <h3>Protect your voice in 3 minutes</h3>
          <p className="muted">
            Upload 2–3 minutes of clean vocals. We build your voiceprint — a mathematical
            fingerprint of how you sound — and watch for clones.
          </p>
          <button className="btn btn-primary" onClick={() => go("enroll")}>
            Enroll my voice
          </button>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <h3>Recent checks</h3>
          <button className="btn btn-ghost btn-sm" onClick={() => go("history")}>
            View all
          </button>
        </div>
        {recent.length === 0 ? (
          <p className="muted">
            Nothing checked yet. Heard a suspicious “new song” in your voice on Reels or
            YouTube? <button className="link" onClick={() => go("check")}>Check a clip</button>.
          </p>
        ) : (
          <ul className="check-list">
            {recent.map((c) => (
              <li key={c.id}>
                <span className="clip-name">{c.filename}</span>
                <BandPill band={c.verdict} />
                <span className="muted small">{c.top_score.toFixed(3)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card how">
        <h3>How a check works</h3>
        <ol>
          <li>Your clip is converted to mono 16 kHz and voice activity is detected.</li>
          <li>An ECAPA-TDNN speaker embedding captures <em>who</em> is singing — not the song.</li>
          <li>It is compared against your enrolled voiceprints with cosine similarity.</li>
          <li>Scores above the match threshold are flagged; you confirm or reject each one.</li>
        </ol>
        <p className="muted small">
          Fingerprinting matches recordings. Voiceprints match voices — so a clone singing a
          brand-new song still gets caught.
        </p>
      </div>
    </div>
  );
}

function EnrollView({ onDone }) {
  const [label, setLabel] = React.useState("");
  const [file, setFile] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [done, setDone] = React.useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!file || !label.trim()) return;
    setError("");
    setBusy(true);
    try {
      const vp = await api.enrollVoiceprint(label.trim(), file);
      setDone(vp);
      setFile(null);
      setLabel("");
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="narrow">
      <div className="card">
        <h3>Enroll your voiceprint</h3>
        <p className="muted">
          Upload <strong>2–3 minutes of clean vocals</strong> — an acapella, a voice note, a
          studio dry vocal. Avoid heavy background music for the best voiceprint.
        </p>
        <form onSubmit={submit}>
          <label>
            Label for this voiceprint
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. My singing voice 2026"
              required
              maxLength={255}
            />
          </label>
          <Dropzone
            file={file}
            setFile={setFile}
            accept="audio/*"
            hint="WAV, MP3, FLAC, OGG or M4A · up to 50 MB"
          />
          {error && <div className="error">{error}</div>}
          <button className="btn btn-primary btn-block" disabled={busy || !file} type="submit">
            {busy ? "Building voiceprint… (first run downloads the model)" : "Build my voiceprint"}
          </button>
        </form>
        {done && (
          <div className="success-box">
            Voiceprint <strong>{done.label}</strong> enrolled — {done.duration_sec.toFixed(0)}s
            of audio, {(done.voiced_ratio * 100).toFixed(0)}% voiced.
          </div>
        )}
      </div>
      <VoiceprintList refreshSignal={done} />
    </div>
  );
}

function VoiceprintList({ refreshSignal }) {
  const [vps, setVps] = React.useState([]);
  React.useEffect(() => {
    api.listVoiceprints().then(setVps).catch(() => {});
  }, [refreshSignal]);

  async function remove(id) {
    if (!window.confirm("Delete this voiceprint?")) return;
    await api.deleteVoiceprint(id);
    setVps((xs) => xs.filter((v) => v.id !== id));
  }

  return (
    <div className="card">
      <h3>Enrolled voiceprints</h3>
      {vps.length === 0 ? (
        <p className="muted">None yet.</p>
      ) : (
        <ul className="vp-list">
          {vps.map((v) => (
            <li key={v.id}>
              <div>
                <div className="clip-name">{v.label}</div>
                <div className="muted small">
                  {v.duration_sec.toFixed(0)}s · {(v.voiced_ratio * 100).toFixed(0)}% voiced ·{" "}
                  {new Date(v.created_at).toLocaleDateString()}
                </div>
              </div>
              <button className="btn btn-ghost btn-sm btn-danger" onClick={() => remove(v.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CheckView({ onDone }) {
  const [file, setFile] = React.useState(null);
  const [vps, setVps] = React.useState([]);
  const [vpId, setVpId] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [result, setResult] = React.useState(null);

  React.useEffect(() => {
    api.listVoiceprints().then(setVps).catch(() => {});
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setBusy(true);
    setResult(null);
    try {
      const r = await api.runCheck(file, vpId || null);
      setResult(r);
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="narrow">
      <div className="card">
        <h3>Check a suspect clip</h3>
        <p className="muted">
          Upload any clip — a “new song” in your voice, a viral reel audio, a voice note.
          We compare <em>who is singing</em> against your voiceprints.
        </p>
        <form onSubmit={submit}>
          <Dropzone
            file={file}
            setFile={setFile}
            accept="audio/*"
            hint="WAV, MP3, FLAC, OGG or M4A · up to 50 MB"
          />
          <label>
            Compare against
            <select value={vpId} onChange={(e) => setVpId(e.target.value)}>
              <option value="">All my voiceprints</option>
              {vps.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
          {error && <div className="error">{error}</div>}
          <button className="btn btn-primary btn-block" disabled={busy || !file} type="submit">
            {busy ? "Analyzing voice…" : "Check this clip"}
          </button>
        </form>
      </div>

      {result && (
        <div className="card">
          <div className="card-head">
            <h3>Result</h3>
            <BandPill band={result.verdict} />
          </div>
          <p className="muted small">
            {result.filename} · {result.duration_sec.toFixed(1)}s ·{" "}
            {(result.voiced_ratio * 100).toFixed(0)}% voiced
          </p>
          <ul className="result-list">
            {result.results.map((r) => (
              <li key={r.voiceprint_id}>
                <div className="result-row">
                  <span className="clip-name">{r.label}</span>
                  <BandPill band={r.band} />
                </div>
                <ScoreBar score={r.score} />
              </li>
            ))}
          </ul>
          <div className="row gap">
            <button className="btn btn-secondary" onClick={() => api.downloadEvidence(result.id)}>
              Download evidence PDF
            </button>
          </div>
          <FeedbackBox check={result} onSaved={(c) => setResult(c)} />
        </div>
      )}
    </div>
  );
}

function FeedbackBox({ check, onSaved }) {
  const [note, setNote] = React.useState(check.feedback_note || "");
  const [saved, setSaved] = React.useState(!!check.feedback);

  async function send(verdict) {
    const c = await api.sendFeedback(check.id, verdict, note.trim() || null);
    setSaved(true);
    if (onSaved) onSaved(c);
  }

  return (
    <div className="feedback">
      <div className="muted small">
        {saved ? "Your feedback is recorded — it tunes future checks." : "Was this verdict right?"}
      </div>
      <textarea
        rows={2}
        placeholder="Optional note (where did you find this clip? link, context…)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="row gap">
        <button
          className={`btn btn-sm ${check.feedback === "confirmed" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => send("confirmed")}
        >
          ✓ Yes, that's my voice
        </button>
        <button
          className={`btn btn-sm ${check.feedback === "rejected" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => send("rejected")}
        >
          ✗ Not my voice
        </button>
      </div>
    </div>
  );
}

function HistoryView() {
  const [checks, setChecks] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [openId, setOpenId] = React.useState(null);

  React.useEffect(() => {
    api
      .listChecks()
      .then(setChecks)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="muted">Loading…</div>;

  return (
    <div className="card">
      <h3>Check history</h3>
      {checks.length === 0 ? (
        <p className="muted">No checks yet.</p>
      ) : (
        <ul className="history-list">
          {checks.map((c) => (
            <li key={c.id} className="history-item">
              <div
                className="history-head"
                onClick={() => setOpenId(openId === c.id ? null : c.id)}
              >
                <div>
                  <div className="clip-name">{c.filename}</div>
                  <div className="muted small">
                    {new Date(c.created_at).toLocaleString()} · top score {c.top_score.toFixed(3)}
                    {c.feedback && ` · you said: ${c.feedback}`}
                  </div>
                </div>
                <BandPill band={c.verdict} />
              </div>
              {openId === c.id && (
                <div className="history-detail">
                  <ul className="result-list">
                    {c.results.map((r) => (
                      <li key={r.voiceprint_id}>
                        <div className="result-row">
                          <span className="clip-name">{r.label}</span>
                          <BandPill band={r.band} />
                        </div>
                        <ScoreBar score={r.score} />
                      </li>
                    ))}
                  </ul>
                  <div className="row gap">
                    <button className="btn btn-secondary btn-sm" onClick={() => api.downloadEvidence(c.id)}>
                      Evidence PDF
                    </button>
                  </div>
                  <FeedbackBox
                    check={c}
                    onSaved={(upd) =>
                      setChecks((xs) => xs.map((x) => (x.id === upd.id ? upd : x)))
                    }
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---------------------------------- shell ---------------------------------- */

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "▦" },
  { id: "enroll", label: "Enroll voice", icon: "◉" },
  { id: "check", label: "Check a clip", icon: "◎" },
  { id: "history", label: "History", icon: "≣" },
];

function Shell({ user, onLogout }) {
  const [view, setView] = React.useState("dashboard");
  const [refreshKey, setRefreshKey] = React.useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldMark size={36} />
          <div>
            <div className="brand-name">Voice-Clone Shield</div>
            <div className="brand-sub muted small">pilot</div>
          </div>
        </div>
        <nav>
          {NAV.map((n) => (
            <button
              key={n.id}
              className={`nav-item${view === n.id ? " active" : ""}`}
              onClick={() => setView(n.id)}
            >
              <span className="nav-icon">{n.icon}</span> {n.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="artist-chip">
            <div className="avatar">{(user.artist_name || "?")[0].toUpperCase()}</div>
            <div>
              <div className="clip-name">{user.artist_name}</div>
              <div className="muted small">{user.email}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm btn-block" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="page-head">
          <h2>{NAV.find((n) => n.id === view).label}</h2>
        </header>
        {view === "dashboard" && <DashboardView refreshKey={refreshKey} go={setView} />}
        {view === "enroll" && <EnrollView onDone={bump} />}
        {view === "check" && <CheckView onDone={bump} />}
        {view === "history" && <HistoryView key={refreshKey} />}
      </main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = React.useState(null);
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.set(null))
      .finally(() => setReady(true));
  }, []);

  if (!ready) return <div className="boot">Loading…</div>;
  if (!user) return <AuthView onAuthed={setUser} />;
  return (
    <Shell
      user={user}
      onLogout={() => {
        tokenStore.set(null);
        setUser(null);
      }}
    />
  );
}
