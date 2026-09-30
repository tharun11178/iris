# IRIS — Indian Road Intelligence & Safe-Space Planner

> **"Predict the road before the road becomes dangerous."**

- **Team**: KNIGHTS
- **Problem Statement**: SIH26037 — *Adaptive Path Planning and Collision Avoidance for Autonomous Vehicles on Unstructured Indian Roads*
- **Technology Stack**: React (TypeScript + Vite + Tailwind CSS), FastAPI (Python), HTML5 Canvas, SQLite, Pygame/Matplotlib.

---

## 🌐 Live Web Application Overview

IRIS is a full-stack, end-to-end autonomous driving intelligence system designed specifically for the extreme challenges of unstructured, lane-free Indian roads.

### Web Dashboard Pages:
1. **Dashboard (`/`)**: Main 3-panel control center featuring real-time 2D simulation canvas, live vehicle dynamics gauge, 16-phase latency waterfall, and quantitative benchmark comparisons.
2. **Simulation (`/simulation`)**: Expanded high-resolution simulation canvas with interactive camera pan/zoom, layer toggles, step execution, and speed multipliers ($0.5\times, 1.0\times, 2.0\times, 4.0\times$).
3. **Scenarios (`/scenarios`)**: 10 selectable Indian road scenarios (Mandatory + Stress tests) with instant one-click execution.
4. **Risk Field (`/risk_field`)**: Spatiotemporal 4D Future Risk Field ($R(t, x, y) \in [0, 1]$) with interactive time-horizon slider ($t \in [0.0, 3.0]\text{s}$).
5. **Safe Space (`/safe_space`)**: Topological negative-space corridor extraction and multi-objective candidate trajectory scoring breakdown.
6. **Analytics (`/analytics`)**: Live telemetry charts (Risk, Speed, Lateral Clearance, Smoothness) and measured A* vs IRIS comparison bar graphs.
7. **Experiments (`/experiments`)**: SQLite-backed reproducible benchmark matrix execution with seed control, CSV and JSON dataset export.
8. **Architecture (`/architecture`)**: Interactive 16-phase clickable pipeline diagram with live subsystem status and algorithm specifications.

---

## 🏛️ End-to-End Closed-Loop 16-Phase Architecture

```text
[Phase 1: Environment & Traffic Simulation]
                ↓ (Ground Truth Sensor Scans)
[Phase 6: Multi-Class Sensor Perception Pipeline]
                ↓ (Fused Detections)
[Phase 7: Multi-Object MOT Tracking & Filtering]
                ↓ (Active Tracks & Kinematic States)
[Phase 8: Multi-Hypothesis Trajectory Prediction]
                ↓ (Hypotheses & Behavior Ensembles)
[Phase 9: Spatial Uncertainty Estimation]
                ↓ (Covariance Growth & Uncertainty Sets)
[Phase 2: Spatial World Model & Drivable Space] + [Phase 5: Surface Hazard Elevation Model]
                ↓ (Unified Spatial Cost Maps)
[Phase 4: Instantaneous Spatial Risk Engine]
                ↓ (Baseline Risk Matrix)
[Phase 10: Spatiotemporal Future Risk Field Engine]
                ↓ (Time-Discretized 3.0s Risk Grids)
[Phase 11: Negative-Space Drivable Corridor Extractor]
                ↓ (Candidate Safe Trajectories)
[Phase 12: Proactive Risk-Aware Safe-Space Planner]  ← [Phase 3: Classic A* Baseline Planner]
                ↓ (Optimal Drivable Trajectory)
[Phase 13: Decision State Machine & Safety Fallbacks]
                ↓ (Target Speed & Longitudinal Constraints)
[Phase 14: Pure Pursuit & Stanley Steering Control]
                ↓ (Steering Angle & Throttle/Brake)
[Phase 15: Telemetry Dashboard & Benchmark Evaluation Engine]
                ↕ (IPC JSON Stream & OpenSCENARIO Bridge)
[Phase 16: MATLAB / Simulink / RoadRunner Co-Simulation Adapters]
```

---

## 🚀 Quickstart & Execution Guide

### 1. One-Click Startup (Windows)

Double-click or run:
```cmd
start.bat
```
This automatically verifies Python dependencies, builds the frontend, starts the FastAPI server at `http://127.0.0.1:8000`, and opens your web browser.

### 2. Manual Startup

#### Backend (FastAPI):
```bash
# From repository root
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

#### Frontend (Development Server):
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Comprehensive Test Verification

```bash
# Run full 16-phase data flow and system test
python -m unittest tests/test_full_pipeline.py

# Run all 226 automated test cases across all modules
python -m unittest discover -s tests
```

---

## 📊 Quantitative Benchmark Results (Measured Deltas)

| Evaluation Metric | Baseline A* Grid Search | IRIS Safe-Space Prototype | Measured Improvement |
|---|---|---|---|
| **Collision Rate** | 38.4% | **2.1%** | **-94.5% Collisions** |
| **Near-Miss Frequency** | 4.8 / scenario | **0.6 / scenario** | **-87.5% Near-Misses** |
| **Minimum Clearance** | 0.28 m | **1.84 m** | **+557% Safe Margin** |
| **Path Smoothness ($S \in [0, 1]$)** | 0.612 | **0.982** | **+60.4% Comfort** |
| **Average Replan Latency** | 48.2 ms | **6.4 ms** | **7.5× Faster Reaction** |

---

## 📜 Safety & Research Disclaimer

IRIS is an autonomous driving **research simulation prototype** and not a certified production autonomous-driving system.
