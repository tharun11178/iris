"""
IRIS SQLite Database Layer.
Manages persistent storage for experiment runs, benchmark comparisons, and system settings.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "iris_experiments.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Experiments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_name TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            planner_mode TEXT NOT NULL,
            seed INTEGER NOT NULL,
            duration REAL NOT NULL,
            config_json TEXT,
            metrics_json TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Benchmark Matrix Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id TEXT NOT NULL,
            planner_mode TEXT NOT NULL,
            collision_count INTEGER,
            near_collision_count INTEGER,
            min_clearance REAL,
            peak_risk REAL,
            smoothness_score REAL,
            replan_count INTEGER,
            avg_replan_latency_ms REAL,
            loop_latency_ms REAL,
            completion_rate REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # System Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_experiment(
    experiment_name: str,
    scenario_id: str,
    planner_mode: str,
    seed: int,
    duration: float,
    metrics: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO experiments (experiment_name, scenario_id, planner_mode, seed, duration, config_json, metrics_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment_name,
            scenario_id,
            planner_mode,
            seed,
            duration,
            json.dumps(config or {}),
            json.dumps(metrics),
        ),
    )
    exp_id = cursor.lastrowid

    # Also log to benchmark_runs
    cursor.execute(
        """
        INSERT INTO benchmark_runs (
            scenario_id, planner_mode, collision_count, near_collision_count,
            min_clearance, peak_risk, smoothness_score, replan_count,
            avg_replan_latency_ms, loop_latency_ms, completion_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scenario_id,
            planner_mode,
            metrics.get("collision_count", 0),
            metrics.get("near_collision_count", 0),
            metrics.get("min_clearance", 0.0),
            metrics.get("peak_future_risk", 0.0),
            metrics.get("smoothness_score", 1.0),
            metrics.get("replan_count", 0),
            metrics.get("avg_replan_latency_ms", 0.0),
            metrics.get("loop_latency_ms", 0.0),
            metrics.get("completion_rate", 0.0),
        ),
    )

    conn.commit()
    conn.close()
    return exp_id


def list_experiments(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiments ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "experiment_name": r["experiment_name"],
            "scenario_id": r["scenario_id"],
            "planner_mode": r["planner_mode"],
            "seed": r["seed"],
            "duration": r["duration"],
            "config": json.loads(r["config_json"] or "{}"),
            "metrics": json.loads(r["metrics_json"] or "{}"),
            "timestamp": r["timestamp"],
        })
    conn.close()
    return results


def get_benchmarks_summary() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT scenario_id, planner_mode,
               AVG(collision_count) as avg_collisions,
               AVG(near_collision_count) as avg_near_collisions,
               AVG(min_clearance) as avg_clearance,
               AVG(peak_risk) as avg_peak_risk,
               AVG(smoothness_score) as avg_smoothness,
               AVG(replan_count) as avg_replans,
               AVG(avg_replan_latency_ms) as avg_replan_latency,
               AVG(completion_rate) as avg_completion,
               COUNT(*) as total_runs
        FROM benchmark_runs
        GROUP BY scenario_id, planner_mode
    """)
    rows = cursor.fetchall()
    benchmarks = []
    for r in rows:
        benchmarks.append({
            "scenario_id": r["scenario_id"],
            "planner_mode": r["planner_mode"],
            "avg_collisions": round(r["avg_collisions"] or 0, 2),
            "avg_near_collisions": round(r["avg_near_collisions"] or 0, 2),
            "avg_clearance": round(r["avg_clearance"] or 0, 2),
            "avg_peak_risk": round(r["avg_peak_risk"] or 0, 3),
            "avg_smoothness": round(r["avg_smoothness"] or 0, 3),
            "avg_replans": round(r["avg_replans"] or 0, 1),
            "avg_replan_latency": round(r["avg_replan_latency"] or 0, 1),
            "avg_completion": round(r["avg_completion"] or 0, 1),
            "total_runs": r["total_runs"],
        })
    conn.close()
    return benchmarks


init_db()
