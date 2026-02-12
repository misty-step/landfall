from __future__ import annotations

import sys
from unittest.mock import patch

from conftest import load_script_module

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
