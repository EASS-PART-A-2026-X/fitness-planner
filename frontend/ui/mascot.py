"""Rep, the Fitness Planner mascot: a small emerald buddy with a coral headband.

Each page gets its own pose. When the page changes, the new SVG replaces the old
one, so the entrance animation plays again: Rep slides in from the side you
navigated from, does that page's move, and a short speech bubble pops up.
"""

POSES = {
    "wave": "Hey there!",
    "think": "Hmm, let me plan…",
    "lift": "Lift time!",
    "run": "Keep moving!",
    "celebrate": "Woohoo!",
}
SECTION_POSES = {
    "dashboard": "wave",
    "coach": "think",
    "plans": "lift",
    "activities": "run",
    "analytics": "celebrate",
}
NAV_ORDER = ("dashboard", "coach", "plans", "activities", "analytics")

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
        '<ellipse class="m-shadow" cx="32" cy="59" rx="13" ry="2.4" fill="rgba(15,23,42,.12)"/>'
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

/* Speech bubble: pops in on each page change, then fades away. */
.fp-bubble {
  position: absolute; left: 104%; top: 50%; z-index: 5;
  padding: .25rem .65rem; border-radius: 999px 999px 999px 4px;
  background: var(--ink, #0F172A); color: #fff; white-space: nowrap;
  font: 600 .68rem "Inter", sans-serif; pointer-events: none;
  box-shadow: 0 6px 16px rgba(15, 23, 42, .18);
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
    "0% { opacity: 0; transform: translate(-6px, -50%) scale(.7); }"
    " 12%, 78% { opacity: 1; transform: translate(0, -50%); }"
    " 100% { opacity: 0; transform: translate(4px, -50%); visibility: hidden; }"
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
