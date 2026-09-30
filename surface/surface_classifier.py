"""
IRIS Surface Analyzer & Classifier Engine (Phase 5)
Provides rule-based classification for hazard severity, confidence, traversability state
(SAFE, CAUTION, RISKY, NON_TRAVERSABLE), spatial risk evaluation, and hidden hazard handling.
"""

from typing import Tuple, Dict, Any, Optional
from surface.surface_hazard import SurfaceHazard, SurfaceHazardType, TraversabilityState
from surface.config import (
    POTHOLE_MIN_DEPTH, POTHOLE_CRITICAL_DEPTH, POTHOLE_TRAVERSABLE_DEPTH,
    WATER_SHALLOW_DEPTH, WATER_MODERATE_DEPTH, WATER_DEEP_DEPTH, WATER_UNKNOWN_SURFACE_RISK_PENALTY,
    RAISED_SAFE_HEIGHT, RAISED_CRITICAL_HEIGHT,
    UNEVEN_LIGHT_ROUGHNESS, UNEVEN_MODERATE_ROUGHNESS, UNEVEN_SEVERE_ROUGHNESS,
    DEBRIS_SMALL_SIZE, DEBRIS_CRITICAL_SIZE,
    SURFACE_TYPE_BASE_RISK,
)


class SurfaceClassifier:
    """
    Evaluates and classifies road surface hazard severity, confidence, traversability, and spatial risk.
    """

    @staticmethod
    def calculate_severity(hazard_type: SurfaceHazardType, **kwargs) -> float:
        """
        Derives normalized hazard severity [0.0, 1.0] from physical dimensions and parameters.
        """
        depth = kwargs.get("depth", None)
        height = kwargs.get("height", None)
        roughness = kwargs.get("roughness", None)
        length = kwargs.get("length", 1.0)
        width = kwargs.get("width", 1.0)
        provided_severity = kwargs.get("severity", None)

        if hazard_type == SurfaceHazardType.POTHOLE:
            if depth is not None:
                if depth <= POTHOLE_MIN_DEPTH:
                    return 0.3
                elif depth >= POTHOLE_CRITICAL_DEPTH:
                    return 0.95
                else:
                    return 0.3 + 0.65 * ((depth - POTHOLE_MIN_DEPTH) / (POTHOLE_CRITICAL_DEPTH - POTHOLE_MIN_DEPTH))

        elif hazard_type == SurfaceHazardType.WATERLOGGING:
            if depth is not None:
                underlying_known = kwargs.get("underlying_surface_known", True)
                base_sev = min(1.0, depth / WATER_DEEP_DEPTH)
                if not underlying_known:
                    base_sev = min(1.0, base_sev + 0.25)
                return float(min(1.0, max(0.3, base_sev)))

        elif hazard_type == SurfaceHazardType.RAISED_SURFACE:
            if height is not None:
                if height <= RAISED_SAFE_HEIGHT:
                    return 0.4
                elif height >= RAISED_CRITICAL_HEIGHT:
                    return 0.95
                else:
                    return 0.4 + 0.55 * ((height - RAISED_SAFE_HEIGHT) / (RAISED_CRITICAL_HEIGHT - RAISED_SAFE_HEIGHT))

        elif hazard_type == SurfaceHazardType.UNEVEN_SURFACE:
            if roughness is not None:
                return float(min(1.0, max(0.1, roughness)))

        elif hazard_type == SurfaceHazardType.DEPRESSION:
            if depth is not None:
                return float(min(1.0, max(0.2, depth / 0.20)))

        elif hazard_type == SurfaceHazardType.DEBRIS:
            sz = max(length, width)
            if sz <= DEBRIS_SMALL_SIZE:
                return 0.4
            elif sz >= DEBRIS_CRITICAL_SIZE:
                return 0.9
            else:
                return 0.4 + 0.5 * ((sz - DEBRIS_SMALL_SIZE) / (DEBRIS_CRITICAL_SIZE - DEBRIS_SMALL_SIZE))

        elif hazard_type == SurfaceHazardType.CONSTRUCTION:
            return 0.85

        if provided_severity is not None:
            return float(min(1.0, max(0.0, provided_severity)))

        return 0.5

    @staticmethod
    def classify_traversability(hazard_type: SurfaceHazardType, severity: float, **kwargs) -> TraversabilityState:
        """
        Classifies physical traversability state (SAFE, CAUTION, RISKY, NON_TRAVERSABLE).
        Note: Risk and Traversability are evaluated separately.
        """
        depth = kwargs.get("depth", None)
        height = kwargs.get("height", None)
        length = kwargs.get("length", 1.0)
        width = kwargs.get("width", 1.0)
        underlying_known = kwargs.get("underlying_surface_known", True)

        if hazard_type == SurfaceHazardType.POTHOLE:
            d = depth if depth is not None else (severity * 0.15)
            if d >= POTHOLE_CRITICAL_DEPTH or severity >= 0.85:
                return TraversabilityState.NON_TRAVERSABLE
            elif d >= POTHOLE_TRAVERSABLE_DEPTH or severity >= 0.6:
                return TraversabilityState.RISKY
            else:
                return TraversabilityState.CAUTION

        elif hazard_type == SurfaceHazardType.WATERLOGGING:
            d = depth if depth is not None else (severity * 0.25)
            if d >= WATER_DEEP_DEPTH or severity >= 0.9:
                return TraversabilityState.NON_TRAVERSABLE
            elif not underlying_known or d >= WATER_MODERATE_DEPTH or severity >= 0.6:
                return TraversabilityState.RISKY
            else:
                return TraversabilityState.CAUTION

        elif hazard_type == SurfaceHazardType.RAISED_SURFACE:
            h = height if height is not None else (severity * 0.25)
            if h >= RAISED_CRITICAL_HEIGHT or severity >= 0.9:
                return TraversabilityState.NON_TRAVERSABLE
            elif h > RAISED_SAFE_HEIGHT or severity >= 0.6:
                return TraversabilityState.RISKY
            else:
                return TraversabilityState.CAUTION

        elif hazard_type == SurfaceHazardType.UNEVEN_SURFACE:
            roughness = kwargs.get("roughness", severity)
            if roughness >= UNEVEN_SEVERE_ROUGHNESS or severity >= 0.85:
                return TraversabilityState.NON_TRAVERSABLE
            elif roughness >= UNEVEN_MODERATE_ROUGHNESS or severity >= 0.5:
                return TraversabilityState.RISKY
            else:
                return TraversabilityState.CAUTION

        elif hazard_type == SurfaceHazardType.DEPRESSION:
            if severity >= 0.85:
                return TraversabilityState.NON_TRAVERSABLE
            elif severity >= 0.55:
                return TraversabilityState.RISKY
            else:
                return TraversabilityState.CAUTION

        elif hazard_type == SurfaceHazardType.DEBRIS:
            sz = max(length, width)
            if sz >= DEBRIS_CRITICAL_SIZE or severity >= 0.85:
                return TraversabilityState.NON_TRAVERSABLE
            elif sz >= DEBRIS_SMALL_SIZE or severity >= 0.55:
                return TraversabilityState.RISKY
            else:
                return TraversabilityState.CAUTION

        elif hazard_type == SurfaceHazardType.CONSTRUCTION:
            if severity >= 0.9:
                return TraversabilityState.NON_TRAVERSABLE
            else:
                return TraversabilityState.RISKY

        return TraversabilityState.CAUTION

    @staticmethod
    def calculate_surface_risk(hazard_type: SurfaceHazardType, severity: float, confidence: float, **kwargs) -> float:
        """
        Calculates spatial surface risk R_surface in [0.0, 1.0] derived from severity,
        confidence, and hidden surface status.
        """
        underlying_known = kwargs.get("underlying_surface_known", True)
        raw_risk = severity * confidence

        if hazard_type == SurfaceHazardType.WATERLOGGING and not underlying_known:
            raw_risk += WATER_UNKNOWN_SURFACE_RISK_PENALTY

        return float(min(1.0, max(0.0, raw_risk)))
