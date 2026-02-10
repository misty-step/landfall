from __future__ import annotations

import pytest

from conftest import load_script_module

update_floating_tag = load_script_module(
    "landfall_update_floating_tag", "scripts/update-floating-tag.py"
)


class TestParseMajorTag:
    def test_standard_semver(self):
        assert update_floating_tag.parse_major_tag("v1.2.3") == "v1"

    def test_high_major(self):
        assert update_floating_tag.parse_major_tag("v12.0.0") == "v12"

    def test_v0(self):
        assert update_floating_tag.parse_major_tag("v0.1.0") == "v0"

    def test_without_v_prefix(self):
        assert update_floating_tag.parse_major_tag("1.2.3") == "v1"

    def test_prerelease_suffix_ignored(self):
        assert update_floating_tag.parse_major_tag("v2.0.0-beta.1") == "v2"

    def test_invalid_tag_raises(self):
        with pytest.raises(ValueError, match="invalid semver tag"):
            update_floating_tag.parse_major_tag("not-a-tag")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="invalid semver tag"):
            update_floating_tag.parse_major_tag("")

    def test_partial_version_raises(self):
        with pytest.raises(ValueError, match="invalid semver tag"):
            update_floating_tag.parse_major_tag("v1.2")


class TestMain:
    def test_prints_major_tag(self, capsys):
        update_floating_tag.main(["--release-tag", "v3.1.4"])
        assert capsys.readouterr().out.strip() == "v3"

    def test_invalid_tag_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            update_floating_tag.main(["--release-tag", "bad"])
        assert exc_info.value.code == 1

    def test_missing_arg_exits(self):
        with pytest.raises(SystemExit):
            update_floating_tag.main([])
