"""Design tokens and global CSS: a clean, warm light theme."""

import streamlit as st

from ui.mascot import MASCOT_CSS

CSS = """
<style>
:root {
  --bg: #F8FAFC;
  --surface: #FFFFFF;
  --surface-2: #F1F5F9;
  --line: #E2E8F0;
  --line-strong: #CBD5E1;
  --ink: #0F172A;
  --muted: #64748B;
  --primary: #10B981;
  --primary-strong: #059669;
  --primary-ink: #047857;
  --primary-soft: #ECFDF5;
  --cardio: #F97362;
  --cardio-ink: #C2410C;
  --cardio-soft: #FFF1EE;
  --strength: #3B82F6;
  --strength-ink: #1D4ED8;
  --strength-soft: #EFF6FF;
  --danger: #E11D48;
  --radius: 16px;
  --shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 6px 20px rgba(15, 23, 42, .05);
  --shadow-hover: 0 2px 4px rgba(15, 23, 42, .05), 0 12px 28px rgba(15, 23, 42, .08);
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
}

/* ---------- Canvas ---------- */
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(55rem 26rem at 100% -8%, rgba(16, 185, 129, .08), transparent 60%),
    radial-gradient(45rem 26rem at -8% 105%, rgba(249, 115, 98, .07), transparent 60%),
    var(--bg);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] {
  max-width: 1180px;
  padding: 2.25rem 1.5rem 4rem;
}
h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.02em; }
p, li, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stMarkdownContainer"] strong { color: var(--ink); }

/* ---------- Cards ---------- */
[class*="st-key-fp-card-"] {
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--line) !important;
  box-shadow: var(--shadow);
  transition: box-shadow .2s ease;
}
[class*="st-key-fp-card-"]:hover { box-shadow: var(--shadow-hover); }

/* ---------- Buttons ---------- */
.stButton > button, .stFormSubmitButton > button {
  min-height: 2.6rem;
  font-weight: 600;
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--ink);
  transition: transform .15s ease, border-color .15s ease, background .15s ease,
    box-shadow .15s ease;
}
.stButton button p, .stFormSubmitButton button p { color: inherit; }
.stButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: var(--primary);
  color: var(--primary-ink);
  background: var(--primary-soft);
  transform: translateY(-1px);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind*="rimary"] {
  background: var(--primary);
  border-color: var(--primary);
  color: #FFFFFF;
  box-shadow: 0 4px 14px rgba(16, 185, 129, .25);
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind*="rimary"]:hover {
  background: var(--primary-strong);
  border-color: var(--primary-strong);
  color: #FFFFFF;
  box-shadow: 0 8px 22px rgba(16, 185, 129, .3);
}
.st-key-fp-danger .stButton > button[kind="primary"] {
  background: var(--danger); border-color: var(--danger); color: #fff;
  box-shadow: 0 4px 14px rgba(225, 29, 72, .2);
}
.st-key-fp-danger .stButton > button[kind="primary"]:hover {
  background: #BE123C; border-color: #BE123C;
}

/* ---------- Top bar ---------- */
.st-key-fp-topbar {
  position: sticky; top: env(safe-area-inset-top, 0px); z-index: 50;
  margin: -1rem 0 1.75rem; padding: .6rem 0;
  background: rgba(248, 250, 252, .86);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--line);
}
.st-key-fp-topbar .stButton > button {
  min-height: 2.25rem; border-color: transparent; background: transparent;
  color: var(--muted); font-weight: 500; box-shadow: none;
}
.st-key-fp-topbar .stButton > button:hover {
  color: var(--ink); background: var(--surface-2); border-color: transparent;
}
.st-key-fp-topbar .stButton > button[kind="primary"] {
  background: var(--primary-soft); color: var(--primary-ink); font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(16, 185, 129, .25);
}
.st-key-fp-topbar .stButton > button[kind="primary"]:hover { transform: none; }

.fp-brand { display: flex; align-items: center; gap: .55rem; }
.fp-brand-name { color: var(--ink); font: 700 1rem var(--display); letter-spacing: -.01em; }
.fp-avatar-row { display: flex; align-items: center; justify-content: flex-end; gap: .55rem; }
.fp-avatar {
  width: 2rem; height: 2rem; border-radius: 50%; display: grid; place-items: center;
  background: var(--primary-soft); border: 1px solid rgba(16, 185, 129, .3);
  color: var(--primary-ink); font-size: .75rem; font-weight: 700;
}
.fp-account-name { color: var(--muted); font-size: .82rem; }

/* ---------- Page header ---------- */
.fp-eyebrow {
  color: var(--primary-ink); font-size: .72rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
}
.fp-page-title {
  margin: .35rem 0 .35rem; color: var(--ink);
  font: 700 clamp(1.7rem, 3.2vw, 2.4rem)/1.1 var(--display); letter-spacing: -.03em;
}
.fp-page-subtitle { max-width: 44rem; margin: 0 0 1.5rem; color: var(--muted); line-height: 1.6; }
.fp-hero {
  display: flex; align-items: center; justify-content: space-between; gap: 1.5rem;
  padding: 1.6rem 1.75rem; margin-bottom: 1.25rem;
  background:
    radial-gradient(30rem 14rem at 100% 0%, rgba(16, 185, 129, .10), transparent 70%),
    var(--surface);
  border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow);
}
.fp-hero .fp-page-subtitle { margin-bottom: 0; }
.fp-accent { color: var(--primary); }

/* ---------- Progress ring ---------- */
.fp-ring { position: relative; flex: 0 0 7.5rem; width: 7.5rem; height: 7.5rem; }
.fp-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.fp-ring-track { stroke: var(--surface-2); }
.fp-ring-value { stroke: var(--primary); transition: stroke-dashoffset .6s ease; }
.fp-ring-label {
  position: absolute; inset: 0; display: grid; place-content: center; text-align: center;
}
.fp-ring-number { color: var(--ink); font: 700 1.6rem/1 var(--display); }
.fp-ring-caption { color: var(--muted); font-size: .7rem; margin-top: .25rem; }

/* ---------- Stat tiles ---------- */
.fp-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr)); gap: .85rem; margin-bottom: 1.75rem; }
.fp-stat {
  padding: 1rem 1.1rem; background: var(--surface);
  border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow);
}
.fp-stat-label { color: var(--muted); font-size: .76rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }
.fp-stat-value {
  margin-top: .35rem; color: var(--ink);
  font: 700 1.85rem/1.1 var(--display); font-variant-numeric: tabular-nums;
}
.fp-stat-value small { color: var(--muted); font: 500 .9rem "Inter", sans-serif; }
.fp-stat-sub { margin-top: .2rem; color: var(--muted); font-size: .78rem; }

/* ---------- Section heading ---------- */
.fp-section { margin: .35rem 0 .75rem; color: var(--ink); font: 600 1.15rem var(--display); }

/* ---------- Icons: emerald by default, coral for cardio, blue for strength ---------- */
.fp-workout { display: flex; align-items: center; gap: 1rem; min-width: 0; }
.fp-icon {
  flex: 0 0 3rem; width: 3rem; height: 3rem; display: grid; place-items: center;
  border-radius: 12px; background: var(--primary-soft); color: var(--primary-ink);
}
.fp-icon svg { width: 1.45rem; height: 1.45rem; }
.fp-icon.is-cardio { background: var(--cardio-soft); color: var(--cardio-ink); }
.fp-icon.is-strength { background: var(--strength-soft); color: var(--strength-ink); }

/* ---------- Workout card ---------- */
.fp-workout-title { color: var(--ink); font: 600 1.05rem var(--display); overflow-wrap: anywhere; }
.fp-meta { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .35rem; }
.fp-chip {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .18rem .6rem; border-radius: 999px;
  background: var(--surface-2); border: 1px solid var(--line);
  color: #475569; font-size: .74rem; font-weight: 500;
}
.fp-chip.is-live { color: var(--primary-ink); border-color: rgba(16, 185, 129, .35); background: var(--primary-soft); }
.fp-chip.is-live::before {
  content: ""; width: .45rem; height: .45rem; border-radius: 50%; background: var(--primary);
  animation: fp-pulse 1.6s ease-in-out infinite;
}
@keyframes fp-pulse { 50% { opacity: .35; } }

.fp-segments { display: flex; gap: .3rem; margin: .2rem 0 .45rem; }
.fp-segment { flex: 1; height: .45rem; border-radius: 99px; background: var(--surface-2); }
.fp-segment.is-done { background: var(--primary); }
.fp-progress-label { display: flex; justify-content: space-between; color: var(--muted); font-size: .76rem; }

.fp-bar { height: .5rem; overflow: hidden; border-radius: 99px; background: var(--surface-2); }
.fp-bar-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--strength), var(--primary)); transition: width .5s ease; }

/* ---------- Activity timeline ---------- */
.fp-timeline { position: relative; margin: .25rem 0 0 .35rem; padding-left: 1.35rem; border-left: 2px solid var(--line); }
.fp-event { position: relative; padding: 0 0 1.15rem; }
.fp-event::before {
  content: ""; position: absolute; left: -1.82rem; top: .3rem;
  width: .75rem; height: .75rem; border-radius: 50%;
  background: var(--surface); border: 3px solid var(--primary);
}
.fp-event-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem; }
.fp-event-title { color: var(--ink); font-weight: 600; }
.fp-event-date { color: var(--muted); font-size: .76rem; }
.fp-event .fp-meta { margin-top: .4rem; }

/* ---------- Exercise list (plan + preview) ---------- */
.fp-exercise {
  display: flex; align-items: flex-start; gap: .9rem;
  padding: .85rem 0; border-bottom: 1px solid var(--line);
}
.fp-exercise:last-child { border-bottom: 0; }
.fp-index {
  flex: 0 0 1.9rem; height: 1.9rem; display: grid; place-items: center; border-radius: 8px;
  background: var(--primary-soft); color: var(--primary-ink); font: 700 .75rem var(--display);
}
.fp-exercise-name { color: var(--ink); font-weight: 600; }
.fp-exercise-note { color: var(--muted); font-size: .8rem; margin-top: .2rem; }
.fp-exercise-spec { margin-left: auto; text-align: right; color: var(--ink); font: 600 .9rem var(--display); white-space: nowrap; }
.fp-exercise-spec small { display: block; color: var(--muted); font: 500 .74rem "Inter", sans-serif; }

.fp-coach {
  display: flex; gap: .75rem; padding: .9rem 1rem; margin: .5rem 0 1rem;
  border-radius: 12px; background: var(--cardio-soft); border: 1px solid #FED7CF;
  color: var(--ink); font-size: .9rem; line-height: 1.55;
}
.fp-coach b { color: var(--cardio-ink); }

/* ---------- Live session ---------- */
.fp-sets { display: flex; flex-wrap: wrap; gap: .5rem; margin: .4rem 0 1rem; }
.fp-set {
  min-width: 4.6rem; padding: .55rem .7rem; border-radius: 12px; text-align: center;
  background: var(--surface-2); border: 1px solid var(--line);
}
.fp-set-label { color: var(--muted); font-size: .68rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
.fp-set-value { color: var(--ink); font: 600 .95rem var(--display); margin-top: .15rem; }
.fp-set.is-done { background: var(--primary-soft); border-color: rgba(16, 185, 129, .4); }
.fp-set.is-done .fp-set-value { color: var(--primary-ink); }
.fp-set.is-active { background: var(--surface); border-color: var(--strength); box-shadow: 0 0 0 3px var(--strength-soft); }

.fp-timer { display: flex; align-items: center; gap: 1.25rem; padding: 1rem 0; }
.fp-timer .fp-ring { flex-basis: 6.5rem; width: 6.5rem; height: 6.5rem; }
.fp-timer .fp-ring-value { stroke: var(--strength); }
.fp-timer-title { color: var(--ink); font: 600 1.1rem var(--display); }

/* ---------- Auth ---------- */
.fp-auth-title {
  margin: 1.5rem 0 1rem; color: var(--ink);
  font: 700 clamp(2.2rem, 5vw, 3.6rem)/1.02 var(--display); letter-spacing: -.04em;
}
.fp-features { list-style: none; padding: 0; margin: 1.5rem 0; display: grid; gap: .9rem; }
.fp-features li { display: flex; gap: .75rem; align-items: flex-start; color: var(--muted); }
.fp-features .fp-icon { flex-basis: 2.3rem; width: 2.3rem; height: 2.3rem; border-radius: 10px; }
.fp-features .fp-icon svg { width: 1.1rem; height: 1.1rem; }
.fp-features strong { display: block; color: var(--ink); font-weight: 600; }

/* ---------- Inputs & misc ---------- */
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: var(--primary-ink); }
[data-testid="stAlert"] { border-radius: 12px; }
.fp-empty { padding: 1.75rem 1rem; text-align: center; }
.fp-empty .fp-icon { margin: 0 auto .75rem; }
.fp-empty-title { color: var(--ink); font: 600 1.1rem var(--display); }
.fp-empty p { margin: .35rem auto 0; max-width: 28rem; }

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { padding: 1.5rem 1rem 3rem; }
  .fp-hero { flex-direction: column; align-items: flex-start; padding: 1.25rem; }
  .fp-account-name { display: none; }
  .st-key-fp-topbar { position: static; }
  .st-key-fp-topbar [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .3rem; }
  .st-key-fp-topbar [data-testid="stColumn"] {
    flex: 1 1 30% !important; width: auto !important; min-width: 0 !important;
  }
  .st-key-fp-topbar [data-testid="stColumn"]:first-child {
    flex-basis: 100% !important; margin-bottom: .5rem;
  }
  .st-key-fp-topbar [data-testid="stColumn"]:nth-last-child(2) { display: none; }
  .fp-exercise-spec { font-size: .82rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition-duration: .01ms !important; }
}
</style>
"""


def inject_theme() -> None:
    st.html(CSS + MASCOT_CSS)
