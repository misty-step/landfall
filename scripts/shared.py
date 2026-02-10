#!/usr/bin/env python3
"""Shared script utilities.

Keep scripts tiny: centralize structured logging + HTTP retry.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import requests


RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, sort_keys=True, default=str))


def request_with_retry(
    logger: logging.Logger,
    session: "requests.Session",
    method: str,
    url: str,
    *,
    timeout: int,
    retries: int,
    retry_backoff: float,
    **kwargs: Any,
) -> "requests.Response":
    # Lazy import: some scripts only use logging helpers.
    import requests

    total_attempts = retries + 1
    method_upper = method.upper()

    for attempt in range(1, total_attempts + 1):
        try:
            response = session.request(method=method_upper, url=url, timeout=timeout, **kwargs)
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt >= total_attempts:
                raise

            delay = retry_backoff * (2 ** (attempt - 1))
            log_event(
                logger,
                logging.WARNING,
                "http_retry_exception",
                attempt=attempt,
                max_attempts=total_attempts,
                method=method_upper,
                url=url,
                wait_seconds=delay,
                error_type=type(exc).__name__,
            )
            time.sleep(delay)
            continue

        if response.status_code in RETRYABLE_STATUS_CODES and attempt < total_attempts:
            delay = retry_backoff * (2 ** (attempt - 1))
            log_event(
                logger,
                logging.WARNING,
                "http_retry_status",
                attempt=attempt,
                max_attempts=total_attempts,
                method=method_upper,
                url=url,
                status_code=response.status_code,
                wait_seconds=delay,
            )
            time.sleep(delay)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError("failed to receive HTTP response")

