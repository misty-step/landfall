use super::*;

fn pr(number: i64, title: &str, merged_at: Option<&str>) -> Value {
    json!({
        "number": number,
        "title": title,
        "user": {"login": "octocat"},
        "merged_at": merged_at,
    })
}

#[test]
fn filter_prs_by_range_excludes_out_of_range_merges() {
    let since = DateTime::parse_from_rfc3339("2024-01-10T00:00:00Z")
        .unwrap()
        .with_timezone(&Utc);
    let until = DateTime::parse_from_rfc3339("2024-02-01T00:00:00Z")
        .unwrap()
        .with_timezone(&Utc);
    let prs = vec![
        pr(1, "ancient unrelated feature", Some("2023-11-01T00:00:00Z")),
        pr(2, "in range fix", Some("2024-01-15T00:00:00Z")),
        pr(3, "future unrelated feature", Some("2024-03-01T00:00:00Z")),
        pr(4, "still open", None),
    ];

    let filtered = filter_prs_by_range(&prs, Some(since), Some(until));

    let titles: Vec<_> = filtered
        .iter()
        .map(|pr| pr["title"].as_str().unwrap())
        .collect();
    assert_eq!(titles, vec!["in range fix"]);
}

#[test]
fn filter_prs_by_range_with_no_previous_tag_is_unbounded_below() {
    let until = DateTime::parse_from_rfc3339("2024-02-01T00:00:00Z")
        .unwrap()
        .with_timezone(&Utc);
    let prs = vec![
        pr(1, "first ever release commit", Some("2020-01-01T00:00:00Z")),
        pr(2, "still too new", Some("2024-03-01T00:00:00Z")),
    ];

    let filtered = filter_prs_by_range(&prs, None, Some(until));

    let titles: Vec<_> = filtered
        .iter()
        .map(|pr| pr["title"].as_str().unwrap())
        .collect();
    assert_eq!(titles, vec!["first ever release commit"]);
}

#[test]
fn git_commit_date_reads_tag_commit_and_none_for_missing_tag() {
    let repo = tempfile::tempdir().unwrap();
    init_fixture_repo(repo.path(), "v1.0.0").unwrap();

    assert!(git_commit_date(repo.path(), "v1.0.0").is_some());
    assert!(git_commit_date(repo.path(), "v9.9.9-does-not-exist").is_none());
}

// The end-to-end regression pinning "extract-prs must not leak closed PRs outside
// the release's tag range" lives in the replay harness as
// `scenario_extract_prs_scoped_to_release_range` (replay/provider_scenarios), since
// it needs to exercise `extract-prs` as a real subprocess against a fake GitHub
// server, which only works via `landmark replay-action`, not `cargo test`'s
// harness binary.
