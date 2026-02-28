import hashlib
import time
from typing import Optional, Tuple
import httpx
from bs4 import BeautifulSoup


async def check_site(url: str) -> dict:
    """
    Perform a single HTTP check on a URL.
    Returns dict with: is_up, status_code, response_time, content_hash, error_message
    """
    result = {
        "is_up": False,
        "status_code": None,
        "response_time": None,
        "content_hash": None,
        "error_message": None,
        "raw_text": None,
    }

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "SiteWatcher/1.0 (+https://sitewatcher.app)"},
        ) as client:
            response = await client.get(url)
            elapsed = time.monotonic() - start

        result["is_up"] = response.status_code < 500
        result["status_code"] = response.status_code
        result["response_time"] = round(elapsed, 3)

        # Extract visible text for content change detection
        try:
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "meta", "link"]):
                tag.decompose()
            visible_text = " ".join(soup.get_text(separator=" ").split())
            result["content_hash"] = hashlib.md5(visible_text.encode()).hexdigest()
            result["raw_text"] = visible_text[:5000]  # store first 5k chars for diff
        except Exception:
            result["content_hash"] = hashlib.md5(response.content).hexdigest()

    except httpx.TimeoutException:
        result["error_message"] = "Connection timed out"
    except httpx.ConnectError as e:
        result["error_message"] = f"Connection failed: {str(e)[:100]}"
    except httpx.TooManyRedirects:
        result["error_message"] = "Too many redirects"
    except Exception as e:
        result["error_message"] = f"Unexpected error: {str(e)[:100]}"

    return result
