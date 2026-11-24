"""Rep, the Fitness Planner mascot: a small emerald buddy with a coral headband.

Each page gets its own pose. When the page changes, the new SVG replaces the old
one, so the entrance animation plays again: Rep slides in from the side you
navigated from, does that page's move, and a short speech bubble pops up.
"""

import html
import math

POSES = {
    "wave": "Hey there!",
    "think": "Hmm, let me plan…",
    "lift": "Lift time!",
    "run": "Keep moving!",
    "celebrate": "Woohoo!",
}
SECTION_POSES = {
    "dashboard": "wave",
    "plans": "lift",
    "create": "think",
    "activities": "run",
    "analytics": "celebrate",
}
NAV_ORDER = ("dashboard", "plans", "create", "activities", "analytics")

INK = "#0F172A"
EMERALD = "#10B981"
CORAL = "#F97362"
BLUE = "#3B82F6"
ARM = "#059669"

_EYES_OPEN = (
    f'<g class="m-eyes"><ellipse cx="27" cy="33" rx="2" ry="2.6" fill="{INK}"/>'
    f'<ellipse cx="37" cy="33" rx="2" ry="2.6" fill="{INK}"/>'
    '<circle cx="27.7" cy="32.1" r=".7" fill="#fff"/>'
    '<circle cx="37.7" cy="32.1" r=".7" fill="#fff"/></g>'
)
_EYES_UP = (
    f'<g class="m-eyes"><ellipse cx="28" cy="31.6" rx="2" ry="2.6" fill="{INK}"/>'
    f'<ellipse cx="38" cy="31.6" rx="2" ry="2.6" fill="{INK}"/>'
    '<circle cx="28.8" cy="30.6" r=".7" fill="#fff"/>'
    '<circle cx="38.8" cy="30.6" r=".7" fill="#fff"/></g>'
)
_EYES_HAPPY = (
    f'<path d="M24.6 33.6q2.4-3 4.8 0M34.6 33.6q2.4-3 4.8 0" fill="none" '
    f'stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>'
)
_SMILE = (
    f'<path d="M29 38.2q3 2.8 6 0" fill="none" stroke="{INK}" '
    'stroke-width="1.6" stroke-linecap="round"/>'
)
_MOUTH_OPEN = (
    f'<path d="M28.6 37.6q3.4 5 6.8 0z" fill="{INK}"/>'
    f'<path d="M30.4 39.6q1.6 1.4 3.2 0" fill="none" stroke="{CORAL}" stroke-width="1.2"/>'
)
_MOUTH_THINK = (
    f'<path d="M30 39h4" stroke="{INK}" stroke-width="1.6" stroke-linecap="round"/>'
)


def _arm(x1: float, y1: float, x2: float, y2: float, cls: str = "") -> str:
    return (
        f'<g class="{cls}"><path d="M{x1} {y1}L{x2} {y2}" stroke="{ARM}" '
        'stroke-width="4" stroke-linecap="round"/>'
        f'<circle cx="{x2}" cy="{y2}" r="2.6" fill="{ARM}"/></g>'
    )


def _legs(cls: str = "") -> str:
    return (
        f'<g class="{cls}"><path class="m-leg-l" d="M27 48.5v6.5" stroke="{INK}" '
        'stroke-width="3" stroke-linecap="round"/>'
        f'<path class="m-leg-r" d="M37 48.5v6.5" stroke="{INK}" '
        'stroke-width="3" stroke-linecap="round"/></g>'
    )


def _sparkle(x: float, y: float, size: float, color: str, delay: float) -> str:
    s = size
    return (
        f'<path class="m-twinkle" style="animation-delay:{delay}s" '
        f'd="M{x} {y - s}Q{x} {y} {x + s} {y}Q{x} {y} {x} {y + s}'
        f'Q{x} {y} {x - s} {y}Q{x} {y} {x} {y - s}z" fill="{color}"/>'
    )


def _confetti() -> str:
    pieces = (
        (10, 14, CORAL, 0.0),
        (54, 10, BLUE, 0.15),
        (6, 30, EMERALD, 0.3),
        (58, 28, CORAL, 0.45),
        (18, 6, BLUE, 0.6),
        (46, 4, EMERALD, 0.75),
    )
    return "".join(
        f'<rect class="m-confetti" style="animation-delay:{delay}s" x="{x}" y="{y}" '
        f'width="3" height="3" rx=".8" fill="{color}"/>'
        for x, y, color, delay in pieces
    )


def _pose_parts(pose: str) -> tuple[str, str, str, str]:
    """Returns (behind_body, arms_and_props, eyes, mouth) for a pose."""
    if pose == "think":
        sparkles = (
            _sparkle(52, 12, 4, "#FBBF24", 0)
            + _sparkle(59, 22, 2.6, BLUE, 0.4)
            + _sparkle(45, 5, 2.4, CORAL, 0.8)
        )
        arms = _arm(18, 38, 12, 45) + _arm(45, 40, 38.5, 42.5, "m-chin")
        return sparkles, arms, _EYES_UP, _MOUTH_THINK
    if pose == "lift":
        dumbbell = (
            f'<g class="m-lift"><path d="M12 11h40" stroke="{INK}" stroke-width="2.4" '
            'stroke-linecap="round"/>'
            f'<rect x="8" y="6" width="5" height="10" rx="1.6" fill="{BLUE}"/>'
            f'<rect x="51" y="6" width="5" height="10" rx="1.6" fill="{BLUE}"/>'
            + _arm(19, 30, 15, 12)
            + _arm(45, 30, 49, 12)
            + "</g>"
        )
        return "", dumbbell, _EYES_OPEN, _SMILE
    if pose == "run":
        lines = (
            f'<g class="m-speed" stroke="{CORAL}" stroke-width="2" stroke-linecap="round">'
            '<path d="M2 28h6"/><path d="M0 35h7"/><path d="M3 42h5"/></g>'
        )
        arms = _arm(18, 36, 12, 30, "m-swing-a") + _arm(46, 36, 52, 42, "m-swing-b")
        return lines, arms, _EYES_OPEN, _SMILE
    if pose == "celebrate":
        arms = _arm(19, 32, 10, 18, "m-cheer-l") + _arm(45, 32, 54, 18, "m-cheer-r")
        return _confetti(), arms, _EYES_HAPPY, _MOUTH_OPEN
    # wave (default)
    arms = _arm(18, 38, 12, 45) + _arm(46, 34, 54, 22, "m-wave")
    return "", arms, _EYES_OPEN, _SMILE


def mascot_svg(pose: str) -> str:
    behind, arms, eyes, mouth = _pose_parts(pose)
    legs = _legs("m-run" if pose == "run" else "")
    return (
        f'<svg class="m-svg" viewBox="0 0 64 64" role="img" aria-label="Rep the mascot, {pose}">'
        '<ellipse class="m-shadow" cx="32" cy="59" rx="13" ry="2.4" fill="rgba(0,0,0,.35)"/>'
        f'<g class="m-bob">{behind}{legs}'
        f'<rect x="16" y="18" width="32" height="32" rx="16" fill="{EMERALD}"/>'
        '<ellipse cx="32" cy="41" rx="9" ry="6.5" fill="#6EE7B7" opacity=".55"/>'
        f'<rect x="17" y="22.5" width="30" height="4.2" rx="2.1" fill="{CORAL}"/>'
        f'<path d="M46 23.5l5-2.5-1.5 4.5 3 2-5 .5z" fill="{CORAL}"/>'
        f"{eyes}"
        '<circle cx="23.4" cy="37.4" r="2.2" fill="#FDA4AF" opacity=".75"/>'
        '<circle cx="40.6" cy="37.4" r="2.2" fill="#FDA4AF" opacity=".75"/>'
        f"{mouth}{arms}</g></svg>"
    )


def mascot_html(section: str, previous: str | None = None) -> str:
    """Rep plus speech bubble; slides in from the side of the previous nav item."""
    pose = SECTION_POSES.get(section, "wave")
    if previous in NAV_ORDER and section in NAV_ORDER and previous != section:
        offset = -26 if NAV_ORDER.index(section) > NAV_ORDER.index(previous) else 26
    else:
        offset = 0
    return (
        f'<span class="fp-mascot pose-{pose}" style="--from:{offset}px">'
        f"{mascot_svg(pose)}"
        f'<span class="fp-bubble">{POSES[pose]}</span></span>'
    )


def celebration_html(title: str) -> str:
    """Full-screen 'workout complete' moment: a giant Rep, a ring burst and confetti.

    Pure CSS, so it plays once per page load and then hides itself.
    """
    colors = (EMERALD, CORAL, BLUE, "#FBBF24", "#5EEAD4", "#F472B6")
    pieces = []
    count = 30
    for index in range(count):
        angle = 2 * math.pi * index / count + (index % 3) * 0.17
        distance = 190 + (index * 47) % 170
        x = round(math.cos(angle) * distance)
        y = round(math.sin(angle) * distance * 0.8) + 90
        pieces.append(
            f'<i class="fp-cel-bit" style="--x:{x}px;--y:{y}px;'
            f"--r:{(index * 97) % 540 - 270}deg;--c:{colors[index % len(colors)]};"
            f'--d:{0.25 + (index % 6) * 0.05:.2f}s"></i>'
        )
    return (
        '<div class="fp-celebrate" role="status" aria-live="polite">'
        '<div class="fp-cel-box"><div class="fp-cel-stage">'
        '<span class="fp-cel-ring"></span><span class="fp-cel-ring is-late"></span>'
        f"{''.join(pieces)}"
        f'<div class="fp-cel-mascot"><div class="pose-celebrate">{mascot_svg("celebrate")}'
        "</div></div></div>"
        '<div class="fp-cel-title">Workout complete!</div>'
        f'<div class="fp-cel-sub">{html.escape(title)} · added to this week</div>'
        "</div></div>"
    )


CELEBRATION_CSS = """
<style>
.fp-celebrate {
  position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center;
  pointer-events: none;
  background: radial-gradient(circle at 50% 45%, rgba(16, 185, 129, .22), rgba(11, 18, 32, .82) 60%);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  animation: fp-cel-fade 5s ease .15s both;
}
@keyframes fp-cel-fade {
  0% { opacity: 0; } 8% { opacity: 1; } 78% { opacity: 1; }
  100% { opacity: 0; visibility: hidden; }
}
.fp-cel-box { display: flex; flex-direction: column; align-items: center; text-align: center; }
.fp-cel-stage { position: relative; width: min(18rem, 70vw); height: min(18rem, 70vw); }
.fp-cel-mascot {
  position: absolute; inset: 0;
  animation: fp-cel-pop .9s cubic-bezier(.34, 1.56, .64, 1) both;
  filter: drop-shadow(0 18px 40px rgba(16, 185, 129, .45));
}
.fp-cel-mascot .m-svg { width: 100%; height: 100%; overflow: visible; }
.fp-cel-mascot svg * { transform-box: fill-box; }
@keyframes fp-cel-pop {
  0% { transform: scale(.2) rotate(-20deg); opacity: 0; }
  60% { transform: scale(1.12) rotate(4deg); opacity: 1; }
  100% { transform: none; opacity: 1; }
}
.fp-cel-ring {
  position: absolute; inset: 12%; border-radius: 50%;
  border: 3px solid #34D399; box-shadow: 0 0 30px rgba(52, 211, 153, .7);
  animation: fp-cel-ring 1.3s cubic-bezier(.2, .8, .2, 1) .25s both;
}
.fp-cel-ring.is-late { border-color: #5EEAD4; animation-delay: .55s; }
@keyframes fp-cel-ring {
  0% { transform: scale(.3); opacity: 1; }
  100% { transform: scale(2.6); opacity: 0; }
}
.fp-cel-bit {
  position: absolute; left: 50%; top: 50%; width: 10px; height: 16px;
  border-radius: 3px; background: var(--c);
  animation: fp-cel-fly 1.9s cubic-bezier(.15, .75, .3, 1) var(--d) both;
}
.fp-cel-bit:nth-child(3n) { width: 12px; height: 12px; border-radius: 50%; }
@keyframes fp-cel-fly {
  0% { transform: translate(-50%, -50%) scale(.2) rotate(0); opacity: 0; }
  12% { opacity: 1; }
  100% {
    transform: translate(calc(-50% + var(--x)), calc(-50% + var(--y))) rotate(var(--r)) scale(1);
    opacity: 0;
  }
}
.fp-cel-title {
  margin-top: 1.25rem;
  font: 700 clamp(2.4rem, 6vw, 4rem)/1 "Space Grotesk", "Inter", sans-serif;
  letter-spacing: -.04em;
  background: linear-gradient(90deg, #34D399, #5EEAD4, #93C5FD);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: fp-cel-rise .7s cubic-bezier(.2, .8, .2, 1) .35s both;
}
.fp-cel-sub {
  margin-top: .6rem; color: #E2E8F0; font: 500 1.05rem "Inter", sans-serif;
  animation: fp-cel-rise .7s cubic-bezier(.2, .8, .2, 1) .5s both;
}
@keyframes fp-cel-rise { from { transform: translateY(14px); opacity: 0; } to { transform: none; opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .fp-celebrate { display: none; } }
</style>
"""

MASCOT_CSS = """
<style>
.fp-mascot {
  position: relative; display: inline-block; flex: 0 0 2.9rem;
  width: 2.9rem; height: 2.9rem;
}
.fp-mascot .m-svg { width: 100%; height: 100%; overflow: visible; }
.fp-mascot svg * { transform-box: fill-box; }

/* Idle: a gentle bounce with a squash on landing, and a blink. */
.m-bob { animation: m-bob 2.6s ease-in-out infinite; transform-origin: 50% 100%; }
@keyframes m-bob {
  0%, 100% { transform: translateY(0) scale(1.03, .97); }
  50% { transform: translateY(-2.5px) scale(.98, 1.02); }
}
.m-shadow { animation: m-shadow 2.6s ease-in-out infinite; transform-origin: center; }
@keyframes m-shadow { 50% { transform: scale(.8); opacity: .6; } }
.m-eyes { animation: m-blink 4.2s infinite; transform-origin: center; }
@keyframes m-blink { 0%, 94%, 100% { transform: scaleY(1); } 97% { transform: scaleY(.1); } }

/* Dashboard: wave hello. */
.m-wave { transform-origin: 0% 100%; animation: m-wave 1.4s ease-in-out .5s 3; }
@keyframes m-wave { 25% { transform: rotate(-22deg); } 75% { transform: rotate(14deg); } }

/* AI Coach: thinking, with twinkling sparkles. */
.m-chin { transform-origin: 100% 0%; animation: m-tap 1.2s ease-in-out infinite; }
@keyframes m-tap { 50% { transform: translateY(-1px) rotate(-6deg); } }
.m-twinkle { transform-origin: center; animation: m-twinkle 1.6s ease-in-out infinite; }
@keyframes m-twinkle {
  0%, 100% { transform: scale(.4) rotate(0); opacity: .3; }
  50% { transform: scale(1) rotate(45deg); opacity: 1; }
}
.pose-think .m-bob { animation-duration: 3.4s; }

/* Plans: press the dumbbell overhead. */
.m-lift { animation: m-lift 1.6s ease-in-out .3s infinite; }
@keyframes m-lift { 50% { transform: translateY(5px); } }

/* Activity: run in place. */
.pose-run .m-bob { animation: m-run-bob .5s ease-in-out infinite; }
@keyframes m-run-bob { 50% { transform: translateY(-2px) rotate(4deg); } }
.m-leg-l { animation: m-leg .5s ease-in-out infinite; transform-origin: 50% 0%; }
.m-leg-r { animation: m-leg .5s ease-in-out infinite reverse; transform-origin: 50% 0%; }
@keyframes m-leg { 0%, 100% { transform: rotate(28deg); } 50% { transform: rotate(-28deg); } }
.m-swing-a { transform-origin: 100% 100%; animation: m-swing .5s ease-in-out infinite; }
.m-swing-b { transform-origin: 0% 0%; animation: m-swing .5s ease-in-out infinite reverse; }
@keyframes m-swing { 50% { transform: rotate(30deg); } }
.m-speed { animation: m-speed .5s linear infinite; }
@keyframes m-speed { 0% { transform: translateX(4px); opacity: 0; } 50% { opacity: 1; } 100% { transform: translateX(-4px); opacity: 0; } }

/* Analytics: jump for joy with confetti. */
.pose-celebrate .m-bob { animation: m-jump 1.1s cubic-bezier(.3, 0, .3, 1) infinite; }
@keyframes m-jump {
  0%, 100% { transform: translateY(0) scale(1.06, .94); }
  45% { transform: translateY(-6px) scale(.96, 1.04); }
}
.m-cheer-l { transform-origin: 100% 100%; animation: m-cheer 1.1s ease-in-out infinite; }
.m-cheer-r { transform-origin: 0% 100%; animation: m-cheer 1.1s ease-in-out infinite reverse; }
@keyframes m-cheer { 50% { transform: rotate(12deg); } }
.m-confetti { transform-origin: center; animation: m-confetti 1.8s ease-out infinite; }
@keyframes m-confetti {
  0% { transform: translateY(6px) scale(0) rotate(0); opacity: 0; }
  20% { opacity: 1; transform: translateY(0) scale(1) rotate(60deg); }
  100% { transform: translateY(14px) rotate(260deg); opacity: 0; }
}

/* Speech bubble: pops in under Rep on each page change (clear of the brand name),
   then fades away. */
.fp-bubble {
  position: absolute; left: 30%; top: calc(100% + 8px); z-index: 60;
  padding: .3rem .7rem; border-radius: 4px 999px 999px 999px;
  background: #F1F5F9; color: #0B1220; white-space: nowrap;
  font: 600 .68rem "Inter", sans-serif; pointer-events: none;
  box-shadow: 0 6px 18px rgba(0, 0, 0, .45);
}
</style>
"""

# Streamlit reuses the DOM nodes when the markdown changes, so a plain class swap
# would not restart an animation. Giving every pose its own animation *name* does:
# the browser restarts an animation whenever its name changes.
_ENTER = (
    "0% { opacity: 0; transform: translateX(var(--from, 0)) scale(.6) rotate(-8deg); }"
    " 60% { opacity: 1; transform: translateX(0) scale(1.08, .92); }"
    " 100% { opacity: 1; transform: none; }"
)
_BUBBLE = (
    "0% { opacity: 0; transform: translateY(-6px) scale(.7); transform-origin: 0 0; }"
    " 12%, 78% { opacity: 1; transform: none; }"
    " 100% { opacity: 0; transform: translateY(4px); visibility: hidden; }"
)
MASCOT_CSS = MASCOT_CSS.replace(
    "</style>",
    "".join(
        f"@keyframes m-enter-{pose} {{ {_ENTER} }}"
        f"@keyframes m-bubble-{pose} {{ {_BUBBLE} }}"
        f".pose-{pose} {{ animation: m-enter-{pose} .7s cubic-bezier(.34, 1.56, .64, 1) both; }}"
        f".pose-{pose} .fp-bubble {{ animation: m-bubble-{pose} 2.8s ease .45s both; }}"
        for pose in POSES
    )
    + "</style>",
)
