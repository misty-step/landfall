use crate::*;

/// Committer date of `rev` in the local checkout, or `None` if `rev` cannot be
/// resolved (e.g. a tag that doesn't exist locally yet).
pub(crate) fn git_commit_date(repo_root: &Path, rev: &str) -> Option<DateTime<Utc>> {
    let output = run_ok("git", ["log", "-1", "--format=%cI", rev], repo_root).ok()?;
    let trimmed = output.trim();
    if trimmed.is_empty() {
        return None;
    }
    DateTime::parse_from_rfc3339(trimmed)
        .ok()
        .map(|value| value.with_timezone(&Utc))
}

pub(crate) fn pr_merged_at(pr: &Value) -> Option<DateTime<Utc>> {
    pr["merged_at"]
        .as_str()
        .and_then(|value| DateTime::parse_from_rfc3339(value).ok())
        .map(|value| value.with_timezone(&Utc))
}

/// Keeps only PRs merged after `since` (exclusive) and at or before `until`
/// (inclusive). A `None` bound is unbounded on that side. PRs with no
/// `merged_at` (still open, or closed unmerged) are dropped.
pub(crate) fn filter_prs_by_range(
    prs: &[Value],
    since: Option<DateTime<Utc>>,
    until: Option<DateTime<Utc>>,
) -> Vec<Value> {
    prs.iter()
        .filter(|pr| {
            let Some(merged_at) = pr_merged_at(pr) else {
                return false;
            };
            since.is_none_or(|bound| merged_at > bound)
                && until.is_none_or(|bound| merged_at <= bound)
        })
        .cloned()
        .collect()
}
