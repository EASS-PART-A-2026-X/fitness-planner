"""Product analytics with PostHog. Off unless POSTHOG_API_KEY is set.

Privacy: people are identified by their numeric account id ("user-42"), never
by username or password, and no plan titles, goals or notes are sent; only
counts, workout types and which page or button was used. Events are sent from
the Streamlit server in the background, so analytics can never slow down or
break a page.
"""

import atexit
import hashlib
import logging
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from posthog import Posthog

DEFAULT_HOST = "https://us.i.posthog.com"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
LAST_PAGE_KEY = "fp-analytics-page"
log = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False)
def _client() -> Posthog | None:
    # Local runs read the repository's .env; real environment variables (e.g.
    # from docker compose) win.
    load_dotenv(ENV_FILE, override=False)
    key = os.getenv("POSTHOG_API_KEY", "").strip()
    if not key:
        return None
    client = Posthog(key, host=os.getenv("POSTHOG_HOST", DEFAULT_HOST).strip())
    atexit.register(client.shutdown)  # flush queued events when the app stops
    return client


def enabled() -> bool:
    return _client() is not None


def distinct_id_for(username: str) -> str:
    """Fallback id when the account id is unknown: a hash, never the name."""
    return "user-" + hashlib.sha256(username.encode()).hexdigest()[:16]


def distinct_id() -> str | None:
    """A stable, anonymous id for the signed-in person (None when signed out)."""
    if user_id := st.session_state.get("user_id"):
        return f"user-{user_id}"
    if username := st.session_state.get("username"):
        return distinct_id_for(str(username))
    return None


def capture(event: str, **properties: object) -> None:
    client = _client()
    who = distinct_id()
    if client is None or who is None:
        return
    try:
        client.capture(
            event, distinct_id=who, properties={"app": "fitness-planner", **properties}
        )
    except Exception:  # analytics must never break the app
        log.warning("PostHog capture failed for %s", event, exc_info=True)


def track_page(page: str) -> None:
    """One $pageview per page change (not per Streamlit rerun)."""
    if st.session_state.get(LAST_PAGE_KEY) == page:
        return
    st.session_state[LAST_PAGE_KEY] = page
    capture("$pageview", page=page, **{"$current_url": f"/{page}"})
