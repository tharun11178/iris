"""
IRIS Web Dashboard Server.
Connects the live 16-phase IRIS Autonomous Driving System to an interactive Web UI.
Serves static frontend assets (HTML/CSS/JS) and real-time REST API state endpoints.
"""

import os
import sys
import json
import time
import math
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.iris_system import IRISSystem
from simulation.environment import SimulationEnvironment


class IRISWebServer:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.scenario_name = "SUDDEN_CATTLE_CROSSING"
        self.planner_mode = "iris"
        self.seed = 42
        self.is_paused = False
        self.fps_target = 20.0
        self.lock = threading.Lock()
        
        # Initialize System
        self.system = None
        self._init_system()
        
        # Background Simulation Thread
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
                "duration": 3600.0  # Run continuously in web mode
            })
            self.system.initialize()

    def _sim_loop(self):
        while self.running:
            t_start = time.perf_counter()
            if not self.is_paused and self.system and self.system.running:
                with self.lock:
                    self.system.step()
                    if self.system.metrics_tracker.metrics.scenario_completed:
                        # Auto-loop or reset upon completion
                        time.sleep(1.0)
                        self._init_system()
            
            elapsed = time.perf_counter() - t_start
            sleep_time = max(0.01, (1.0 / self.fps_target) - elapsed)
            time.sleep(sleep_time)

    def get_state(self):
        with self.lock:
            if not self.system or not self.system.env:
                return {"status": "initializing"}

            env = self.system.env
            ego = env.ego_vehicle
            wm = self.system.world_model
            metrics = self.system.metrics_tracker.metrics
            replanning = self.system.replanning_manager
            
            # Ego Data
            ego_data = {
                "x": round(ego.x, 2),
                "y": round(ego.y, 2),
                "heading": round(ego.heading, 3),
                "velocity": round(ego.velocity, 2),
                "speed_kmh": round(ego.velocity * 3.6, 1),
                "target_speed": round(getattr(ego, "target_speed", 10.0), 2),
                "steering_angle": round(getattr(ego, "steering_angle", 0.0), 3),
                "length": ego.length,
                "width": ego.width,
                "clearance": round(env.get_minimum_clearance(), 2),
                "decision_state": getattr(self.system, "current_decision_state", "CRUISE"),
            }

            # Active Path
            path_points = []
            if ego.current_path and hasattr(ego.current_path, "waypoints"):
                path_points = [[round(p[0], 2), round(p[1], 2)] for p in ego.current_path.waypoints]
            ego_data["path"] = path_points

            # Traffic Actors
            actors_data = []
            for actor in getattr(env, "traffic_actors", []):
                # Hypotheses
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
                            hyp_pts = [[round(pt[0], 2), round(pt[1], 2)] for pt in getattr(hyp, "trajectory", [])]
                            h_type = getattr(hyp, "hypothesis_type", "DEFAULT")
                            hypotheses.append({
                                "type": h_type.name if hasattr(h_type, "name") else str(h_type),
                                "probability": round(getattr(hyp, "probability", 0.5), 2),
                                "points": hyp_pts
                            })

                # Uncertainty Ellipse
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
                actors_data.append({
                    "id": actor.actor_id,
                    "type": a_type.name if hasattr(a_type, "name") else str(a_type),
                    "x": round(actor.x, 2),
                    "y": round(actor.y, 2),
                    "heading": round(actor.heading, 3),
                    "speed": round(actor.velocity, 2),
                    "length": getattr(actor, "length", 4.0),
                    "width": getattr(actor, "width", 1.8),
                    "hypotheses": hypotheses,
                    "uncertainty": ellipse_data
                })

            # Surface Hazards
            hazards_data = []
            for h in env.surface_hazards:
                hazards_data.append({
                    "id": h.hazard_id,
                    "type": h.hazard_type.name if hasattr(h.hazard_type, "name") else str(h.hazard_type),
                    "x": round(h.x, 2),
                    "y": round(h.y, 2),
                    "length": round(getattr(h, "length", 2.0), 2),
                    "width": round(getattr(h, "width", 2.0), 2),
                    "severity": round(getattr(h, "severity", 0.5), 2),
                    "is_traversable": getattr(h, "is_traversable", True)
                })

            # Safe Space Candidate Corridors
            corridors = []
            if hasattr(self.system, "safe_space_planner") and self.system.safe_space_planner.last_result:
                res = self.system.safe_space_planner.last_result
                if hasattr(res, "candidates"):
                    for c in res.candidates[:5]:
                        if hasattr(c, "trajectory"):
                            corridors.append({
                                "points": [[round(p[0], 2), round(p[1], 2)] for p in c.trajectory],
                                "score": round(getattr(c, "total_score", 0.0), 3),
                                "is_selected": getattr(c, "is_selected", False)
                            })

            # Replanning Events
            events_data = []
            if replanning and replanning.event_log:
                for ev in replanning.event_log[-6:]:
                    events_data.append({
                        "timestamp": round(getattr(ev, "timestamp", 0.0), 2),
                        "reason": str(getattr(ev, "trigger_reason", "REPLAN")),
                        "latency_ms": round(getattr(ev, "replan_latency_ms", 0.0), 1),
                        "risk_before": round(getattr(ev, "risk_before", 0.0), 2),
                        "risk_after": round(getattr(ev, "risk_after", 0.0), 2),
                    })

            # Risk Summary & Heatmap Samples
            risk_summary = {
                "peak_future_risk": round(metrics.peak_risk, 3),
                "current_risk": round(self.system.risk_engine.risk_grid.get_max_risk() if self.system.risk_engine.risk_grid else 0.0, 3)
            }

            # Downsampled Risk Heatmap for Fast Web Canvas Rendering (e.g., 20 rows x 50 cols)
            risk_matrix = []
            if self.system.risk_engine.risk_grid:
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
                "scenario_id": self.scenario_name,
                "planner_mode": self.planner_mode,
                "road": {
                    "length": env.road.length,
                    "width": env.road.width,
                    "lanes": getattr(env.road, "num_lanes", 2),
                },
                "ego": ego_data,
                "actors": actors_data,
                "hazards": hazards_data,
                "corridors": corridors,
                "events": events_data,
                "risk": risk_summary,
                "risk_matrix": risk_matrix,
                "metrics": {
                    "completion_rate": round(metrics.completion_rate * 100, 1),
                    "scenario_completed": metrics.scenario_completed,
                    "collision_count": metrics.collision_count,
                    "near_collision_count": metrics.near_collision_count,
                    "min_clearance": round(metrics.min_clearance_meters, 2),
                    "smoothness_score": round(metrics.smoothness_score, 3),
                    "replan_count": metrics.replan_count,
                    "avg_replan_latency_ms": round(metrics.avg_replan_latency_ms, 1),
                    "loop_latency_ms": round(self.system.latencies.get("Overall_Loop", 0.0), 1),
                },
                "latencies": {k: round(v, 1) for k, v in self.system.latencies.items()}
            }

    def switch_scenario(self, scenario_name):
        self.scenario_name = scenario_name
        self._init_system()

    def switch_planner(self, planner_mode):
        self.planner_mode = planner_mode
        self._init_system()

    def reset(self):
        self._init_system()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        return self.is_paused


def json_serial(obj):
    if hasattr(obj, "item"):
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)


def make_handler(web_server):
    class IRISHTTPRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
            super().__init__(*args, directory=web_dir, **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    state = web_server.get_state()
                    self.wfile.write(json.dumps(state, default=json_serial).encode("utf-8"))
                except Exception as e:
                    self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            elif parsed.path == "/api/scenarios":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                scenarios = [
                    {"id": "SUDDEN_CATTLE_CROSSING", "name": "Sudden Cattle Crossing", "desc": "Cattle herd blocking lane with dynamic risk surge"},
                    {"id": "UNMARKED_VILLAGE_ROAD", "name": "Unmarked Village Road", "desc": "Narrow lane-free road with two-wheelers and pedestrians"},
                    {"id": "DENSE_MARKET", "name": "Dense Indian Market", "desc": "High entropy pushcarts, rickshaws, and pedestrians"},
                    {"id": "COMBINED_SURFACE_HAZARDS", "name": "Potholes & Waterlogging", "desc": "Severe road degradation with water logging friction loss"},
                    {"id": "UNSIGNALIZED_URBAN_INTERSECTION", "name": "Urban Unsignalized Intersection", "desc": "Multi-agent cross traffic without signals"},
                    {"id": "HIGHWAY_MERGE", "name": "Highway High-Speed Merge", "desc": "Aggressive high-speed lane merge scenario"},
                ]
                self.wfile.write(json.dumps(scenarios).encode("utf-8"))
            else:
                super().do_GET()

        def do_POST(self):
            parsed = urlparse(self.path)
            content_length = int(self.headers.get("Content-Length", 0))
            body_str = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                body = json.loads(body_str) if body_str else {}
            except Exception:
                body = {}

            if parsed.path == "/api/pause":
                paused = web_server.toggle_pause()
                self._send_json({"is_paused": paused})
            elif parsed.path == "/api/reset":
                web_server.reset()
                self._send_json({"status": "reset_complete"})
            elif parsed.path == "/api/switch_scenario":
                sc = body.get("scenario", "SUDDEN_CATTLE_CROSSING")
                web_server.switch_scenario(sc)
                self._send_json({"status": "switched", "scenario": sc})
            elif parsed.path == "/api/switch_planner":
                planner = body.get("planner", "iris")
                web_server.switch_planner(planner)
                self._send_json({"status": "switched", "planner": planner})
            else:
                self.send_response(404)
                self.end_headers()

        def _send_json(self, data):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        def log_message(self, format, *args):
            # Suppress noisy HTTP request logging in terminal
            pass

    return IRISHTTPRequestHandler


def run_server(port=8000):
    server_instance = IRISWebServer(host="127.0.0.1", port=port)
    handler = make_handler(server_instance)
    httpd = HTTPServer(("127.0.0.1", port), handler)
    print(f"[IRIS Web Server] Running live simulation web server at: http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
