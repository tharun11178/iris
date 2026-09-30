"""
IRIS FastAPI Application & Autonomous Driving Backend Engine.
Unified 16-Phase closed-loop autonomous driving intelligence system.
"""

import os
import sys
import json
import time
import math
import asyncio
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add root directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.iris_system import IRISSystem
from simulation.vehicle_safety import VehicleSafetyChecker, VehicleCondition
from backend.database import save_experiment, list_experiments, get_benchmarks_summary

app = FastAPI(
    title="IRIS — Indian Road Intelligence & Safe-Space Planner",
    description="Adaptive Path Planning and Collision Avoidance for Autonomous Vehicles on Unstructured Indian Roads (SIH26037)",
    version="2.0.0"
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SystemManager:
    def __init__(self):
        self.scenario_name = "SUDDEN_CATTLE_CROSSING"
        self.planner_mode = "iris"
        self.seed = 42
        self.is_paused = False
        self.fps_target = 20.0
        self.speed_multiplier = 1.0
        self.is_demo_mode = False
        self.demo_step_index = 0
        self.demo_scenarios = [
            "UNMARKED_VILLAGE_ROAD",
            "UNSIGNALIZED_URBAN_INTERSECTION",
            "SUDDEN_CATTLE_CROSSING",
            "HIGHWAY_MERGE",
            "DENSE_MARKET"
        ]
        self.lock = threading.Lock()
        
        self.system: Optional[IRISSystem] = None
        self._init_system()

        # Background Simulation Worker Thread
        self.running = True
        self.sim_thread = threading.Thread(target=self._sim_loop, daemon=True)
        self.sim_thread.start()

    def _init_system(self):
        with self.lock:
            if self.system is not None:
                try:
                    self.system.running = False
                except Exception:
                    pass
            self.system = IRISSystem({
                "scenario": self.scenario_name,
                "planner": self.planner_mode,
                "mode": "simulation",
                "seed": self.seed,
                "headless": True,
                "duration": 3600.0
            })
            self.system.initialize()

    def _sim_loop(self):
        while self.running:
            t_start = time.perf_counter()
            if not self.is_paused and self.system and self.system.running:
                with self.lock:
                    self.system.step()
                    if self.system.metrics_tracker.metrics.scenario_completed:
                        if self.is_demo_mode:
                            self.demo_step_index = (self.demo_step_index + 1) % len(self.demo_scenarios)
                            self.scenario_name = self.demo_scenarios[self.demo_step_index]
                        time.sleep(1.0)
                        self._init_system()

            elapsed = time.perf_counter() - t_start
            target_dt = max(0.01, (1.0 / (self.fps_target * self.speed_multiplier)) - elapsed)
            time.sleep(target_dt)

    def get_full_state(self) -> Dict[str, Any]:
        with self.lock:
            if not self.system or not self.system.env:
                return {"status": "initializing"}

            env = self.system.env
            ego = env.ego_vehicle
            wm = self.system.world_model
            metrics = self.system.metrics_tracker.metrics
            replanning = self.system.replanning_manager
            converter = wm.converter

            # Vehicle footprint corners
            corners = ego.get_corners() if hasattr(ego, "get_corners") else []
            footprint_pts = [[round(p[0], 2), round(p[1], 2)] for p in corners]

            # Clearances and TTC
            left_clr = max(0.0, (env.road.width / 2.0) - ego.y - (ego.width / 2.0))
            right_clr = max(0.0, ego.y - (-env.road.width / 2.0) - (ego.width / 2.0))
            min_road_clr = min(left_clr, right_clr)
            min_clr = env.get_minimum_clearance()

            ttc = 999.0
            nearest_obs_dist = 999.0
            if ego.velocity > 0.1:
                for a in getattr(env, "traffic_actors", []):
                    d = math.hypot(a.x - ego.x, a.y - ego.y) - (ego.length + a.length) / 2.0
                    if d < nearest_obs_dist:
                        nearest_obs_dist = d
                    if a.x > ego.x and abs(a.y - ego.y) < 2.5:
                        cand_ttc = max(0.0, (a.x - ego.x) / max(0.1, ego.velocity))
                        if cand_ttc < ttc:
                            ttc = cand_ttc

            # Vehicle Condition evaluation
            condition_str = "NORMAL"
            if hasattr(ego, "condition"):
                condition_val = ego.condition
                condition_str = condition_val.value if hasattr(condition_val, "value") else str(condition_val)
            else:
                if not env.road.is_within_road(ego.x, ego.y):
                    condition_str = "OFF_ROAD"
                elif min_clr < 0.6 or ttc < 1.5:
                    condition_str = "COLLISION_RISK"
                elif min_clr < 1.5 or float(metrics.peak_risk) > 0.6:
                    condition_str = "CAUTION"

            # Lookahead and Waypoint
            lookahead_pt = [round(ego.x + 5.0, 2), round(ego.y, 2)]
            if hasattr(ego, "lookahead_point") and ego.lookahead_point:
                # Convert from world to sim if needed
                lx, ly = ego.lookahead_point
                if ly > 2.0 and ly > env.road.width / 2.0:
                    lx, ly = converter.world_to_sim(lx, ly)
                lookahead_pt = [round(lx, 2), round(ly, 2)]

            current_wp = [round(ego.x + 10.0, 2), 0.0]

            # Ego vehicle state
            ego_data = {
                "x": round(ego.x, 2),
                "y": round(ego.y, 2),
                "heading": round(ego.heading, 3),
                "heading_deg": round(math.degrees(ego.heading), 1),
                "velocity": round(ego.velocity, 2),
                "speed_kmh": round(ego.velocity * 3.6, 1),
                "target_speed": round(getattr(ego, "target_speed", 10.0), 2),
                "target_speed_kmh": round(getattr(ego, "target_speed", 10.0) * 3.6, 1),
                "steering_angle": round(getattr(ego, "steering_angle", 0.0), 3),
                "steering_angle_deg": round(math.degrees(getattr(ego, "steering_angle", 0.0)), 1),
                "steering_command": round(getattr(ego, "steering_angle", 0.0) / 0.5, 2),
                "acceleration": round(getattr(ego, "acceleration", 0.0), 2),
                "brake": round(max(0.0, -getattr(ego, "acceleration", 0.0)), 2),
                "length": ego.length,
                "width": ego.width,
                "clearance": round(min_clr, 2),
                "left_clearance": round(left_clr, 2),
                "right_clearance": round(right_clr, 2),
                "min_road_clearance": round(min_road_clr, 2),
                "min_obstacle_clearance": round(max(0.0, nearest_obs_dist), 2),
                "ttc": round(ttc, 2),
                "condition": condition_str,
                "is_safe": bool(env.road.is_within_road(ego.x, ego.y) and min_clr > 0.4),
                "decision_state": getattr(self.system, "current_decision_state", getattr(ego, "decision_state", "NORMAL_DRIVING")),
                "lookahead_point": lookahead_pt,
                "current_waypoint": current_wp,
                "footprint": footprint_pts,
                "safety_hold": bool(condition_str == "SAFETY_HOLD"),
            }

            # Active path in simulation coordinates (converted from world grid waypoints)
            path_points = []
            if ego.current_path:
                w_pts = getattr(ego.current_path, "world_points", getattr(ego.current_path, "waypoints", []))
                for pt in w_pts:
                    sx, sy = converter.world_to_sim(pt[0], pt[1])
                    path_points.append([round(sx, 2), round(sy, 2)])
            ego_data["path"] = path_points

            # Traffic actors
            actors_data = []
            for actor in getattr(env, "traffic_actors", []):
                hypotheses = []
                pred_set = getattr(wm, "prediction_set", None)
                if pred_set:
                    pred = None
                    if hasattr(pred_set, "get_prediction_by_track_id"):
                        pred = pred_set.get_prediction_by_track_id(actor.actor_id)
                    elif hasattr(pred_set, "predictions"):
                        for p in pred_set.predictions:
                            if getattr(p, "track_id", None) == actor.actor_id:
                                pred = p
                                break
                    if pred and hasattr(pred, "hypotheses"):
                        for hyp in pred.hypotheses:
                            traj = getattr(hyp, "trajectory", [])
                            hyp_pts = []
                            for pt in traj:
                                sx, sy = converter.world_to_sim(pt[0], pt[1]) if pt[1] > 2.0 else (pt[0], pt[1])
                                hyp_pts.append([round(sx, 2), round(sy, 2)])
                            h_type = getattr(hyp, "hypothesis_type", "DEFAULT")
                            hypotheses.append({
                                "type": h_type.name if hasattr(h_type, "name") else str(h_type),
                                "probability": round(getattr(hyp, "probability", 0.5), 2),
                                "points": hyp_pts
                            })

                ellipse_data = None
                unc_set = getattr(wm, "uncertainty_set", None)
                if unc_set:
                    unc = None
                    if hasattr(unc_set, "get_uncertainty_by_track_id"):
                        unc = unc_set.get_uncertainty_by_track_id(actor.actor_id)
                    elif hasattr(unc_set, "regions"):
                        for r in unc_set.regions:
                            if getattr(r, "track_id", None) == actor.actor_id:
                                unc = r
                                break
                    if unc and hasattr(unc, "current_ellipse") and unc.current_ellipse:
                        el = unc.current_ellipse
                        ellipse_data = {
                            "semi_major": round(el.semi_major, 2),
                            "semi_minor": round(el.semi_minor, 2),
                            "angle": round(getattr(el, "orientation", 0.0), 2),
                            "total_uncertainty": round(getattr(unc, "total_uncertainty", 0.5), 2)
                        }

                a_type = getattr(actor, "actor_type", "CAR")
                corners_actor = actor.get_corners() if hasattr(actor, "get_corners") else []
                actors_data.append({
                    "id": actor.actor_id,
                    "type": a_type.name if hasattr(a_type, "name") else str(a_type),
                    "x": round(actor.x, 2),
                    "y": round(actor.y, 2),
                    "heading": round(actor.heading, 3),
                    "speed": round(actor.velocity, 2),
                    "length": getattr(actor, "length", 4.0),
                    "width": getattr(actor, "width", 1.8),
                    "corners": [[round(p[0], 2), round(p[1], 2)] for p in corners_actor],
                    "hypotheses": hypotheses,
                    "uncertainty": ellipse_data
                })

            # Surface Hazards
            hazards_data = []
            for h in getattr(env, "surface_hazards", []):
                h_type = getattr(h, "hazard_type", "POTHOLE")
                hazards_data.append({
                    "id": h.hazard_id,
                    "type": h_type.name if hasattr(h_type, "name") else str(h_type),
                    "x": round(h.x, 2),
                    "y": round(h.y, 2),
                    "length": round(getattr(h, "length", 2.0), 2),
                    "width": round(getattr(h, "width", 2.0), 2),
                    "severity": round(getattr(h, "severity", 0.5), 2),
                    "is_traversable": getattr(h, "is_traversable", True)
                })

            # Safe Space Corridors in simulation frame
            corridors = []
            if hasattr(self.system, "safe_space_planner") and self.system.safe_space_planner.last_result:
                res = self.system.safe_space_planner.last_result
                candidates = getattr(res, "candidate_paths", getattr(res, "candidates", []))
                for c in candidates[:6]:
                    c_line = getattr(c, "centerline", getattr(c, "trajectory", []))
                    pts_sim = []
                    for p in c_line:
                        sx, sy = converter.world_to_sim(p[0], p[1]) if p[1] > 2.0 else (p[0], p[1])
                        pts_sim.append([round(sx, 2), round(sy, 2)])
                    corridors.append({
                        "points": pts_sim,
                        "score": round(getattr(c, "total_score", 0.0), 3),
                        "is_selected": bool(getattr(c, "is_valid", False) and (c == getattr(res, "selected_corridor", None))),
                        "clearance": round(getattr(c, "min_clearance", 2.0), 2)
                    })

            # Replanning Events
            events_data = []
            if replanning and replanning.event_log:
                for ev in replanning.event_log[-12:]:
                    events_data.append({
                        "timestamp": round(getattr(ev, "timestamp", 0.0), 2),
                        "reason": str(getattr(ev, "trigger_reason", "REPLAN")),
                        "latency_ms": round(getattr(ev, "replan_latency_ms", 0.0), 1),
                        "risk_before": round(getattr(ev, "risk_before", 0.0), 2),
                        "risk_after": round(getattr(ev, "risk_after", 0.0), 2),
                    })

            # Downsampled Risk Heatmap
            risk_matrix = []
            if self.system.risk_engine and self.system.risk_engine.risk_grid:
                rg = self.system.risk_engine.risk_grid.total_risk
                r_step = max(1, rg.shape[0] // 20)
                c_step = max(1, rg.shape[1] // 60)
                sub_rg = rg[::r_step, ::c_step]
                risk_matrix = [[round(float(v), 2) for v in row] for row in sub_rg]

            return {
                "status": "running",
                "sim_time": round(env.sim_time, 2),
                "step_count": self.system.step_count,
                "is_paused": self.is_paused,
                "is_demo_mode": self.is_demo_mode,
                "scenario_id": self.scenario_name,
                "planner_mode": self.planner_mode,
                "road": {
                    "length": env.road.length,
                    "width": env.road.width,
                    "safe_margin": 0.5,
                    "safe_width": env.road.width - 1.0,
                    "lanes": getattr(env.road, "num_lanes", 2),
                },
                "ego": ego_data,
                "actors": actors_data,
                "hazards": hazards_data,
                "corridors": corridors,
                "events": events_data,
                "risk": {
                    "peak_future_risk": round(float(metrics.peak_risk), 3),
                    "current_risk": round(float(self.system.risk_engine.risk_grid.get_max_risk() if self.system.risk_engine.risk_grid else 0.0), 3)
                },
                "risk_matrix": risk_matrix,
                "metrics": {
                    "completion_rate": round(float(metrics.completion_rate * 100), 1),
                    "scenario_completed": bool(metrics.scenario_completed),
                    "collision_count": int(metrics.collision_count),
                    "near_collision_count": int(metrics.near_collision_count),
                    "min_clearance": round(float(metrics.min_clearance_meters), 2),
                    "smoothness_score": round(float(metrics.smoothness_score), 3),
                    "replan_count": int(metrics.replan_count),
                    "avg_replan_latency_ms": round(float(metrics.avg_replan_latency_ms), 1),
                    "loop_latency_ms": round(float(self.system.latencies.get("Overall_Loop", 0.0)), 1),
                },
                "latencies": {k: round(float(v), 1) for k, v in self.system.latencies.items()}
            }


manager = SystemManager()


# --------------------------------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------------------------------

@app.get("/api/system/status")
def get_system_status():
    return {
        "project": "IRIS — Indian Road Intelligence & Safe-Space Planner",
        "team": "KNIGHTS",
        "problem_statement": "SIH26037",
        "tagline": "Predict the road before the road becomes dangerous.",
        "status": "active",
        "phases_connected": 16,
        "is_paused": manager.is_paused,
        "is_demo_mode": manager.is_demo_mode,
        "active_scenario": manager.scenario_name,
        "active_planner": manager.planner_mode,
        "speed_multiplier": manager.speed_multiplier,
        "external_adapters": {
            "matlab": "AVAILABLE (Native Adapter Loaded)",
            "simulink": "AVAILABLE (14-DOF Signal Bus Ready)",
            "roadrunner": "AVAILABLE (OpenSCENARIO Catalog Ready)",
        },
        "disclaimer": "IRIS is a research simulation prototype and not a certified autonomous-driving system."
    }


@app.post("/api/system/start")
def start_system():
    manager.is_paused = False
    return {"status": "running"}


@app.post("/api/system/pause")
def pause_system():
    manager.is_paused = not manager.is_paused
    return {"is_paused": manager.is_paused}


@app.post("/api/system/reset")
def reset_system():
    manager._init_system()
    return {"status": "reset_complete"}


@app.post("/api/system/step")
def step_system():
    if manager.system:
        with manager.lock:
            manager.system.step()
    return {"status": "stepped"}


class SpeedRequest(BaseModel):
    multiplier: float


@app.post("/api/system/speed")
def set_speed(req: SpeedRequest):
    manager.speed_multiplier = max(0.2, min(5.0, req.multiplier))
    return {"speed_multiplier": manager.speed_multiplier}


@app.get("/api/simulation/state")
@app.get("/api/state")
def get_simulation_state():
    return manager.get_full_state()


@app.get("/api/simulation/vehicle")
def get_simulation_vehicle():
    state = manager.get_full_state()
    return state.get("ego", {})


@app.get("/api/simulation/objects")
def get_simulation_objects():
    state = manager.get_full_state()
    return {
        "actors": state.get("actors", []),
        "hazards": state.get("hazards", [])
    }


@app.get("/api/simulation/path")
def get_simulation_path():
    state = manager.get_full_state()
    ego = state.get("ego", {})
    return {
        "selected_path": ego.get("path", []),
        "lookahead_point": ego.get("lookahead_point", []),
        "current_waypoint": ego.get("current_waypoint", []),
        "condition": ego.get("condition", "NORMAL")
    }


@app.get("/api/risk/current")
def get_current_risk():
    state = manager.get_full_state()
    return {
        "risk_summary": state.get("risk", {}),
        "risk_matrix": state.get("risk_matrix", [])
    }


@app.get("/api/risk/future")
def get_future_risk():
    with manager.lock:
        fr = getattr(manager.system.world_model, "future_risk_field", None) if manager.system and manager.system.world_model else None
        horizon = 3.0
        peak = 0.0
        time_slices = []
        if fr and hasattr(fr, "get_peak_risk"):
            peak = fr.get_peak_risk()
        return {
            "prediction_horizon_seconds": horizon,
            "peak_future_risk": peak,
            "risk_summary": manager.get_full_state().get("risk", {}),
        }


@app.get("/api/safe-space")
def get_safe_space():
    state = manager.get_full_state()
    return {
        "corridors": state.get("corridors", []),
        "active_planner": manager.planner_mode,
        "selected_path": state.get("ego", {}).get("path", [])
    }


@app.get("/api/replanning/events")
def get_replanning_events():
    state = manager.get_full_state()
    return {
        "events": state.get("events", []),
        "total_replans": state.get("metrics", {}).get("replan_count", 0)
    }


@app.get("/api/metrics")
def get_metrics():
    state = manager.get_full_state()
    return state.get("metrics", {})


@app.get("/api/scenarios")
def list_scenarios():
    return [
        {
            "id": "UNMARKED_VILLAGE_ROAD",
            "name": "Unmarked Village Road",
            "category": "Mandatory",
            "description": "Narrow lane-free road with wandering pedestrians, motorcycles, and uneven shoulder.",
            "difficulty": "Medium",
            "traffic_density": "Moderate",
            "active_hazards": ["Uneven Road", "Potholes"]
        },
        {
            "id": "UNSIGNALIZED_URBAN_INTERSECTION",
            "name": "Unsignalized Urban Intersection",
            "category": "Mandatory",
            "description": "Multi-agent cross-traffic with swarming auto-rickshaws and crossing pedestrians without signals.",
            "difficulty": "High",
            "traffic_density": "Dense",
            "active_hazards": ["Cross Traffic", "Blind Spots"]
        },
        {
            "id": "HIGHWAY_MERGE",
            "name": "Highway Merge with Slow Vehicles",
            "category": "Mandatory",
            "description": "High-speed highway entry with slow-moving commercial trucks and merging vehicles.",
            "difficulty": "Medium",
            "traffic_density": "High",
            "active_hazards": ["Speed Differential", "Merge Conflict"]
        },
        {
            "id": "DENSE_MARKET",
            "name": "Dense Indian Market Area",
            "category": "Mandatory",
            "description": "High-entropy market corridor with static pushcarts, dense pedestrians, and two-wheelers.",
            "difficulty": "Extreme",
            "traffic_density": "Very High",
            "active_hazards": ["Pushcarts", "Crowd Density"]
        },
        {
            "id": "SUDDEN_CATTLE_CROSSING",
            "name": "Sudden Cattle Crossing",
            "category": "Mandatory",
            "description": "Unpredictable cattle herd crossing road requiring multi-hypothesis prediction and safe corridor extraction.",
            "difficulty": "High",
            "traffic_density": "Dynamic",
            "active_hazards": ["Cattle Herd", "Sudden Obstruction"]
        },
        {
            "id": "POTHOLE_AVOIDANCE",
            "name": "Severe Pothole Avoidance",
            "category": "Stress Test",
            "description": "Multiple deep surface depressions testing 3D surface hazard traversability classification.",
            "difficulty": "Medium",
            "traffic_density": "Low",
            "active_hazards": ["Deep Potholes", "Suspension Risk"]
        },
        {
            "id": "WATERLOGGING",
            "name": "Monsoon Waterlogging",
            "category": "Stress Test",
            "description": "Extensive standing water patch causing severe friction loss and hidden submerged hazard uncertainty.",
            "difficulty": "High",
            "traffic_density": "Moderate",
            "active_hazards": ["Water Puddle", "Friction Loss"]
        },
        {
            "id": "COMBINED_SURFACE_HAZARDS",
            "name": "Potholes + Waterlogging + Hidden Hazards",
            "category": "Stress Test",
            "description": "Combined severe road surface degradation with surface friction and deep pothole clusters.",
            "difficulty": "High",
            "traffic_density": "Moderate",
            "active_hazards": ["Potholes", "Waterlogging"]
        },
        {
            "id": "WRONG_SIDE_MOTORCYCLE",
            "name": "Wrong-Side Motorcycle",
            "category": "Stress Test",
            "description": "Oncoming aggressive motorcycle driving against traffic flow on ego vehicle lane.",
            "difficulty": "High",
            "traffic_density": "Dynamic",
            "active_hazards": ["Head-on Conflict", "Wrong-Way Vehicle"]
        },
        {
            "id": "TRAFFIC_CHAOS",
            "name": "Combined Indian Traffic Chaos",
            "category": "Stress Test",
            "description": "Maximum stress environment combining cattle, auto-rickshaws, potholes, water, and swerving bikes.",
            "difficulty": "Extreme",
            "traffic_density": "Maximum",
            "active_hazards": ["All Combined Hazards"]
        },
    ]


@app.post("/api/scenarios/{scenario_id}/start")
def start_scenario(scenario_id: str):
    manager.is_demo_mode = False
    manager.scenario_name = scenario_id
    manager._init_system()
    return {"status": "scenario_started", "scenario": scenario_id}


class PlannerRequest(BaseModel):
    planner: str


@app.post("/api/planner/{planner_mode}/set")
def set_planner(planner_mode: str):
    if planner_mode in ["iris", "astar", "safe_space", "adaptive", "iris_full", "baseline_astar"]:
        manager.planner_mode = planner_mode
        manager._init_system()
        return {"status": "planner_set", "planner": planner_mode}
    raise HTTPException(status_code=400, detail="Invalid planner mode")


@app.post("/api/demo/start")
def start_demo():
    manager.is_demo_mode = True
    manager.demo_step_index = 0
    manager.scenario_name = manager.demo_scenarios[0]
    manager._init_system()
    return {"status": "demo_started"}


@app.get("/api/experiments")
def get_experiments():
    return {
        "experiments": list_experiments(limit=50),
        "benchmarks": get_benchmarks_summary()
    }


class RunExperimentRequest(BaseModel):
    scenario_id: str
    planner_mode: str
    seed: int = 42
    duration: float = 6.0


@app.post("/api/experiments/run")
def run_experiment_endpoint(req: RunExperimentRequest):
    # Run rapid headless experiment
    temp_sys = IRISSystem({
        "scenario": req.scenario_id,
        "planner": req.planner_mode,
        "mode": "simulation",
        "seed": req.seed,
        "headless": True,
        "duration": req.duration
    })
    temp_sys.initialize()
    while temp_sys.running:
        temp_sys.step()
    
    final_m = temp_sys.metrics_tracker.finalize()
    m_dict = final_m.to_dict()
    m_dict["peak_future_risk"] = float(final_m.peak_risk)
    m_dict["loop_latency_ms"] = float(temp_sys.latencies.get("Overall_Loop", 0.0))

    exp_id = save_experiment(
        experiment_name=f"Run_{req.scenario_id}_{req.planner_mode}",
        scenario_id=req.scenario_id,
        planner_mode=req.planner_mode,
        seed=req.seed,
        duration=req.duration,
        metrics=m_dict,
        config=temp_sys.config
    )

    return {
        "experiment_id": exp_id,
        "metrics": m_dict
    }


@app.get("/api/experiments/export/{format}")
def export_experiments(format: str):
    exps = list_experiments(limit=100)
    if format == "json":
        return exps
    elif format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Experiment", "Scenario", "Planner", "Seed", "Collisions", "NearMisses", "MinClearance", "PeakRisk", "Smoothness", "Replans", "Timestamp"])
        for e in exps:
            m = e.get("metrics", {})
            writer.writerow([
                e["id"], e["experiment_name"], e["scenario_id"], e["planner_mode"], e["seed"],
                m.get("collision_count", 0), m.get("near_collision_count", 0),
                m.get("min_clearance_meters", m.get("min_clearance", 0.0)),
                m.get("peak_risk", m.get("peak_future_risk", 0.0)),
                m.get("smoothness_score", 1.0),
                m.get("replan_count", 0),
                e["timestamp"]
            ])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=iris_experiments.csv"})
    raise HTTPException(status_code=400, detail="Unsupported format")


@app.get("/api/system/architecture")
def get_architecture():
    return [
        {
            "id": "p1",
            "name": "Phase 1: Environment & Traffic Simulation",
            "purpose": "Simulates lane-free unstructured Indian roads, heterogeneous dynamic agents, and surface hazards.",
            "inputs": "Scenario Presets, Random Seed, Road Geometry",
            "outputs": "EgoVehicle, TrafficActors (Rickshaws, Cattle, Bikes, Trucks), SurfaceHazards",
            "algorithm": "2D Kinematic Model with Heterogeneous Behavioral Dynamics",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p2",
            "name": "Phase 2: Spatial World Model",
            "purpose": "Maintains 2D 0.25m spatial occupancy and drivable space grid.",
            "inputs": "Ego State, Road Boundaries, Static Elements",
            "outputs": "OccupancyGrid (Free, Occupied, Pothole, Boundary)",
            "algorithm": "2D Discrete Spatial Rasterization & Coordinate Converter",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p3",
            "name": "Phase 3: Baseline A* Grid Planner",
            "purpose": "Provides classical heuristic grid search benchmark for comparative validation.",
            "inputs": "WorldModel Grid, Start Position, Goal Position",
            "outputs": "Grid Waypoint Path, Path Validation Result",
            "algorithm": "8-Connected A* Heuristic Search with Footprint Validation",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p4",
            "name": "Phase 4: Instantaneous Risk Engine",
            "purpose": "Computes current spatial risk combining traffic, surface, boundary, and collision cones.",
            "inputs": "WorldModel, Dynamic Actors, Surface Model",
            "outputs": "RiskGrid (R(x,y) in [0.0, 1.0])",
            "algorithm": "Multi-Factor Weighted Spatial Risk Fusion",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p5",
            "name": "Phase 5: Road Surface Intelligence",
            "purpose": "Detects and classifies potholes, waterlogging, and elevation hazards.",
            "inputs": "Surface Hazard Entities, Sensor Noise",
            "outputs": "Surface Hazard Traversability & Friction Cost Masks",
            "algorithm": "Depth/Severity Penalty with Friction Degradation Mapping",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p6",
            "name": "Phase 6: Multi-Class Perception",
            "purpose": "Simulates sensor detection across 7 Indian traffic participant categories.",
            "inputs": "Raw Environment Actor Objects, Range Noise",
            "outputs": "DetectedObjects with Confidence & Bounding Boxes",
            "algorithm": "Multi-Sensor Detection Simulation with Sensor Fusion",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p7",
            "name": "Phase 7: Multi-Object MOT Tracking",
            "purpose": "Maintains temporal identity and kinematic filtering across occlusion.",
            "inputs": "Detections, Previous Track States",
            "outputs": "Confirmed Tracks with Velocity & Acceleration Vectors",
            "algorithm": "Extended Kalman Filter + Hungarian Assignment",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p8",
            "name": "Phase 8: Motion Prediction",
            "purpose": "Generates multi-hypothesis future trajectories over a 3.0s horizon.",
            "inputs": "Active MOT Tracks, Road Constraints",
            "outputs": "Multi-Hypothesis Trajectory Ensembles (CV, Swerving, Turn)",
            "algorithm": "Behavioral Hypothesis Generator with Road-Bound Constraints",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p9",
            "name": "Phase 9: Spatial Uncertainty Modeling",
            "purpose": "Separates confidence from uncertainty and expands spatial covariance ellipses.",
            "inputs": "Tracks, Prediction Hypotheses Disagreement, Perception Confidence",
            "outputs": "Spatial Uncertainty Ellipses and Temporal Growth Masks",
            "algorithm": "Covariance Propagation & Multi-Branch Divergence Penalty",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p10",
            "name": "Phase 10: Spatiotemporal Future Risk Field",
            "purpose": "Projects dynamic future collision and surface risk over 0-3.0s into a 4D tensor.",
            "inputs": "Predictions, Uncertainty Sets, Surface Hazards, WorldModel",
            "outputs": "FutureRiskField tensor across discretized timesteps",
            "algorithm": "Spatiotemporal Gaussian Convolution & Horizon Discretization",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p11",
            "name": "Phase 11: Negative-Space Corridor Analyzer",
            "purpose": "Extracts open drivable safe corridors rather than merely avoiding obstacles.",
            "inputs": "FutureRiskField, WorldModel Drivable Space",
            "outputs": "Candidate Safe Corridors & Sampled Trajectories",
            "algorithm": "Voronoi / Negative Space Drivability Corridor Extraction",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p12",
            "name": "Phase 12: Proactive Safe-Space Planner & Replanning",
            "purpose": "Multi-objective trajectory cost scoring and event-driven replanning triggers.",
            "inputs": "Candidate Corridors, Current Path, Future Risk Surges",
            "outputs": "Selected Drivable Trajectory, Replanning Trigger Flag",
            "algorithm": "Multi-Objective Cost Optimization with Hysteresis Triggers",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p13",
            "name": "Phase 13: Decision State Machine",
            "purpose": "Selects tactical driving mode and longitudinal speed profiles.",
            "inputs": "Future Peak Risk, Side Clearance, Replan Event, Goal Distance",
            "outputs": "Decision State (CRUISE, CAUTION, CREEP, OVERTAKE, EMERGENCY_STOP)",
            "algorithm": "Hierarchical Deterministic Finite State Machine",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p14",
            "name": "Phase 14: Vehicle Motion Control",
            "purpose": "Computes cross-track steering and PID longitudinal acceleration/braking.",
            "inputs": "Ego Kinematics, Selected Path Waypoints, Target Speed",
            "outputs": "Steering Angle (rad), Throttle/Brake Acceleration (m/s2)",
            "algorithm": "Pure Pursuit / Stanley Geometric Steering + Longitudinal PID",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p15",
            "name": "Phase 15: Evaluation & Metrics Engine",
            "purpose": "Tracks real-time collision logging, TTC, side clearance, and smoothness score.",
            "inputs": "Ego Telemetry, Dynamic Environment, Replanning Logs",
            "outputs": "Standardized Autonomous Driving Benchmark Metrics",
            "algorithm": "Continuous Geometric Collision & Curvature Variance Scoring",
            "status": "CONNECTED (Active)"
        },
        {
            "id": "p16",
            "name": "Phase 16: MATLAB / Simulink / RoadRunner Bridge",
            "purpose": "Provides co-simulation bridges and open standard schema export.",
            "inputs": "WorldModel, FutureRiskField, Trajectory Buses",
            "outputs": "JSON Socket Stream, Simulink Buses, OpenSCENARIO Specs",
            "algorithm": "IPC Socket Streaming & OpenSCENARIO Catalog Mapping",
            "status": "CONNECTED (Available)"
        }
    ]


# --------------------------------------------------------------------------
# WEBSOCKET REAL-TIME STREAMING
# --------------------------------------------------------------------------

@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            state = manager.get_full_state()
            await websocket.send_text(json.dumps(state))
            await asyncio.sleep(0.05)  # 20 FPS stream
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# --------------------------------------------------------------------------
# MOUNT STATIC FRONTEND ASSETS
# --------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.join(ROOT_DIR, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
