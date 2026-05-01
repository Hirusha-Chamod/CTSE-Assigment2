"""Wikipedia tool — owned by Reshan (Gap Analyst Agent).

Fetches a concise summary for an educational topic from the public
Wikipedia REST API. The Gap Analyst feeds the returned text directly
into its system prompt, so the tool deliberately strips the topic
of characters that would break the URL path.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import requests

from core.logger import get_logger

_logger = get_logger("tool.wiki")

_WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_DEFAULT_TIMEOUT = 10


class WikiToolError(RuntimeError):
    """Raised when the Wikipedia API is unreachable or returns an error."""


def fetch_wikipedia_summary(topic: str, timeout: int = _DEFAULT_TIMEOUT) -> Optional[str]:
    """Fetch the lead-paragraph summary of a topic from Wikipedia.

    Args:
        topic: Subject keyword. Spaces are URL-encoded automatically.
        timeout: HTTP timeout in seconds. Defaults to 10.

    Returns:
        The Wikipedia `extract` text on success.
        The string `"Topic not found on Wikipedia."` if the API responded
        successfully but had no extract for the topic.
        `None` if the input was empty or whitespace-only (caller should
        treat this as a usage error).

    Raises:
        WikiToolError: If the network request fails or the response is
            not valid JSON.
    """
    if not topic or not topic.strip():
        _logger.warning("fetch_wikipedia_summary called with empty topic")
        return None

    title = quote(topic.strip().replace(" ", "_"), safe="")
    url = _WIKI_SUMMARY_URL.format(title=title)
    _logger.info("GET %s", url)

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "EduMAS/1.0 (educational MAS coursework)"},
        )
    except requests.exceptions.RequestException as exc:
        _logger.error("Wikipedia request failed: %s", exc)
        raise WikiToolError(f"Could not reach Wikipedia: {exc}") from exc

    if response.status_code == 404:
        _logger.info("Wikipedia 404 for topic=%s", topic)
        return "Topic not found on Wikipedia."

    if response.status_code != 200:
        _logger.error(
            "Wikipedia returned %d: %s", response.status_code, response.text[:200]
        )
        raise WikiToolError(
            f"Wikipedia returned {response.status_code} for topic '{topic}'."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise WikiToolError(f"Wikipedia response was not JSON: {exc}") from exc

    extract = data.get("extract")
    if not extract:
        return "Topic not found on Wikipedia."
    return str(extract)


if __name__ == "__main__":
    print(fetch_wikipedia_summary("Photosynthesis"))
