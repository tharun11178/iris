"""
IRIS Safe-Space Analyzer (Phase 11).
Integrates WorldModel drivable grid representation, ClearanceMap, FreeSpaceDetector,
and candidate safe corridors into a comprehensive SafeSpaceMap representation.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
import numpy as np

from world.world_model import WorldModel
from future_risk.future_risk_field import FutureRiskField
from safe_space.free_space import FreeSpaceRegion, FreeSpaceDetector
from safe_space.clearance import ClearanceMap
from safe_space.corridor import SafeCorridor


@dataclass
class SafeSpaceMap:
    """
    Exposes complete spatial negative-space, clearance, free regions, and candidate corridor information.
    """
    clearance_grid: Optional[np.ndarray] = None
    free_regions: List[FreeSpaceRegion] = field(default_factory=list)
    candidate_corridors: List[SafeCorridor] = field(default_factory=list)
    selected_corridor: Optional[SafeCorridor] = None
    num_drivable_cells: int = 0
    num_safe_cells: int = 0
    num_risky_cells: int = 0

    def get_clearance(self, row: int, col: int) -> float:
        """Returns clearance distance in meters at grid cell (row, col)."""
        if self.clearance_grid is None:
            return 0.0
        return float(self.clearance_grid[row, col])

    def get_region(self, region_id: int) -> Optional[FreeSpaceRegion]:
        """Returns FreeSpaceRegion by region ID."""
        for reg in self.free_regions:
            if reg.region_id == region_id:
                return reg
        return None

    def get_candidate_corridors(self) -> List[SafeCorridor]:
        """Returns list of candidate corridors."""
        return self.candidate_corridors

    def get_safe_cells(self, max_risk_threshold: float = 0.3) -> List[Tuple[int, int]]:
        """Returns list of (row, col) grid indices with low risk (< threshold)."""
        if self.clearance_grid is None:
            return []
        safe_list = []
        rows, cols = self.clearance_grid.shape
        for r in range(rows):
            for c in range(cols):
                if self.clearance_grid[r, c] > 0.5:
                    safe_list.append((r, c))
        return safe_list


class SafeSpaceAnalyzer:
    """
    Analyzes environment and future risk field to generate a populated SafeSpaceMap.
    """

    def __init__(self):
        self.clearance_model = ClearanceMap()
        self.free_space_detector = FreeSpaceDetector()

    def analyze(
        self,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
    ) -> SafeSpaceMap:
        """
        Executes clearance mapping and free-space component detection.
        """
        # 1. Compute Clearance Map
        clearance_grid = self.clearance_model.compute_clearance(world_model)

        # Extract risk matrix (t=0.0s or peak matrix) if available
        risk_matrix = None
        if future_risk_field is not None:
            risk_matrix = future_risk_field.peak_risk_matrix
        elif hasattr(world_model, "future_risk_field") and world_model.future_risk_field is not None:
            risk_matrix = world_model.future_risk_field.peak_risk_matrix

        # 2. Detect Connected Free-Space Regions
        regions = self.free_space_detector.detect_regions(world_model, clearance_grid, risk_matrix)

        # 3. Calculate cell counts
        drivable_cnt = 0
        safe_cnt = 0
        risky_cnt = 0

        num_rows, num_cols = world_model.grid.num_rows, world_model.grid.num_cols
        for r in range(num_rows):
            for c in range(num_cols):
                cell = world_model.grid.cells[r][c]
                if cell.is_drivable:
                    drivable_cnt += 1
                    c_val = clearance_grid[r, c]
                    r_val = risk_matrix[r, c] if risk_matrix is not None else 0.0
                    if c_val >= 1.0 and r_val < 0.4:
                        safe_cnt += 1
                    else:
                        risky_cnt += 1

        space_map = SafeSpaceMap(
            clearance_grid=clearance_grid,
            free_regions=regions,
            candidate_corridors=[],
            selected_corridor=None,
            num_drivable_cells=drivable_cnt,
            num_safe_cells=safe_cnt,
            num_risky_cells=risky_cnt,
        )
        return space_map
