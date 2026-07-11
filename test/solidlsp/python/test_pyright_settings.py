"""Policy unit tests for PyrightServer LS-specific settings.

These do not start Pyright; they only verify how ``ls_specific_settings.python`` values are resolved,
following the same style as ``test/solidlsp/java/test_jdtls_path_resolution.py``.
"""

from __future__ import annotations

from solidlsp.language_servers.pyright_server import DEFAULT_ANALYSIS_TIMEOUT, PyrightServer
from solidlsp.settings import SolidLSPSettings


def _custom(settings: dict) -> SolidLSPSettings.CustomLSSettings:
    return SolidLSPSettings.CustomLSSettings(settings)


class TestPyrightAnalysisTimeout:
    """The initial-analysis wait must default to DEFAULT_ANALYSIS_TIMEOUT and honor an override."""

    def test_default_when_unset(self) -> None:
        assert PyrightServer._resolve_analysis_timeout(_custom({})) == DEFAULT_ANALYSIS_TIMEOUT
        # Guard the documented default so it cannot silently regress to the old 5s.
        assert DEFAULT_ANALYSIS_TIMEOUT == 30.0

    def test_override_is_honored(self) -> None:
        assert PyrightServer._resolve_analysis_timeout(_custom({"analysis_timeout": 60})) == 60.0

    def test_override_coerced_to_float(self) -> None:
        # Config values may arrive as strings (YAML/JSON); they must be coerced to float.
        result = PyrightServer._resolve_analysis_timeout(_custom({"analysis_timeout": "12.5"}))
        assert isinstance(result, float)
        assert result == 12.5
