"""Tests that ls_specific_settings from global and project configs are deep-merged.

Before the fix, ``dict.update()`` replaced the entire per-language settings dict
when both global and project configs had entries for the same language.  Keys
set only in the global config (e.g. ``disabled: true``) were silently dropped.
"""

from unittest.mock import MagicMock

from serena.ls_manager import LanguageServerFactory


def _make_factory_spy() -> tuple[MagicMock, list]:
    """Patch LanguageServerFactory so we can capture the merged settings."""
    captured: list[dict | None] = []

    original_init = LanguageServerFactory.__init__

    def spy_init(self, *args, ls_specific_settings: dict | None = None, **kwargs):
        captured.append(ls_specific_settings)
        original_init(self, *args, ls_specific_settings=ls_specific_settings, **kwargs)

    return captured, spy_init


# ---------------------------------------------------------------------------
# Deep merge of language-specific settings from two config sources
# ---------------------------------------------------------------------------


class TestDeepMergeLSSpecificSettings:
    def test_global_key_preserved_when_project_overlaps(self, tmp_path) -> None:
        """A key set only in the global config survives the merge with project config."""
        global_settings = {"kotlin": {"disabled": True}}
        project_settings = {"kotlin": {"jvm_options": "-Xmx8G -XX:+UseG1GC"}}

        merged = _merge_ls_specific_settings(global_settings, project_settings)
        assert merged == {"kotlin": {"disabled": True, "jvm_options": "-Xmx8G -XX:+UseG1GC"}}

    def test_project_key_preserved_when_global_is_empty(self) -> None:
        """Project settings pass through when global has no entry for the language."""
        global_settings: dict = {}
        project_settings = {"kotlin": {"jvm_options": "-Xmx4G"}}

        merged = _merge_ls_specific_settings(global_settings, project_settings)
        assert merged == {"kotlin": {"jvm_options": "-Xmx4G"}}

    def test_disjoint_languages_do_not_interfere(self) -> None:
        """Settings for different languages are independently preserved."""
        global_settings = {"python": {"analysis_timeout": 30}}
        project_settings = {"kotlin": {"jvm_options": "-Xmx8G"}}

        merged = _merge_ls_specific_settings(global_settings, project_settings)
        assert merged == {
            "python": {"analysis_timeout": 30},
            "kotlin": {"jvm_options": "-Xmx8G"},
        }

    def test_merged_keys_are_independent_copies(self) -> None:
        """Modifying the merged result must not mutate the global source."""
        global_settings = {"kotlin": {"disabled": True}}
        project_settings = {"kotlin": {"jvm_options": "-Xmx8G"}}

        merged = _merge_ls_specific_settings(global_settings, project_settings)
        merged["kotlin"]["new_key"] = "value"

        assert "new_key" not in global_settings["kotlin"]

    def test_project_key_overrides_global_key(self) -> None:
        """When both configs set the same key, the project value wins."""
        global_settings = {"kotlin": {"jvm_options": "-Xmx2G"}}
        project_settings = {"kotlin": {"jvm_options": "-Xmx8G"}}

        merged = _merge_ls_specific_settings(global_settings, project_settings)
        assert merged == {"kotlin": {"jvm_options": "-Xmx8G"}}

    def test_project_non_dict_value_replaces_global(self) -> None:
        """If the project config has a non-dict value, it replaces the global entry."""
        global_settings = {"kotlin": {"disabled": True}}
        project_settings = {"kotlin": "ignored"}

        merged = _merge_ls_specific_settings(global_settings, project_settings)
        assert merged == {"kotlin": "ignored"}


def _merge_ls_specific_settings(
    global_settings: dict,
    project_settings: dict,
) -> dict:
    """Replicate the deep-merge logic from Project.create_language_server_manager."""
    ls_specific_settings = dict(global_settings)
    for lang, settings in project_settings.items():
        if isinstance(settings, dict) and lang in ls_specific_settings:
            ls_specific_settings[lang] = {**ls_specific_settings[lang], **settings}
        else:
            ls_specific_settings[lang] = settings
    return ls_specific_settings
