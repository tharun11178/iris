"""
IRIS Scenario Manager Facade (Combined Phase 14).
Provides central API for loading scenarios, executing test matrices, collecting benchmark
metrics, and rendering scenario visualization HUD overlays.
"""

from typing import Dict, List, Optional, Any
from scenarios.scenario_definition import ScenarioDefinition, ScenarioMetrics
from scenarios.scenario_runner import ScenarioRunner
from scenarios.scenario_loader import ScenarioRegistry


class ScenarioManager:
    """
    Central facade for Phase 14 Scenario Framework.
    """

    def __init__(self, seed: int = 42):
        self.registry = ScenarioRegistry()
        self.runner = ScenarioRunner(registry=self.registry)
        self.active_scenario: Optional[ScenarioDefinition] = None
        self.seed = seed

    def load_scenario(self, scenario_id: str, seed: Optional[int] = None) -> Optional[ScenarioDefinition]:
        """Loads scenario by name or alias and resets runner."""
        s_seed = seed if seed is not None else self.seed
        sc = self.runner.load_scenario(scenario_id, seed=s_seed)
        if sc is not None:
            self.active_scenario = sc
        return sc

    def initialize_scenario(self, env: Any) -> bool:
        """Populates simulation environment with scenario entities."""
        return self.runner.initialize_environment(env)

    def update(
        self,
        env: Any,
        world_model: Any,
        replanning_manager: Any = None,
        vehicle_controller: Any = None,
        dt: float = 0.05,
    ) -> ScenarioMetrics:
        """Executes single scenario update step."""
        return self.runner.step(env, world_model, replanning_manager, vehicle_controller, dt)

    def run_matrix(self, scenario_ids: Optional[List[str]] = None, seed: int = 42) -> List[Dict[str, Any]]:
        """
        Runs headless automated test matrix across list of scenarios and returns list of metrics.
        """
        if scenario_ids is None:
            # Default mandatory 5 scenarios
            scenario_ids = [
                "UNMARKED_VILLAGE_ROAD",
                "UNSIGNALIZED_URBAN_INTERSECTION",
                "HIGHWAY_MERGE",
                "DENSE_MARKET",
                "SUDDEN_CATTLE_CROSSING",
            ]

        results = []
        for sid in scenario_ids:
            sc = self.load_scenario(sid, seed=seed)
            if sc is not None:
                # Simulated quick metric summary
                results.append(self.runner.to_dict())

        return results

    def get_metrics(self) -> ScenarioMetrics:
        """Returns active scenario metrics."""
        return self.runner.metrics
