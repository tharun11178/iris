"""
IRIS Ablation Configuration & Feature Toggles (Combined Phase 15).
Provides granular component toggles and pre-configured ablation presets for experimental evaluation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class AblationConfig:
    """
    Granular feature toggles for ablation studies.
    Architecture remains intact when toggles are disabled.
    """
    name: str = "FULL"
    enable_future_risk: bool = True
    enable_uncertainty: bool = True
    enable_safe_space: bool = True
    enable_surface_cost: bool = True
    enable_clearance_cost: bool = True
    enable_adaptive_replanning: bool = True
    enable_boundary_cost: bool = True
    enable_smoothness_cost: bool = True

    @classmethod
    def get_preset(cls, preset_name: str) -> "AblationConfig":
        """Factory for standardized ablation presets."""
        name = preset_name.upper()
        if name in ("FULL", "IRIS_FULL"):
            return cls(name="FULL")

        if name in ("WITHOUT_FUTURE_RISK", "NO_FUTURE_RISK"):
            return cls(
                name="WITHOUT_FUTURE_RISK",
                enable_future_risk=False
            )

        if name in ("WITHOUT_UNCERTAINTY", "NO_UNCERTAINTY"):
            return cls(
                name="WITHOUT_UNCERTAINTY",
                enable_uncertainty=False
            )

        if name in ("WITHOUT_SAFE_SPACE", "NO_SAFE_SPACE"):
            return cls(
                name="WITHOUT_SAFE_SPACE",
                enable_safe_space=False,
                enable_clearance_cost=False
            )

        if name in ("WITHOUT_SURFACE_COST", "NO_SURFACE_COST"):
            return cls(
                name="WITHOUT_SURFACE_COST",
                enable_surface_cost=False
            )

        if name in ("WITHOUT_ADAPTIVE_REPLANNING", "NO_ADAPTIVE_REPLANNING"):
            return cls(
                name="WITHOUT_ADAPTIVE_REPLANNING",
                enable_adaptive_replanning=False
            )

        # Default fallback
        return cls(name=preset_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "enable_future_risk": self.enable_future_risk,
            "enable_uncertainty": self.enable_uncertainty,
            "enable_safe_space": self.enable_safe_space,
            "enable_surface_cost": self.enable_surface_cost,
            "enable_clearance_cost": self.enable_clearance_cost,
            "enable_adaptive_replanning": self.enable_adaptive_replanning,
            "enable_boundary_cost": self.enable_boundary_cost,
            "enable_smoothness_cost": self.enable_smoothness_cost,
        }
