use crate::*;

fn scoping_pr(number: i64, title: &str, merged_at: Option<&str>) -> Value {
    json!({
        "number": number,
        "title": title,
        "user": {"login": "octocat"},
        "merged_at": merged_at,
    })
}

/// Commits with an explicit, far-future author/committer date so the gap between
/// the fixture's two tags is large and stable, independent of how fast the two
/// `git commit` calls run back-to-back on the test host.
fn commit_with_date(repo: &Path, message: &str, date: &str) -> Result<()> {
    let status = Command::new("git")
        .args(["commit", "-q", "-m", message])
        .current_dir(repo)
        .env("GIT_AUTHOR_DATE", date)
        .env("GIT_COMMITTER_DATE", date)
        .status()?;
    if !status.success() {
        return Err(format!("git commit failed for {message}").into());
    }
    Ok(())
}

/// Regression for the bitterblossom v1.79.0 incident: with no CHANGELOG.md,
/// `extract-prs` fell back to GitHub's "last 100 closed PRs" unfiltered, so a
/// release with one real commit shipped notes describing ~19 unrelated features.
/// `extract-prs` must scope PRs to the release's tag range instead.
pub(crate) fn scenario_extract_prs_scoped_to_release_range(tmp_root: &Path) -> Result<Value> {
    let repo = tmp_root.join("extract-prs-scoped-to-release-range");
    init_fixture_repo(&repo, "v1.0.0")?;
    fs::write(repo.join("feature.txt"), "second release\n")?;
    run_ok("git", ["add", "feature.txt"], &repo)?;
    commit_with_date(&repo, "feat: second release", "2030-06-01T00:00:00+00:00")?;
    run_ok("git", ["tag", "v1.1.0"], &repo)?;

    let previous = git_commit_date(&repo, "v1.0.0").ok_or("missing v1.0.0 commit date")?;
    let target = git_commit_date(&repo, "v1.1.0").ok_or("missing v1.1.0 commit date")?;

    let fake = FakeState {
        pull_requests: vec![
            scoping_pr(
                1,
                "ancient unrelated feature",
                Some(&(previous - chrono::Duration::days(30)).to_rfc3339()),
            ),
            scoping_pr(
                2,
                "the actual shipped fix",
                Some(&(previous + chrono::Duration::hours(1)).to_rfc3339()),
            ),
            scoping_pr(
                3,
                "merged after this release",
                Some(&(target + chrono::Duration::days(1)).to_rfc3339()),
            ),
            scoping_pr(4, "still open, never merged", None),
        ],
        ..Default::default()
    };
    let server = start_fake_server(fake)?;

    let output_file = repo.join("pr-changelog.md");
    let result = Command::new(current_exe())
        .args([
            "extract-prs",
            "--github-token",
            "token",
            "--repository",
            "owner/repo",
            "--release-tag",
            "v1.1.0",
            "--api-base-url",
            &server.url,
            "--repo-root",
        ])
        .arg(&repo)
        .args(["--output-file"])
        .arg(&output_file)
        .output()?;
    if !result.status.success() {
        return Err(String::from_utf8_lossy(&result.stderr).to_string().into());
    }
    let rendered = fs::read_to_string(&output_file)?;
    if !rendered.contains("the actual shipped fix") {
        return Err(format!("expected in-range PR in rendered changelog:\n{rendered}").into());
    }
    if rendered.contains("ancient unrelated feature") {
        return Err(format!("out-of-range PR leaked into rendered changelog:\n{rendered}").into());
    }
    if rendered.contains("merged after this release") {
        return Err(format!("future PR leaked into rendered changelog:\n{rendered}").into());
    }
    if rendered.contains("still open, never merged") {
        return Err(format!("unmerged PR leaked into rendered changelog:\n{rendered}").into());
    }

    Ok(json!({
        "output_file": output_file,
        "rendered_pr_count": rendered.lines().filter(|line| line.starts_with("- ")).count(),
    }))
}
