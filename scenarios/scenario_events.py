"""
IRIS Scenario Event System (Combined Phase 14).
Executes time-triggered dynamic events modifying environment state, actor trajectories,
surface hazards, weather parameters, and traffic density during simulation execution.
"""

from typing import List, Dict, Any, Optional
from simulation.environment import SimulationEnvironment
from simulation.entities import TrafficActor, SurfaceHazard, ActorType, HazardType, BehaviorMode
from scenarios.scenario_definition import ScenarioEvent, ScenarioEventType


class ScenarioEventEngine:
    """
    Evaluates and applies dynamic time-triggered events onto the active SimulationEnvironment.
    """

    def process_events(
        self,
        env: SimulationEnvironment,
        events: List[ScenarioEvent],
        current_time: float,
        dt: float = 0.05,
    ) -> List[ScenarioEvent]:
        """
        Processes events matching current_time interval. Returns list of executed events.
        """
        executed: List[ScenarioEvent] = []

        for evt in events:
            # Execute event if timestamp falls within current time step window [t - dt/2, t + dt/2]
            if abs(evt.timestamp - current_time) <= (dt / 1.99):
                self._apply_event(env, evt)
                executed.append(evt)

        return executed

    def _apply_event(self, env: SimulationEnvironment, evt: ScenarioEvent):
        """Dispatches event based on event_type."""
        p = evt.parameters

        if evt.event_type == ScenarioEventType.SPAWN_OBJECT:
            actor_id = p.get("actor_id", len(env.traffic_actors) + 500)
            a_type = p.get("actor_type", ActorType.CAR)
            x = p.get("x", 40.0)
            y = p.get("y", 0.0)
            heading = p.get("heading", 0.0)
            vel = p.get("velocity", 5.0)
            beh = p.get("behavior", BehaviorMode.CRUISE)
            actor = TrafficActor(actor_id, a_type, x, y, heading, vel, beh)
            env.traffic_actors.append(actor)

        elif evt.event_type == ScenarioEventType.MOVE_OBJECT:
            actor_id = p.get("actor_id")
            for actor in env.traffic_actors:
                if actor.actor_id == actor_id:
                    if "velocity" in p:
                        actor.velocity = float(p["velocity"])
                    if "x" in p:
                        actor.x = float(p["x"])
                    if "y" in p:
                        actor.y = float(p["y"])

        elif evt.event_type == ScenarioEventType.CHANGE_DIRECTION:
            actor_id = p.get("actor_id")
            for actor in env.traffic_actors:
                if actor.actor_id == actor_id:
                    if "heading" in p:
                        actor.heading = float(p["heading"])
                    if "behavior" in p:
                        actor.behavior = p["behavior"]

        elif evt.event_type == ScenarioEventType.ENTER_ROAD:
            actor_id = p.get("actor_id", len(env.traffic_actors) + 600)
            a_type = p.get("actor_type", ActorType.CATTLE)
            x = p.get("x", 45.0)
            y = p.get("y", -5.5)  # Entering from road shoulder (-Y)
            heading = p.get("heading", 1.5708)  # Moving across (+Y)
            vel = p.get("velocity", 1.5)
            actor = TrafficActor(actor_id, a_type, x, y, heading, vel, BehaviorMode.CROSSING)
            env.traffic_actors.append(actor)

        elif evt.event_type == ScenarioEventType.EXIT_ROAD:
            actor_id = p.get("actor_id")
            env.traffic_actors = [a for a in env.traffic_actors if a.actor_id != actor_id]

        elif evt.event_type == ScenarioEventType.CREATE_HAZARD:
            h_id = p.get("hazard_id", len(env.surface_hazards) + 800)
            h_type = p.get("hazard_type", HazardType.POTHOLE)
            hx = p.get("x", 50.0)
            hy = p.get("y", 0.0)
            hl = p.get("length", 2.0)
            hw = p.get("width", 2.0)
            sev = p.get("severity", 0.8)
            unc = p.get("uncertainty", 0.2)
            hazard = SurfaceHazard(h_id, h_type, hx, hy, hl, hw, sev, unc)
            env.surface_hazards.append(hazard)

        elif evt.event_type == ScenarioEventType.REMOVE_HAZARD:
            h_id = p.get("hazard_id")
            env.surface_hazards = [h for h in env.surface_hazards if h.hazard_id != h_id]

        elif evt.event_type == ScenarioEventType.CHANGE_HAZARD:
            h_id = p.get("hazard_id")
            for h in env.surface_hazards:
                if h.hazard_id == h_id:
                    if "severity" in p:
                        h.severity = float(p["severity"])
                    if "uncertainty" in p:
                        h.uncertainty = float(p["uncertainty"])
