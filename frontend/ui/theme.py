"""Design tokens and global CSS: a dark navy theme with emerald and blue glows."""

import streamlit as st

from ui.mascot import CELEBRATION_CSS, MASCOT_CSS

CSS = """
<style>
:root {
  --bg: #0B1220;
  --bg-2: #111C30;
  --surface: rgba(17, 27, 46, .72);
  --surface-solid: #111B2E;
  --surface-2: rgba(255, 255, 255, .05);
  --surface-3: rgba(255, 255, 255, .08);
  --line: rgba(255, 255, 255, .08);
  --line-soft: rgba(255, 255, 255, .07);
  --line-strong: rgba(255, 255, 255, .14);
  --ink: #F1F5F9;
  --ink-dark: #0B1220;
  --muted: #94A3B8;
  --primary: #10B981;
  --primary-strong: #059669;
  --primary-ink: #6EE7B7;
  --primary-soft: rgba(16, 185, 129, .12);
  --teal: #14B8A6;
  --gradient: linear-gradient(135deg, #10B981 0%, #14B8A6 100%);
  --gradient-text: linear-gradient(90deg, #34D399, #5EEAD4);
  --cardio: #F97362;
  --cardio-ink: #FDA192;
  --cardio-soft: rgba(249, 115, 98, .12);
  --strength: #3B82F6;
  --strength-ink: #93C5FD;
  --strength-soft: rgba(59, 130, 246, .14);
  --amber: #F59E0B;
  --amber-ink: #FCD34D;
  --amber-soft: rgba(245, 158, 11, .13);
  --violet: #8B5CF6;
  --violet-ink: #C4B5FD;
  --violet-soft: rgba(139, 92, 246, .15);
  --danger: #E11D48;
  --radius: 20px;
  --radius-sm: 12px;
  --highlight: inset 0 1px 0 rgba(255, 255, 255, .05);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, .25);
  --shadow: var(--highlight), 0 1px 2px rgba(0, 0, 0, .2), 0 18px 40px -20px rgba(0, 0, 0, .6);
  --shadow-hover: var(--highlight), 0 2px 4px rgba(0, 0, 0, .25),
    0 28px 56px -20px rgba(0, 0, 0, .7), 0 0 0 1px rgba(16, 185, 129, .18);
  --shadow-lg: 0 30px 60px -20px rgba(0, 0, 0, .7), 0 12px 24px -12px rgba(0, 0, 0, .5);
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
  --ease: cubic-bezier(.2, .8, .2, 1);
}

/* ---------- Canvas: navy with glows and a fading grid, like the hero ---------- */
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(60rem 34rem at 100% -10%, rgba(16, 185, 129, .22), transparent 60%),
    radial-gradient(50rem 30rem at -10% 45%, rgba(59, 130, 246, .16), transparent 60%),
    radial-gradient(46rem 28rem at 60% 120%, rgba(20, 184, 166, .12), transparent 60%),
    linear-gradient(180deg, #0B1220 0%, #0D1628 50%, #0B1220 100%);
  background-attachment: fixed;
}
[data-testid="stAppViewContainer"]::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, .035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, .035) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(ellipse 80% 60% at 70% 0%, #000 20%, transparent 75%);
  mask-image: radial-gradient(ellipse 80% 60% at 70% 0%, #000 20%, transparent 75%);
}
[data-testid="stMain"] { position: relative; z-index: 1; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] {
  max-width: 1200px;
  padding: 1.5rem 1.5rem 5rem;
}
h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.025em; }
p, li, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stMarkdownContainer"] strong { color: var(--ink); }
::selection { background: rgba(16, 185, 129, .35); color: #fff; }

/* ---------- Cards: dark glass ---------- */
[class*="st-key-fp-card-"] {
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(22, 34, 56, .78), rgba(15, 24, 42, .78));
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--line) !important;
  box-shadow: var(--shadow);
  transition: box-shadow .3s var(--ease), transform .3s var(--ease), border-color .3s var(--ease);
}
[class*="st-key-fp-card-"]:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
  border-color: rgba(16, 185, 129, .25) !important;
}
[class*="st-key-fp-card-"] h3 { font-family: var(--display); font-weight: 600; }
/* Streamlit pulls text blocks up with a -1rem bottom margin (to hide a
   paragraph's margin). Our HTML blocks have no such margin, so inside cards and
   dialogs that made them overflow their row and sit low; undo it there. */
[class*="st-key-fp-card-"] [data-testid="stMarkdownContainer"]:has(> [class^="fp-"]),
[data-testid="stDialog"] [data-testid="stMarkdownContainer"]:has(> [class^="fp-"]) {
  margin-bottom: 0;
}

/* ---------- Buttons ---------- */
.stButton > button, .stFormSubmitButton > button {
  min-height: 2.65rem;
  padding: 0 1.15rem;
  font-weight: 600;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: rgba(255, 255, 255, .04);
  color: var(--ink);
  box-shadow: var(--highlight);
  transition: transform .2s var(--ease), border-color .2s ease, background .2s ease,
    box-shadow .2s ease, color .2s ease;
}
.stButton button p, .stFormSubmitButton button p { color: inherit; font-weight: inherit; }
.stButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: rgba(52, 211, 153, .5);
  color: var(--primary-ink);
  background: var(--primary-soft);
  transform: translateY(-1px);
  box-shadow: 0 8px 22px -8px rgba(16, 185, 129, .45);
}
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {
  outline: none; box-shadow: 0 0 0 4px rgba(16, 185, 129, .3);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind*="rimary"] {
  background: var(--gradient);
  border-color: transparent;
  color: #FFFFFF;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .25), 0 10px 26px -8px rgba(16, 185, 129, .65);
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind*="rimary"]:hover {
  background: linear-gradient(135deg, #34D399 0%, #2DD4BF 100%);
  border-color: transparent;
  color: var(--ink-dark);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .3), 0 14px 32px -8px rgba(16, 185, 129, .75);
}
.st-key-fp-danger .stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #F43F5E, #E11D48); color: #fff;
  box-shadow: 0 10px 24px -8px rgba(225, 29, 72, .6);
}
.st-key-fp-danger .stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #FB7185, #F43F5E); color: #fff;
}

/* ---------- Back links + plan header ---------- */
[class*="st-key-fp-back-"] { margin: -.75rem 0 -.35rem; }
[class*="st-key-fp-back-"] .stButton > button {
  min-height: 2rem; padding: 0 .75rem 0 .5rem; font-size: .84rem; font-weight: 500;
  color: var(--muted); background: transparent; border-color: transparent; box-shadow: none;
}
[class*="st-key-fp-back-"] .stButton > button:hover {
  color: var(--ink); background: rgba(255, 255, 255, .06); border-color: transparent;
  box-shadow: none; transform: none;
}
.st-key-fp-plan-hero {
  position: relative; overflow: hidden; isolation: isolate;
  padding: 1.35rem 1.6rem; margin-bottom: .75rem; border-radius: 24px;
  background:
    radial-gradient(26rem 14rem at 95% 0%, rgba(16, 185, 129, .3), transparent 65%),
    radial-gradient(22rem 12rem at 0% 120%, rgba(59, 130, 246, .22), transparent 65%),
    linear-gradient(135deg, #0E1729 0%, #13203A 100%);
  border: 1px solid rgba(52, 211, 153, .18);
  box-shadow: var(--highlight), var(--shadow-lg);
}
.st-key-fp-plan-hero [data-testid="stMarkdownContainer"]:has(> [class^="fp-"]) { margin-bottom: 0; }
.fp-plan-id { display: flex; align-items: center; gap: 1.25rem; min-width: 0; }
.fp-plan-id > div:last-child { min-width: 0; }
.fp-plan-id .fp-type-art { flex: 0 0 5.5rem; width: 5.5rem; height: 5.5rem; margin: 0; }
.fp-plan-id .fp-type-art svg { width: 4rem; height: 4rem; }
.fp-plan-id .fp-icon { flex-basis: 4rem; width: 4rem; height: 4rem; border-radius: 18px; }
.fp-plan-id .fp-page-title {
  margin: .3rem 0 .15rem; font-size: clamp(1.8rem, 3.4vw, 2.5rem); overflow-wrap: anywhere;
}
.st-key-fp-plan-hero .fp-segments { margin-top: .55rem; }
.st-key-fp-plan-hero .fp-meta { margin: .5rem 0 .2rem; }
.fp-plan-heading { margin: .25rem 0 1.1rem; }

/* ---------- Create: workout picture grid ---------- */
[class*="st-key-fp-type-"] {
  position: relative; gap: 0; margin-bottom: .35rem;
  border-radius: var(--radius); border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(22, 34, 56, .8), rgba(15, 24, 42, .8));
  box-shadow: var(--shadow); overflow: hidden;
  transition: transform .3s var(--ease), box-shadow .3s var(--ease), border-color .3s var(--ease);
}
[class*="st-key-fp-type-"]:hover {
  transform: translateY(-4px); box-shadow: var(--shadow-hover);
  border-color: rgba(52, 211, 153, .4);
}
/* The real button is stretched invisibly over the whole card. */
[class*="st-key-fp-type-"] [data-testid="stElementContainer"]:has(.stButton) {
  position: absolute; inset: 0; z-index: 2; margin: 0;
}
[class*="st-key-fp-type-"] .stButton, [class*="st-key-fp-type-"] .stButton > button {
  width: 100%; height: 100%;
}
[class*="st-key-fp-type-"] .stButton > button {
  opacity: 0; border-radius: var(--radius); cursor: pointer;
}
[class*="st-key-fp-type-"] .stButton > button:focus-visible { opacity: 1; background: transparent; }
.fp-type { padding: 1.1rem 1.1rem 1.15rem; }
.fp-type-art {
  display: grid; place-items: center; height: 7.2rem; border-radius: 16px; margin-bottom: .85rem;
  color: var(--primary-ink);
  background:
    radial-gradient(10rem 6rem at 70% 0%, rgba(16, 185, 129, .35), transparent 70%),
    linear-gradient(160deg, rgba(16, 185, 129, .16), rgba(16, 185, 129, .04));
  box-shadow: inset 0 0 0 1px rgba(52, 211, 153, .18);
}
.fp-type-art svg { width: 5.2rem; height: 5.2rem; filter: drop-shadow(0 0 10px currentColor); }
.tone-cardio .fp-type-art, .fp-type-art.tone-cardio {
  color: var(--cardio-ink);
  background:
    radial-gradient(10rem 6rem at 70% 0%, rgba(249, 115, 98, .35), transparent 70%),
    linear-gradient(160deg, rgba(249, 115, 98, .16), rgba(249, 115, 98, .04));
  box-shadow: inset 0 0 0 1px rgba(249, 115, 98, .2);
}
.tone-strength .fp-type-art, .fp-type-art.tone-strength {
  color: var(--strength-ink);
  background:
    radial-gradient(10rem 6rem at 70% 0%, rgba(59, 130, 246, .38), transparent 70%),
    linear-gradient(160deg, rgba(59, 130, 246, .16), rgba(59, 130, 246, .04));
  box-shadow: inset 0 0 0 1px rgba(96, 165, 250, .2);
}
.tone-mind .fp-type-art, .fp-type-art.tone-mind {
  color: var(--violet-ink);
  background:
    radial-gradient(10rem 6rem at 70% 0%, rgba(139, 92, 246, .38), transparent 70%),
    linear-gradient(160deg, rgba(139, 92, 246, .16), rgba(139, 92, 246, .04));
  box-shadow: inset 0 0 0 1px rgba(167, 139, 250, .22);
}
.fp-type-art.is-custom, .fp-type-art.tone-custom { height: 5.5rem; margin: 0; color: var(--muted); }
.fp-type-art.is-custom svg, .fp-type-art.tone-custom svg { width: 3.6rem; height: 3.6rem; filter: none; }
.fp-type-label { color: var(--ink); font: 600 1.1rem var(--display); letter-spacing: -.015em; }
.fp-type-tagline { color: var(--muted); font-size: .82rem; margin-top: .2rem; }
.fp-chosen { display: flex; align-items: center; gap: 1.4rem; margin: .5rem 0 1.6rem; }
.fp-chosen .fp-type-art { flex: 0 0 7rem; width: 7rem; height: 7rem; margin: 0; }
.fp-chosen .fp-type-art svg { width: 5rem; height: 5rem; }

/* ---------- Exercise editor rows ---------- */
[class*="st-key-fp-row-"] {
  padding: .85rem 1rem .6rem; margin-bottom: .4rem; border-radius: 16px;
  background: rgba(255, 255, 255, .03); border: 1px solid var(--line);
  transition: border-color .2s ease, background .2s ease;
}
[class*="st-key-fp-row-"]:focus-within {
  border-color: rgba(52, 211, 153, .35); background: rgba(16, 185, 129, .04);
}
[class*="st-key-fp-row-"] input[type="text"]:not([inputmode]) { font-weight: 600; }
[class*="st-key-fp-trash-row-"] .stButton > button {
  min-height: 2.4rem; padding: 0; color: var(--muted); background: transparent; border-color: transparent;
}
[class*="st-key-fp-trash-row-"] .stButton > button:hover {
  color: #FDA4AF; background: rgba(225, 29, 72, .12); border-color: rgba(244, 63, 94, .35);
  box-shadow: none;
}
[class*="st-key-fp-chips-"] { flex-wrap: wrap; gap: .45rem; margin-top: .4rem; }
[class*="st-key-fp-chips-"] .stButton > button {
  min-height: 2.1rem; padding: 0 .85rem; font-size: .82rem; font-weight: 500;
  background: var(--primary-soft); color: var(--primary-ink);
  border: 1px dashed rgba(52, 211, 153, .45);
}
[data-testid="stSegmentedControl"] button { min-width: 2.6rem; }

/* ---------- Trash button + dialogs ---------- */
[class*="st-key-fp-trash-"] .stButton > button {
  padding: 0; min-height: 2.65rem; color: var(--muted); background: transparent;
  border-color: var(--line);
}
[class*="st-key-fp-trash-"] .stButton > button:hover {
  color: #FDA4AF; background: rgba(225, 29, 72, .12); border-color: rgba(244, 63, 94, .45);
  box-shadow: 0 8px 20px -8px rgba(225, 29, 72, .5);
}
[data-testid="stDialog"] { align-items: center; padding-top: 0; }
[data-testid="stDialog"] [role="dialog"] {
  background: linear-gradient(180deg, #16223A, #0F1A2E);
  border: 1px solid var(--line-strong); border-radius: 22px;
  box-shadow: 0 40px 80px -20px rgba(0, 0, 0, .8), 0 0 0 1px rgba(16, 185, 129, .08);
}
[data-testid="stDialog"] [role="dialog"] h2 { font-family: var(--display); letter-spacing: -.02em; }

/* ---------- Top bar: floating dark glass pill ---------- */
.st-key-fp-topbar {
  position: sticky; top: calc(env(safe-area-inset-top, 0px) + .75rem); z-index: 50;
  margin: 0 0 1.75rem; padding: .45rem .55rem .45rem 1rem;
  background: rgba(13, 22, 40, .7);
  backdrop-filter: saturate(160%) blur(18px);
  -webkit-backdrop-filter: saturate(160%) blur(18px);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  box-shadow: var(--highlight), 0 16px 40px -16px rgba(0, 0, 0, .7);
}
.st-key-fp-topbar .stButton > button {
  min-height: 2.35rem; padding: 0 .9rem; border-color: transparent; background: transparent;
  color: var(--muted); font-weight: 500; box-shadow: none;
}
.st-key-fp-topbar .stButton > button:hover {
  color: var(--ink); background: rgba(255, 255, 255, .06); border-color: transparent;
  box-shadow: none; transform: none;
}
.st-key-fp-topbar .stButton > button[kind="primary"] {
  background: #F1F5F9; color: var(--ink-dark); font-weight: 600;
  box-shadow: 0 6px 18px -6px rgba(255, 255, 255, .25);
}
.st-key-fp-topbar .stButton > button[kind="primary"]:hover { background: #FFFFFF; color: var(--ink-dark); }
.st-key-logout .stButton > button, .st-key-fp-topbar [class*="st-key-logout"] button {
  border: 1px solid var(--line-strong) !important;
}

/* Streamlit's markdown wrapper adds bottom margins; centre the bar's HTML blocks. */
.st-key-fp-topbar [data-testid="stColumn"] > div,
.st-key-fp-topbar [data-testid="stVerticalBlock"] { justify-content: center; }
.st-key-fp-topbar [data-testid="stElementContainer"]:has(.stMarkdown) {
  display: flex; align-items: center; min-height: 2.35rem;
}
.st-key-fp-topbar .stMarkdown, .st-key-fp-topbar [data-testid="stMarkdownContainer"] {
  width: 100%; margin: 0 !important;
}
.st-key-fp-topbar [data-testid="stMarkdownContainer"] > * { margin: 0 !important; }

.fp-brand { display: flex; align-items: center; gap: .6rem; }
.fp-brand-name {
  color: var(--ink); font: 700 1.05rem var(--display); letter-spacing: -.02em; white-space: nowrap;
}
.fp-avatar-row {
  display: flex; align-items: center; justify-content: flex-end; gap: .6rem; min-width: 0;
}
.fp-avatar {
  flex: 0 0 2.15rem; width: 2.15rem; height: 2.15rem; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--gradient); color: #fff; font-size: .74rem; font-weight: 700;
  letter-spacing: .02em;
  box-shadow: 0 0 0 3px var(--bg), 0 0 0 4px rgba(52, 211, 153, .45), 0 0 16px rgba(16, 185, 129, .4);
}
.fp-account-name {
  min-width: 0; overflow: hidden; text-overflow: ellipsis;
  color: var(--muted); font-size: .82rem; white-space: nowrap;
}

/* ---------- Page header ---------- */
.fp-eyebrow {
  display: inline-flex; align-items: center; gap: .5rem;
  color: var(--primary-ink); font-size: .72rem; font-weight: 700;
  letter-spacing: .16em; text-transform: uppercase;
}
.fp-eyebrow::before {
  content: ""; width: 1.4rem; height: 2px; border-radius: 2px; background: var(--gradient);
}
.fp-page-title {
  margin: .5rem 0 .5rem; color: var(--ink);
  font: 700 clamp(2rem, 4vw, 3rem)/1.04 var(--display); letter-spacing: -.04em;
}
.fp-page-subtitle {
  max-width: 44rem; margin: 0 0 1.75rem; color: var(--muted);
  font-size: 1.05rem; line-height: 1.6;
}

/* ---------- Hero: the brightest panel on the page ---------- */
.fp-hero {
  position: relative; overflow: hidden; isolation: isolate;
  display: flex; align-items: center; justify-content: space-between; gap: 2rem;
  padding: 2.4rem 2.6rem; margin-bottom: 1.25rem;
  background:
    radial-gradient(28rem 18rem at 92% 10%, rgba(16, 185, 129, .38), transparent 65%),
    radial-gradient(26rem 16rem at 0% 110%, rgba(59, 130, 246, .28), transparent 65%),
    linear-gradient(135deg, #0E1729 0%, #13203A 100%);
  border: 1px solid rgba(52, 211, 153, .18); border-radius: 28px;
  box-shadow: var(--highlight), var(--shadow-lg), 0 0 60px -20px rgba(16, 185, 129, .35);
}
.fp-hero::before {
  content: ""; position: absolute; inset: 0; z-index: -1;
  background-image:
    linear-gradient(rgba(255, 255, 255, .05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, .05) 1px, transparent 1px);
  background-size: 36px 36px;
  -webkit-mask-image: radial-gradient(ellipse at 70% 30%, #000 10%, transparent 70%);
  mask-image: radial-gradient(ellipse at 70% 30%, #000 10%, transparent 70%);
}
.fp-hero .fp-page-title { color: #F8FAFC; font-size: clamp(2.2rem, 4.6vw, 3.4rem); }
.fp-hero .fp-page-subtitle { margin-bottom: 0; color: rgba(226, 232, 240, .72); }
.fp-accent {
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}

/* ---------- Progress ring ---------- */
.fp-ring { position: relative; flex: 0 0 8.5rem; width: 8.5rem; height: 8.5rem; }
.fp-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); overflow: visible; }
.fp-ring-track { stroke: rgba(255, 255, 255, .08); }
.fp-ring-value {
  stroke: url(#fp-ring-grad); transition: stroke-dashoffset .8s var(--ease);
  filter: drop-shadow(0 0 6px rgba(52, 211, 153, .6));
}
.fp-ring-label {
  position: absolute; inset: 0; display: grid; place-content: center; text-align: center;
}
.fp-ring-number { color: var(--ink); font: 700 1.75rem/1 var(--display); letter-spacing: -.03em; }
.fp-ring-caption { color: var(--muted); font-size: .7rem; margin-top: .3rem; }
.fp-hero .fp-ring-number { color: #fff; font-size: 2rem; }

/* ---------- Stat tiles ---------- */
.fp-stats {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 1rem; margin-bottom: 2.25rem;
}
.fp-stat {
  position: relative; overflow: hidden;
  padding: 1.2rem 1.25rem 1.15rem;
  background: linear-gradient(180deg, rgba(22, 34, 56, .8), rgba(15, 24, 42, .8));
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow);
  transition: transform .3s var(--ease), box-shadow .3s var(--ease), border-color .3s var(--ease);
}
.fp-stat:hover {
  transform: translateY(-3px); box-shadow: var(--shadow-hover);
  border-color: rgba(16, 185, 129, .22);
}
.fp-stat::after {
  content: ""; position: absolute; left: 1.25rem; right: 1.25rem; top: 0; height: 2px;
  border-radius: 0 0 2px 2px; background: var(--gradient); opacity: 0;
  box-shadow: 0 0 12px rgba(16, 185, 129, .8);
  transition: opacity .3s ease;
}
.fp-stat:hover::after { opacity: 1; }
.fp-stat-label {
  color: var(--muted); font-size: .72rem; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase;
}
.fp-stat-value {
  margin-top: .55rem; color: var(--ink);
  font: 700 2.2rem/1 var(--display); letter-spacing: -.03em; font-variant-numeric: tabular-nums;
}
.fp-stat-value small { color: var(--muted); font: 500 .95rem "Inter", sans-serif; letter-spacing: 0; }
.fp-stat-sub { margin-top: .45rem; color: var(--muted); font-size: .8rem; }
.fp-stat-icon {
  position: absolute; top: 1rem; right: 1rem;
  width: 2.1rem; height: 2.1rem; display: grid; place-items: center; border-radius: 10px;
  background: var(--primary-soft); color: var(--primary-ink);
  box-shadow: inset 0 0 0 1px rgba(52, 211, 153, .18);
}
.fp-stat-icon svg { width: 1.05rem; height: 1.05rem; }
.fp-stat-icon.tone-blue { background: var(--strength-soft); color: var(--strength-ink); box-shadow: inset 0 0 0 1px rgba(96, 165, 250, .2); }
.fp-stat-icon.tone-coral { background: var(--cardio-soft); color: var(--cardio-ink); box-shadow: inset 0 0 0 1px rgba(249, 115, 98, .2); }
.fp-stat-icon.tone-amber { background: var(--amber-soft); color: var(--amber-ink); box-shadow: inset 0 0 0 1px rgba(245, 158, 11, .2); }
.fp-stat-icon.tone-violet { background: var(--violet-soft); color: var(--violet-ink); box-shadow: inset 0 0 0 1px rgba(139, 92, 246, .22); }

/* ---------- Section heading ---------- */
.fp-section {
  margin: .35rem 0 .85rem; color: var(--ink);
  font: 600 1.3rem var(--display); letter-spacing: -.02em;
}

/* ---------- Icons: emerald by default, coral for cardio, blue for strength ---------- */
.fp-workout { display: flex; align-items: center; gap: 1rem; min-width: 0; }
.fp-icon {
  flex: 0 0 3.1rem; width: 3.1rem; height: 3.1rem; display: grid; place-items: center;
  border-radius: 14px; background: var(--primary-soft); color: var(--primary-ink);
  box-shadow: inset 0 0 0 1px rgba(52, 211, 153, .2);
}
.fp-icon svg { width: 1.45rem; height: 1.45rem; }
.fp-icon.is-cardio {
  background: var(--cardio-soft); color: var(--cardio-ink);
  box-shadow: inset 0 0 0 1px rgba(249, 115, 98, .22);
}
.fp-icon.is-strength {
  background: var(--strength-soft); color: var(--strength-ink);
  box-shadow: inset 0 0 0 1px rgba(96, 165, 250, .22);
}

.fp-icon.is-mind {
  background: var(--violet-soft); color: var(--violet-ink);
  box-shadow: inset 0 0 0 1px rgba(139, 92, 246, .25);
}

/* ---------- Workout card ---------- */
.fp-workout-title {
  color: var(--ink); font: 600 1.12rem var(--display); letter-spacing: -.015em;
  overflow-wrap: anywhere;
}
.fp-meta { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .45rem; }
.fp-chip {
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .2rem .65rem; border-radius: 999px;
  background: var(--surface-2); border: 1px solid var(--line);
  color: #CBD5E1; font-size: .74rem; font-weight: 500;
}
.fp-chip.is-live {
  color: var(--primary-ink); border-color: rgba(52, 211, 153, .4); background: var(--primary-soft);
}
.fp-chip.is-live::before {
  content: ""; width: .45rem; height: .45rem; border-radius: 50%; background: var(--primary);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, .25), 0 0 8px rgba(16, 185, 129, .8);
  animation: fp-pulse 1.6s ease-in-out infinite;
}
@keyframes fp-pulse { 50% { opacity: .35; } }

.fp-segments { display: flex; gap: .3rem; margin: .2rem 0 .5rem; }
.fp-segment { flex: 1; height: .5rem; border-radius: 99px; background: var(--surface-3); }
.fp-segment.is-done { background: var(--gradient); box-shadow: 0 0 10px rgba(16, 185, 129, .55); }
.fp-progress-label {
  display: flex; justify-content: space-between; color: var(--muted); font-size: .78rem;
}
.fp-progress-label span:last-child { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }

.fp-bar { height: .55rem; overflow: hidden; border-radius: 99px; background: var(--surface-3); }
.fp-bar-fill {
  height: 100%; border-radius: inherit;
  background: linear-gradient(90deg, var(--strength), var(--primary)); transition: width .6s var(--ease);
  box-shadow: 0 0 10px rgba(16, 185, 129, .5);
}

/* ---------- Activity timeline ---------- */
.fp-timeline {
  position: relative; margin: .4rem 0 0 .4rem; padding-left: 1.4rem;
  border-left: 2px dashed var(--line-strong);
}
.fp-event { position: relative; padding: 0 0 1.25rem; }
.fp-event:last-child { padding-bottom: .25rem; }
.fp-event::before {
  content: ""; position: absolute; left: -1.88rem; top: .28rem;
  width: .8rem; height: .8rem; border-radius: 50%;
  background: var(--primary); border: 3px solid var(--surface-solid);
  box-shadow: 0 0 0 1px rgba(52, 211, 153, .45), 0 0 10px rgba(16, 185, 129, .6);
}
.fp-event-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem; }
.fp-event-title { color: var(--ink); font-weight: 600; }
.fp-event-date { color: var(--muted); font-size: .76rem; }
.fp-event .fp-meta { margin-top: .45rem; }

/* ---------- Exercise list (plan + preview) ---------- */
.fp-exercise {
  display: flex; align-items: flex-start; gap: 1rem;
  padding: 1rem .25rem; border-bottom: 1px solid var(--line);
  transition: background .2s ease;
}
.fp-exercise:hover { background: rgba(255, 255, 255, .03); border-radius: 12px; }
.fp-exercise:last-child { border-bottom: 0; }
.fp-index {
  flex: 0 0 2.1rem; width: 2.1rem; height: 2.1rem; display: grid; place-items: center;
  border-radius: 10px;
  background: var(--gradient); color: #fff; font: 700 .76rem var(--display);
  box-shadow: 0 4px 14px -4px rgba(16, 185, 129, .7);
}
.fp-exercise-name { color: var(--ink); font-weight: 600; font-size: 1.02rem; }
.fp-exercise-note { color: var(--muted); font-size: .84rem; margin-top: .2rem; }
.fp-exercise-spec {
  margin-left: auto; text-align: right; color: var(--ink);
  font: 600 .95rem var(--display); white-space: nowrap; font-variant-numeric: tabular-nums;
}
.fp-exercise-spec small { display: block; color: var(--muted); font: 500 .74rem "Inter", sans-serif; margin-top: .15rem; }

.fp-coach {
  position: relative; display: flex; gap: .85rem; align-items: flex-start;
  padding: 1rem 1.15rem 1rem 1.35rem; margin: .6rem 0 1rem;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(249, 115, 98, .12), rgba(251, 146, 60, .06));
  border: 1px solid rgba(249, 115, 98, .22); color: var(--ink); font-size: .92rem; line-height: 1.6;
  overflow: hidden;
}
.fp-coach::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, #F97362, #FB923C);
}
.fp-coach b {
  flex: 0 0 auto; color: var(--cardio-ink); font-size: .7rem; letter-spacing: .12em;
  text-transform: uppercase; padding-top: .2rem;
}

/* ---------- Live session ---------- */
.fp-sets { display: flex; flex-wrap: wrap; gap: .55rem; margin: .45rem 0 1rem; }
.fp-set {
  min-width: 4.8rem; padding: .6rem .75rem; border-radius: 14px; text-align: center;
  background: var(--surface-2); border: 1px solid var(--line);
  transition: all .25s var(--ease);
}
.fp-set-label { color: var(--muted); font-size: .66rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }
.fp-set-value { color: var(--ink); font: 600 1rem var(--display); margin-top: .15rem; }
.fp-set.is-done { background: var(--primary-soft); border-color: rgba(52, 211, 153, .4); }
.fp-set.is-done .fp-set-value { color: var(--primary-ink); }
.fp-set.is-active {
  background: var(--strength-soft); border-color: var(--strength);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, .15), 0 0 20px -4px rgba(59, 130, 246, .6);
}

.fp-timer { display: flex; align-items: center; gap: 1.4rem; padding: 1rem 0; }
.fp-timer .fp-ring { flex-basis: 7rem; width: 7rem; height: 7rem; }
.fp-timer .fp-ring-value { stroke: var(--strength); filter: drop-shadow(0 0 6px rgba(59, 130, 246, .7)); }
.fp-timer-title { color: var(--ink); font: 600 1.15rem var(--display); }

/* ---------- Auth ---------- */
.fp-auth-title {
  margin: 1.5rem 0 1rem; color: var(--ink);
  font: 700 clamp(2.4rem, 5.5vw, 4rem)/1 var(--display); letter-spacing: -.045em;
}
.fp-features { list-style: none; padding: 0; margin: 1.75rem 0; display: grid; gap: 1rem; }
.fp-features li { display: flex; gap: .85rem; align-items: flex-start; color: var(--muted); }
.fp-features .fp-icon { flex-basis: 2.4rem; width: 2.4rem; height: 2.4rem; border-radius: 11px; }
.fp-features .fp-icon svg { width: 1.1rem; height: 1.1rem; }
.fp-features strong { display: block; color: var(--ink); font-weight: 600; }

/* ---------- Inputs & misc ---------- */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea { font-size: .95rem; }
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  border-radius: 12px !important; background-color: rgba(255, 255, 255, .04) !important;
  transition: box-shadow .2s ease, border-color .2s ease;
}
[data-baseweb="input"] > div, [data-baseweb="base-input"] { background-color: transparent !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
[data-baseweb="select"] > div:focus-within {
  box-shadow: 0 0 0 4px rgba(16, 185, 129, .2);
}
[data-testid="stTabs"] [role="tab"] { font-weight: 500; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: var(--primary-ink); font-weight: 600; }
[data-testid="stAlert"] { border-radius: 14px; }
[data-testid="stVegaLiteChart"] { margin-top: .25rem; }
[data-testid="stForm"] { border-color: var(--line) !important; border-radius: 16px; }

.fp-empty { padding: 2.5rem 1rem 2.25rem; text-align: center; }
.fp-empty .fp-icon {
  margin: 0 auto 1.1rem; width: 3.6rem; height: 3.6rem; border-radius: 18px;
  box-shadow: inset 0 0 0 1px rgba(52, 211, 153, .25), 0 0 0 8px rgba(255, 255, 255, .03),
    0 0 0 16px rgba(255, 255, 255, .015), 0 0 30px rgba(16, 185, 129, .25);
}
.fp-empty .fp-icon.is-cardio { box-shadow: inset 0 0 0 1px rgba(249, 115, 98, .25), 0 0 0 8px rgba(255, 255, 255, .03), 0 0 0 16px rgba(255, 255, 255, .015), 0 0 30px rgba(249, 115, 98, .2); }
.fp-empty .fp-icon.is-strength { box-shadow: inset 0 0 0 1px rgba(96, 165, 250, .25), 0 0 0 8px rgba(255, 255, 255, .03), 0 0 0 16px rgba(255, 255, 255, .015), 0 0 30px rgba(59, 130, 246, .2); }
.fp-empty-title { color: var(--ink); font: 600 1.25rem var(--display); letter-spacing: -.02em; }
.fp-empty p { margin: .45rem auto 0; max-width: 28rem; line-height: 1.6; }

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 3rem; }
  .fp-hero { flex-direction: column; align-items: flex-start; padding: 1.6rem 1.4rem; border-radius: 22px; }
  .fp-ring { flex-basis: 7rem; width: 7rem; height: 7rem; }
  .fp-account-name { display: none; }
  .st-key-fp-topbar { position: static; border-radius: 22px; padding: .6rem; margin-bottom: 1.75rem; }
  .st-key-fp-topbar [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .3rem; }
  .st-key-fp-topbar [data-testid="stColumn"] {
    flex: 1 1 30% !important; width: auto !important; min-width: 0 !important;
  }
  .st-key-fp-topbar [data-testid="stColumn"]:first-child {
    flex-basis: 100% !important; margin-bottom: .5rem;
  }
  .st-key-fp-topbar [data-testid="stColumn"]:nth-last-child(2) { display: none; }
  .fp-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .7rem; }
  .fp-chosen { gap: 1rem; }
  .fp-chosen .fp-type-art { flex-basis: 5rem; width: 5rem; height: 5rem; }
  .fp-stat-value { font-size: 1.8rem; }
  .fp-exercise-spec { font-size: .82rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition-duration: .01ms !important; }
}
</style>
"""


def inject_theme() -> None:
    st.html(CSS + MASCOT_CSS + CELEBRATION_CSS)
