"""Tests for LanguageServerManager.from_languages partial-success behavior.

Previously, a single failing language server killed all successfully-started
servers (fail-fast).  After the fix, the manager tolerates individual failures
and returns the successful subset — only raising when *all* servers fail.
"""

from unittest.mock import MagicMock

import pytest

from serena.ls_manager import LanguageServerFactory, LanguageServerManager, LanguageServerManagerInitialisationError
from solidlsp.ls_config import Language


class _FakeFactory(LanguageServerFactory):
    """A factory whose create_language_server returns pre-built mock servers.

    Each server has ``start()`` and ``is_running()`` patched.  Setting
    ``_fail_on`` to a language raises an exception during ``start()`` for that
    language.
    """

    def __init__(self, servers: dict[Language, MagicMock], fail_on: set[Language] | None = None) -> None:
        self._servers = servers
        self._fail_on = fail_on or set()

    def create_language_server(self, language: Language) -> MagicMock:
        ls = self._servers[language]
        if language in self._fail_on:
            ls.start.side_effect = RuntimeError(f"Simulated failure for {language.value}")
        else:
            ls.start.return_value = None
        ls.is_running.return_value = True
        return ls


def _make_mock_server(language: Language) -> MagicMock:
    ls = MagicMock()
    ls.language = language
    ls.is_running.return_value = False  # before start()
    return ls


# ---------------------------------------------------------------------------
# Partial success
# ---------------------------------------------------------------------------


def test_partial_success_one_fails_others_succeed() -> None:
    """When one LS fails, the manager returns with the successful ones."""
    rust = _make_mock_server(Language.RUST)
    python = _make_mock_server(Language.PYTHON)

    factory = _FakeFactory(
        {Language.RUST: rust, Language.PYTHON: python},
        fail_on={Language.PYTHON},
    )

    manager = LanguageServerManager.from_languages([Language.RUST, Language.PYTHON], factory)

    assert Language.RUST in manager._language_servers
    assert Language.PYTHON not in manager._language_servers
    assert len(manager._language_servers) == 1

    rust.start.assert_called_once()
    python.start.assert_called_once()
    # The failing server should have been stopped (factory creates it; start
    # raises; the exception is captured but the mock's stop is not called
    # because the original fail-fast code called stop on *successful* servers
    # before raising.  In partial-success mode neither the failed nor the
    # successful servers get an extra stop.)
    python.stop.assert_not_called()
    rust.stop.assert_not_called()


def test_all_succeed() -> None:
    """When all LS start successfully, the manager contains all of them."""
    rust = _make_mock_server(Language.RUST)
    python = _make_mock_server(Language.PYTHON)

    factory = _FakeFactory({Language.RUST: rust, Language.PYTHON: python})

    manager = LanguageServerManager.from_languages([Language.RUST, Language.PYTHON], factory)

    assert Language.RUST in manager._language_servers
    assert Language.PYTHON in manager._language_servers
    assert len(manager._language_servers) == 2


def test_all_fail_raises() -> None:
    """When every LS fails, LanguageServerManagerInitialisationError is raised."""
    rust = _make_mock_server(Language.RUST)
    python = _make_mock_server(Language.PYTHON)

    factory = _FakeFactory(
        {Language.RUST: rust, Language.PYTHON: python},
        fail_on={Language.RUST, Language.PYTHON},
    )

    with pytest.raises(LanguageServerManagerInitialisationError, match="All 2 language server"):
        LanguageServerManager.from_languages([Language.RUST, Language.PYTHON], factory)


def test_partial_success_preserves_working_manager() -> None:
    """A returned manager from partial success can answer get_active_languages."""
    rust = _make_mock_server(Language.RUST)
    kotlin = _make_mock_server(Language.KOTLIN)

    factory = _FakeFactory(
        {Language.RUST: rust, Language.KOTLIN: kotlin},
        fail_on={Language.KOTLIN},
    )

    manager = LanguageServerManager.from_languages([Language.RUST, Language.KOTLIN], factory)

    active = manager.get_active_languages()
    assert Language.RUST in active
    assert Language.KOTLIN not in active
