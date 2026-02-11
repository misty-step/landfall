from __future__ import annotations

import argparse

import pytest


def test_validate_args_accepts_valid_inputs(close_resolved_failures):
    # Arrange
    args = argparse.Namespace(
        github_token="token",
        repository="octo/example",
        release_tag="v2.0.0",
        api_base_url="https://api.github.com",
        timeout=5,
        retries=2,
        retry_backoff=1.0,
        log_level="INFO",
    )

    # Act / Assert — no exception raised
    close_resolved_failures.validate_args(args)


@pytest.mark.parametrize(
    "override, match",
    [
        ({"github_token": ""}, "github-token must be non-empty"),
        ({"repository": "invalid"}, "repository must match owner/repo"),
        ({"release_tag": ""}, "release-tag must be non-empty"),
        ({"timeout": 0}, "timeout must be greater than zero"),
        ({"retries": -1}, "retries cannot be negative"),
        ({"retry_backoff": -0.5}, "retry-backoff cannot be negative"),
        ({"api_base_url": "ftp://bad"}, "api-base-url must start with http"),
    ],
)
def test_validate_args_rejects_invalid(close_resolved_failures, override, match):
    # Arrange
    defaults = dict(
        github_token="token",
        repository="octo/example",
        release_tag="v2.0.0",
        api_base_url="https://api.github.com",
        timeout=5,
        retries=2,
        retry_backoff=1.0,
        log_level="INFO",
    )
    defaults.update(override)
    args = argparse.Namespace(**defaults)

    # Act / Assert
    with pytest.raises(ValueError, match=match):
        close_resolved_failures.validate_args(args)


def test_find_open_failure_issues_filters_by_title(close_resolved_failures, request_session_factory):
    # Arrange
    from conftest import FakeResponse

    issues_payload = [
        {"number": 10, "title": "[Landfall] Synthesis failed for v1.0.0"},
        {"number": 11, "title": "Unrelated bug"},
        {"number": 12, "title": "[Landfall] Synthesis failed for v1.1.0"},
    ]
    session = request_session_factory([FakeResponse(status_code=200, json_data=issues_payload)])

    # Act
    result = close_resolved_failures.find_open_failure_issues(
        api_base_url="https://api.github.test",
        repository="octo/example",
        headers={"Authorization": "Bearer tok"},
        timeout=5,
        retries=0,
        retry_backoff=0,
        session=session,
    )

    # Assert
    assert len(result) == 2
    assert result[0]["number"] == 10
    assert result[1]["number"] == 12


def test_find_open_failure_issues_returns_empty_when_no_matches(
    close_resolved_failures, request_session_factory
):
    # Arrange
    from conftest import FakeResponse

    session = request_session_factory(
        [FakeResponse(status_code=200, json_data=[{"number": 1, "title": "Normal issue"}])]
    )

    # Act
    result = close_resolved_failures.find_open_failure_issues(
        api_base_url="https://api.github.test",
        repository="octo/example",
        headers={},
        timeout=5,
        retries=0,
        retry_backoff=0,
        session=session,
    )

    # Assert
    assert result == []


def test_find_open_failure_issues_sends_correct_request(
    close_resolved_failures, request_session_factory
):
    # Arrange
    from conftest import FakeResponse

    session = request_session_factory([FakeResponse(status_code=200, json_data=[])])

    # Act
    close_resolved_failures.find_open_failure_issues(
        api_base_url="https://api.github.test",
        repository="octo/example",
        headers={"Authorization": "Bearer tok"},
        timeout=10,
        retries=0,
        retry_backoff=0,
        session=session,
    )

    # Assert
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://api.github.test/repos/octo/example/issues"
    assert call["kwargs"]["params"] == {"state": "open", "per_page": 100}


def test_close_issue_with_comment_posts_comment_and_closes(
    close_resolved_failures, request_session_factory
):
    # Arrange
    from conftest import FakeResponse

    session = request_session_factory([
        FakeResponse(status_code=201, json_data={}),  # comment
        FakeResponse(status_code=200, json_data={}),  # close
    ])

    # Act
    close_resolved_failures.close_issue_with_comment(
        api_base_url="https://api.github.test",
        repository="octo/example",
        issue_number=42,
        release_tag="v2.0.0",
        headers={"Authorization": "Bearer tok"},
        timeout=5,
        retries=0,
        retry_backoff=0,
        session=session,
    )

    # Assert — two calls: comment then close
    assert len(session.calls) == 2

    comment_call = session.calls[0]
    assert comment_call["method"] == "POST"
    assert comment_call["url"].endswith("/repos/octo/example/issues/42/comments")
    body = comment_call["kwargs"]["json"]["body"]
    assert "v2.0.0" in body
    assert "resolved" in body

    close_call = session.calls[1]
    assert close_call["method"] == "PATCH"
    assert close_call["url"].endswith("/repos/octo/example/issues/42")
    assert close_call["kwargs"]["json"]["state"] == "closed"
    assert close_call["kwargs"]["json"]["state_reason"] == "completed"
