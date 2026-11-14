"""Small, explicit error types so CLI failures are readable."""
from __future__ import annotations


class StudioError(Exception):
    """Base class for expected studio errors."""


class HighlightError(StudioError):
    """Invalid highlight selection."""


class LayoutError(StudioError):
    """Text cannot be fitted into the requested box."""


class TemplateError(StudioError):
    """Template or plan is malformed."""
