from __future__ import annotations


class EnvironmentalServiceError(Exception):
    """Base exception for environmental input service operations."""


class InvalidCoordinatesError(EnvironmentalServiceError, ValueError):
    """Raised when geographic coordinates are outside valid WGS 84 bounds."""


class InsufficientDataError(EnvironmentalServiceError):
    """Raised when required environmental inputs are missing or incomplete."""


class UnsupportedSimulationError(EnvironmentalServiceError):
    """Raised when a crop or requested output cannot be simulated."""
