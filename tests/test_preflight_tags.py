from __future__ import annotations

from unittest.mock import patch

from conftest import load_script_module

# Module-level import for @patch decorator resolution.
# The fixture in conftest.py handles session-scoped loading; this mirrors
# the pattern but is needed because @patch requires the module in sys.modules
# at decoration time (before fixtures run).
import sys

preflight_tags = load_script_module("landfall_preflight_tags", "scripts/preflight-tags.py")
sys.modules["landfall_preflight_tags"] = preflight_tags


class TestFilterVersionTags:
    def test_standard_semver(self):
        assert preflight_tags.filter_version_tags(["v1.0.0", "v2.1.3"]) == ["v1.0.0", "v2.1.3"]

    def test_ignores_non_version(self):
        assert preflight_tags.filter_version_tags(["some-tag", "v1.0.0", "latest"]) == ["v1.0.0"]

    def test_empty_list(self):
        assert preflight_tags.filter_version_tags([]) == []

    def test_no_version_tags(self):
        assert preflight_tags.filter_version_tags(["feature", "deploy-2024"]) == []

    def test_without_v_prefix(self):
        assert preflight_tags.filter_version_tags(["1.2.3", "v1.0.0"]) == ["1.2.3", "v1.0.0"]

    def test_prerelease(self):
        assert preflight_tags.filter_version_tags(["v1.0.0-beta.1"]) == ["v1.0.0-beta.1"]


class TestSemverKey:
    def test_standard_tag(self):
        assert preflight_tags._semver_key("v1.2.3") == (1, 2, 3)

    def test_no_v_prefix(self):
        assert preflight_tags._semver_key("1.2.3") == (1, 2, 3)

    def test_double_digit_major(self):
        assert preflight_tags._semver_key("v10.0.0") == (10, 0, 0)

    def test_non_version_returns_zero(self):
        assert preflight_tags._semver_key("not-a-tag") == (0, 0, 0)

    def test_sort_order(self):
        tags = ["v9.0.0", "v10.0.0", "v1.0.0", "v2.0.0"]
        result = sorted(tags, key=preflight_tags._semver_key)
        assert result == ["v1.0.0", "v2.0.0", "v9.0.0", "v10.0.0"]


class TestDiagnoseOrphanedTags:
    def test_no_tags_returns_none(self):
        assert preflight_tags.diagnose_orphaned_tags(all_tags=[], reachable_tags=[]) is None

    def test_no_version_tags_returns_none(self):
        assert preflight_tags.diagnose_orphaned_tags(
            all_tags=["feature", "deploy"],
            reachable_tags=[],
        ) is None

    def test_reachable_version_tags_returns_none(self):
        assert preflight_tags.diagnose_orphaned_tags(
            all_tags=["v1.0.0", "v1.1.0"],
            reachable_tags=["v1.0.0", "v1.1.0"],
        ) is None

    def test_partial_reachable_returns_none(self):
        """If at least one version tag is reachable, semantic-release is fine."""
        assert preflight_tags.diagnose_orphaned_tags(
            all_tags=["v1.0.0", "v2.0.0"],
            reachable_tags=["v2.0.0"],
        ) is None

    def test_orphaned_returns_diagnostic(self):
        result = preflight_tags.diagnose_orphaned_tags(
            all_tags=["v1.0.0", "v1.1.0", "v1.6.4"],
            reachable_tags=[],
        )
        assert result is not None
        assert result["count"] == 3
        assert result["earliest"] == "v1.0.0"
        assert result["latest"] == "v1.6.4"

    def test_orphaned_with_non_version_tags(self):
        """Non-version reachable tags don't count."""
        result = preflight_tags.diagnose_orphaned_tags(
            all_tags=["v1.0.0", "feature-tag"],
            reachable_tags=["feature-tag"],
        )
        assert result is not None
        assert result["count"] == 1

    def test_orphaned_single_tag(self):
        result = preflight_tags.diagnose_orphaned_tags(
            all_tags=["v1.0.0"],
            reachable_tags=[],
        )
        assert result is not None
        assert result["earliest"] == "v1.0.0"
        assert result["latest"] == "v1.0.0"

    def test_orphaned_semver_sort_not_lexicographic(self):
        """v10.0.0 should sort after v9.0.0, not before."""
        result = preflight_tags.diagnose_orphaned_tags(
            all_tags=["v10.0.0", "v9.0.0", "v1.0.0"],
            reachable_tags=[],
        )
        assert result is not None
        assert result["earliest"] == "v1.0.0"
        assert result["latest"] == "v10.0.0"


class TestMain:
    @patch("landfall_preflight_tags.get_reachable_tags")
    @patch("landfall_preflight_tags.get_all_tags")
    def test_no_tags_passes(self, mock_all, mock_reachable):
        mock_all.return_value = []
        mock_reachable.return_value = []
        assert preflight_tags.main() == 0

    @patch("landfall_preflight_tags.get_reachable_tags")
    @patch("landfall_preflight_tags.get_all_tags")
    def test_reachable_tags_passes(self, mock_all, mock_reachable):
        mock_all.return_value = ["v1.0.0", "v1.1.0"]
        mock_reachable.return_value = ["v1.0.0", "v1.1.0"]
        assert preflight_tags.main() == 0

    @patch("landfall_preflight_tags.get_current_branch")
    @patch("landfall_preflight_tags.get_reachable_tags")
    @patch("landfall_preflight_tags.get_all_tags")
    def test_orphaned_tags_fails(self, mock_all, mock_reachable, mock_branch, capsys):
        mock_all.return_value = ["v1.0.0", "v1.6.4"]
        mock_reachable.return_value = []
        mock_branch.return_value = "master"
        assert preflight_tags.main() == 1
        captured = capsys.readouterr()
        assert "Orphaned tag history" in captured.err
        assert "master" in captured.err
        assert "v1.6.4" in captured.err

    @patch("landfall_preflight_tags.get_current_branch")
    @patch("landfall_preflight_tags.get_reachable_tags")
    @patch("landfall_preflight_tags.get_all_tags")
    def test_orphaned_tags_suggests_fix(self, mock_all, mock_reachable, mock_branch, capsys):
        mock_all.return_value = ["v1.0.0", "v1.6.4"]
        mock_reachable.return_value = []
        mock_branch.return_value = "main"
        preflight_tags.main()
        captured = capsys.readouterr()
        assert "git merge" in captured.err
        assert "v1.6.4" in captured.err
        assert "main" in captured.err

    @patch("landfall_preflight_tags.get_reachable_tags")
    @patch("landfall_preflight_tags.get_all_tags")
    def test_only_non_version_tags_passes(self, mock_all, mock_reachable):
        mock_all.return_value = ["feature", "deploy-2024"]
        mock_reachable.return_value = []
        assert preflight_tags.main() == 0

    @patch("landfall_preflight_tags.get_current_branch")
    @patch("landfall_preflight_tags.get_reachable_tags")
    @patch("landfall_preflight_tags.get_all_tags")
    def test_orphaned_suggests_highest_semver_tag(self, mock_all, mock_reachable, mock_branch, capsys):
        """Merge suggestion should target the highest semver tag, not lexicographic."""
        mock_all.return_value = ["v1.0.0", "v10.0.0", "v9.0.0"]
        mock_reachable.return_value = []
        mock_branch.return_value = "master"
        preflight_tags.main()
        captured = capsys.readouterr()
        assert "v10.0.0" in captured.err
