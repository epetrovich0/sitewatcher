"""
AI-powered features for SiteWatcher — Groq.
Read-only statistics and answers. No site creation actions.
"""

import logging
import os
import statistics
from datetime import datetime, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not set")


async def _call_groq(
    prompt: str,
    max_tokens: int = 400,
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> Optional[str]:
    if not GROQ_API_KEY:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Groq Error {resp.status_code}")
                return None
    except Exception as e:
        logger.error(f"Groq exception: {e}")
        return None


# ==================== SYSTEM PROMPT ====================
_SYSTEM_CHATBOT = """You are a helpful SiteWatcher AI assistant in Telegram.

IMPORTANT LIMITS:
- You cannot add, create, or delete sites.
- Site creation is only available in the web interface.
- Reply with information only: statistics, site status, alert explanations, and similar facts.

Be polite, concise, and helpful. Reply in the user's language."""


# ==================== FUNCTIONS ====================

async def analyze_downtime(
    site_name: str,
    site_url: str,
    error_message: Optional[str],
    status_code: Optional[int],
    recent_incidents: list[dict],
) -> Optional[str]:
    incident_context = ""
    if recent_incidents:
        lines = [f"- {inc['checked_at']}: {inc.get('error', 'down')}" for inc in recent_incidents[-5:]]
        incident_context = "\nRecent incidents:\n" + "\n".join(lines)

    prompt = f"""Analyze the outage and explain it clearly:

Site: {site_name} ({site_url})
Error: {error_message or 'No response'}
Status: {status_code or 'N/A'}
{incident_context}

Reply briefly in 2-4 sentences."""

    return await _call_groq(prompt, max_tokens=250, temperature=0.65)


async def suggest_response_threshold(
    site_name: str,
    site_url: str,
    response_times: list,  # floats in seconds, is_up=True only
) -> dict:
    """
    Analyzes response time history and suggests a smart alert threshold.
    Stats are computed in Python — only 1 small Groq call for the human message.
    Returns: {"suggested_threshold": float|None, "message": str, "median_ms": int|None, "p95_ms": int|None}
    """
    if len(response_times) < 5:
        return {
            "suggested_threshold": None,
            "message": "Not enough data yet — at least 5 successful checks are required.",
            "median_ms": None,
            "p95_ms": None,
        }

    times_ms = [t * 1000 for t in response_times]
    median_ms = int(statistics.median(times_ms))

    sorted_ms = sorted(times_ms)
    p95_idx = min(int(len(sorted_ms) * 0.95), len(sorted_ms) - 1)
    p95_ms = int(sorted_ms[p95_idx])

    # Recommended: 2× P95 rounded to 100 ms, clamped to [500 ms, 30 s]
    suggested_ms = max(500, min(30_000, round(p95_ms * 2 / 100) * 100))
    suggested_sec = round(suggested_ms / 1000, 1)

    # One tiny Groq call just for the friendly phrasing
    prompt = (
        f"For site '{site_name}', response times are: median {median_ms}ms, P95 {p95_ms}ms. "
        f"Recommended alert threshold: {suggested_ms}ms. "
        "Write one friendly recommendation sentence that starts with 'Your site'. "
        "Do not use filler phrases like 'Sure' or 'Great'."
    )
    ai_message = await _call_groq(prompt, max_tokens=100, temperature=0.4)

    if not ai_message:
        ai_message = (
            f"Your site usually responds in {median_ms}ms, "
            f"I recommend a {suggested_ms}ms threshold (P95 {p95_ms}ms × 2)."
        )

    return {
        "suggested_threshold": suggested_sec,
        "message": ai_message,
        "median_ms": median_ms,
        "p95_ms": p95_ms,
    }


async def analyze_content_diff(
    site_name: str,
    site_url: str,
    old_text: str,
    new_text: str,
) -> Optional[str]:
    prompt = f"""Compare the changes on the page:

Site: {site_name} ({site_url})

OLD: {old_text[:2500]}
NEW: {new_text[:2500]}

Describe what changed in 2-4 sentences."""

    return await _call_groq(prompt, max_tokens=280)


async def handle_bot_chat(
    user_message: str,
    user,
    sites: list[dict],
    stats: Optional[dict] = None,
) -> tuple[str, Optional[dict]]:
    """Answers only, no create/delete actions."""
    
    tier = "Pro ⭐" if getattr(user, 'is_paid', False) else "Free"
    context = f"User: {user.email} | Plan: {tier} | Sites: {len(sites)}"

    prompt = f"""Context:
{context}

User message: {user_message}

Give a helpful answer. Do not suggest adding a site or try to create one."""

    response = await _call_groq(
        prompt, 
        max_tokens=450, 
        system=_SYSTEM_CHATBOT, 
        temperature=0.7
    )

    if not response:
        return "🤖 AI is currently unavailable. Use /sites or /status.", None

    # Strip any accidental ACTION tokens
    reply = response.replace("ACTION:ADD_SITE", "").replace("ACTION:DELETE_SITE", "").strip()
    
    return reply, None  # action is always None


# Weekly report stubs
async def generate_weekly_summary(*args, **kwargs):
    return None

async def generate_full_weekly_report(*args, **kwargs):
    return None