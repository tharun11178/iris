/* ==========================================================================
   IRIS Web Application Frontend Logic
   High-performance 2D Canvas Visualizer, HUD Controller, and REST Poller
   ========================================================================== */

class IRISApp {
    constructor() {
        this.canvas = document.getElementById("simCanvas");
        this.ctx = this.canvas.getContext("2d");
        this.container = document.getElementById("canvasContainer");

        // Camera & View Transform
        this.scale = 14.0; // pixels per meter
        this.cameraX = 0.0; // world center X (meters)
        this.cameraY = 25.0; // world center Y (meters)
        this.followEgo = true;
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;

        // Layer Toggles
        this.showRisk = true;
        this.showPredictions = true;
        this.showUncertainty = true;
        this.showCorridors = true;
        this.showHazards = true;

        // State & Interpolation
        this.latestState = null;
        this.lastFetchTime = 0;
        this.isPaused = false;

        this.initUI();
        this.initCanvasEvents();
        this.resize();
        window.addEventListener("resize", () => this.resize());

        // Start Loop
        this.startStatePolling();
        requestAnimationFrame(() => this.renderLoop());
    }

    initUI() {
        // Scenario Selector
        const scenarioSelect = document.getElementById("scenarioSelect");
        scenarioSelect.addEventListener("change", async (e) => {
            const sc = e.target.value;
            await fetch("/api/switch_scenario", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario: sc })
            });
        });

        // Planner Switcher
        const btnIris = document.getElementById("btnPlannerIris");
        const btnAstar = document.getElementById("btnPlannerAstar");

        btnIris.addEventListener("click", async () => {
            btnIris.classList.add("active");
            btnAstar.classList.remove("active");
            await fetch("/api/switch_planner", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ planner: "iris" })
            });
        });

        btnAstar.addEventListener("click", async () => {
            btnAstar.classList.add("active");
            btnIris.classList.remove("active");
            await fetch("/api/switch_planner", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ planner: "astar" })
            });
        });

        // Play/Pause Button
        const btnPause = document.getElementById("btnPause");
        const playIcon = document.getElementById("playIcon");
        const pauseIcon = document.getElementById("pauseIcon");
        const btnPauseText = document.getElementById("btnPauseText");

        btnPause.addEventListener("click", async () => {
            const res = await fetch("/api/pause", { method: "POST" });
            const data = await res.json();
            this.isPaused = data.is_paused;
            if (this.isPaused) {
                playIcon.style.display = "block";
                pauseIcon.style.display = "none";
                btnPauseText.textContent = "Resume";
            } else {
                playIcon.style.display = "none";
                pauseIcon.style.display = "block";
                btnPauseText.textContent = "Pause";
            }
        });

        // Reset Button
        const btnReset = document.getElementById("btnReset");
        btnReset.addEventListener("click", async () => {
            await fetch("/api/reset", { method: "POST" });
        });

        // Layer Checkboxes
        document.getElementById("chkRisk").addEventListener("change", (e) => this.showRisk = e.target.checked);
        document.getElementById("chkPredictions").addEventListener("change", (e) => this.showPredictions = e.target.checked);
        document.getElementById("chkUncertainty").addEventListener("change", (e) => this.showUncertainty = e.target.checked);
        document.getElementById("chkCorridors").addEventListener("change", (e) => this.showCorridors = e.target.checked);
        document.getElementById("chkHazards").addEventListener("change", (e) => this.showHazards = e.target.checked);

        // View Controls
        const btnFollow = document.getElementById("btnFollow");
        btnFollow.addEventListener("click", () => {
            this.followEgo = !this.followEgo;
            btnFollow.classList.toggle("active", this.followEgo);
        });

        document.getElementById("btnZoomIn").addEventListener("click", () => {
            this.scale = Math.min(35.0, this.scale * 1.2);
        });

        document.getElementById("btnZoomOut").addEventListener("click", () => {
            this.scale = Math.max(5.0, this.scale / 1.2);
        });

        document.getElementById("btnResetView").addEventListener("click", () => {
            this.scale = 14.0;
            this.followEgo = true;
            btnFollow.classList.add("active");
        });
    }

    initCanvasEvents() {
        this.canvas.addEventListener("mousedown", (e) => {
            this.isDragging = true;
            this.dragStartX = e.clientX;
            this.dragStartY = e.clientY;
            this.followEgo = false;
            document.getElementById("btnFollow").classList.remove("active");
        });

        window.addEventListener("mousemove", (e) => {
            if (!this.isDragging) return;
            const dx = e.clientX - this.dragStartX;
            const dy = e.clientY - this.dragStartY;
            this.dragStartX = e.clientX;
            this.dragStartY = e.clientY;

            // Invert Y because canvas Y is down while world Y is up
            this.cameraX -= dx / this.scale;
            this.cameraY += dy / this.scale;
        });

        window.addEventListener("mouseup", () => {
            this.isDragging = false;
        });

        this.canvas.addEventListener("wheel", (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
            this.scale = Math.max(5.0, Math.min(40.0, this.scale * zoomFactor));
        });
    }

    resize() {
        const rect = this.container.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.displayWidth = rect.width;
        this.displayHeight = rect.height;
    }

    worldToScreen(x, y) {
        // World: X is lateral (left - / right +), Y is longitudinal (forward +)
        // Screen: (0,0) top left. Center screen is camera (cameraX, cameraY)
        const screenX = this.displayWidth / 2 + (x - this.cameraX) * this.scale;
        const screenY = this.displayHeight / 2 - (y - this.cameraY) * this.scale;
        return { x: screenX, y: screenY };
    }

    startStatePolling() {
        const poll = async () => {
            try {
                const res = await fetch("/api/state");
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.status === "running") {
                        this.latestState = data;
                        this.updateHUD(data);
                    }
                }
            } catch (err) {
                // Silently retry on polling error
            }
            setTimeout(poll, 50); // 20 FPS state update
        };
        poll();
    }

    updateHUD(state) {
        // Ego Telemetry
        const ego = state.ego;
        document.getElementById("speedVal").textContent = ego.speed_kmh.toFixed(1);
        document.getElementById("targetSpeedVal").textContent = (ego.target_speed * 3.6).toFixed(1);
        document.getElementById("steerVal").textContent = (ego.steering_angle * 180 / Math.PI).toFixed(1) + "°";
        document.getElementById("clearanceVal").textContent = ego.clearance.toFixed(2) + " m";
        document.getElementById("simTimeVal").textContent = state.sim_time.toFixed(2) + " s";
        document.getElementById("peakRiskVal").textContent = state.risk.peak_future_risk.toFixed(3);

        const decPill = document.getElementById("decisionPill");
        decPill.textContent = ego.decision_state || "CRUISE";
        if (ego.decision_state === "EMERGENCY_STOP") {
            decPill.style.background = "rgba(239, 68, 68, 0.2)";
            decPill.style.color = "#ef4444";
        } else if (ego.decision_state === "CAUTION" || ego.decision_state === "CREEP") {
            decPill.style.background = "rgba(245, 158, 11, 0.2)";
            decPill.style.color = "#f59e0b";
        } else {
            decPill.style.background = "rgba(6, 182, 212, 0.15)";
            decPill.style.color = "#06b6d4";
        }

        // Latencies
        const lat = state.latencies || {};
        document.getElementById("loopLatencyBadge").textContent = (state.metrics.loop_latency_ms || 0).toFixed(1) + " ms";
        document.getElementById("latP6").textContent = (lat.P6_Perception || 0).toFixed(1) + " ms";
        document.getElementById("latP7").textContent = (lat.P7_Tracking || 0).toFixed(1) + " ms";
        document.getElementById("latP8").textContent = (lat.P8_Prediction || 0).toFixed(1) + " ms";
        document.getElementById("latP9").textContent = (lat.P9_Uncertainty || 0).toFixed(1) + " ms";
        document.getElementById("latP10").textContent = (lat.P10_FutureRisk || 0).toFixed(1) + " ms";
        document.getElementById("latP12").textContent = (lat.P12_Replanning || 0).toFixed(1) + " ms";
        document.getElementById("latP14").textContent = (lat.P14_Control || 0).toFixed(1) + " ms";

        // Metrics
        const m = state.metrics;
        document.getElementById("completionBadge").textContent = m.completion_rate.toFixed(0) + "% Complete";
        document.getElementById("collisionVal").textContent = m.collision_count;
        document.getElementById("nearMissVal").textContent = m.near_collision_count;
        document.getElementById("smoothnessVal").textContent = m.smoothness_score.toFixed(3);
        document.getElementById("replanCountVal").textContent = m.replan_count;

        // Bottom HUD
        document.getElementById("egoCoordsHud").textContent = `X: ${ego.x.toFixed(1)}m | Y: ${ego.y.toFixed(1)}m | ${ego.speed_kmh.toFixed(1)} km/h`;

        // Event Stream
        const evContainer = document.getElementById("eventStream");
        if (state.events && state.events.length > 0) {
            evContainer.innerHTML = state.events.slice().reverse().map(ev => `
                <div class="event-item ${ev.risk_before > 0.6 ? 'danger' : ''}">
                    <span class="ev-reason">${ev.reason} (${ev.latency_ms}ms)</span>
                    <span class="ev-time">t = ${ev.timestamp}s</span>
                </div>
            `).join("");
        }
    }

    renderLoop() {
        this.render();
        requestAnimationFrame(() => this.renderLoop());
    }

    render() {
        const ctx = this.ctx;
        const w = this.displayWidth;
        const h = this.displayHeight;

        // Clear Canvas
        ctx.fillStyle = "#090d16";
        ctx.fillRect(0, 0, w, h);

        if (!this.latestState) {
            ctx.fillStyle = "#64748b";
            ctx.font = "14px Inter";
            ctx.textAlign = "center";
            ctx.fillText("Connecting to IRIS Simulation Pipeline...", w / 2, h / 2);
            return;
        }

        const state = this.latestState;
        const ego = state.ego;

        // Update Camera in Follow Mode
        if (this.followEgo && ego) {
            this.cameraX = ego.x;
            this.cameraY = ego.y + 15.0; // Keep ego slightly below center
        }

        // 1. Draw Road Surface & Markings
        this.drawRoad(state.road);

        // 2. Draw Risk Heatmap Layer
        if (this.showRisk && state.risk_matrix) {
            this.drawRiskHeatmap(state.risk_matrix, state.road);
        }

        // 3. Draw Surface Hazards
        if (this.showHazards && state.hazards) {
            this.drawHazards(state.hazards);
        }

        // 4. Draw Safe-Space Candidate Corridors
        if (this.showCorridors && state.corridors) {
            this.drawCorridors(state.corridors);
        }

        // 5. Draw Dynamic Actors, Predictions & Uncertainty
        if (state.actors) {
            this.drawActors(state.actors);
        }

        // 6. Draw Ego Vehicle & Active Planned Trajectory
        if (ego) {
            this.drawEgoVehicle(ego);
        }
    }

    drawRoad(road) {
        const ctx = this.ctx;
        const halfW = road.width / 2;
        const p1 = this.worldToScreen(-halfW, 0);
        const p2 = this.worldToScreen(halfW, road.length);

        // Asphalt Road Surface
        ctx.fillStyle = "#161f30";
        ctx.fillRect(p1.x, p2.y, (p2.x - p1.x), (p1.y - p2.y));

        // Road Boundaries
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p1.x, p2.y);
        ctx.moveTo(p2.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // Dashed Center / Lane Lines
        ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([8, 8]);
        ctx.beginPath();
        const centerLineX = this.worldToScreen(0, 0).x;
        ctx.moveTo(centerLineX, p1.y);
        ctx.lineTo(centerLineX, p2.y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    drawRiskHeatmap(matrix, road) {
        const ctx = this.ctx;
        const rows = matrix.length;
        if (rows === 0) return;
        const cols = matrix[0].length;

        const halfW = road.width / 2;
        const dy = road.length / rows;
        const dx = road.width / cols;

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const risk = matrix[r][c];
                if (risk < 0.15) continue;

                const worldX = -halfW + c * dx;
                const worldY = r * dy;
                const pt = this.worldToScreen(worldX, worldY);
                const sizeX = dx * this.scale;
                const sizeY = dy * this.scale;

                const alpha = Math.min(0.7, risk * 0.7);
                if (risk > 0.6) {
                    ctx.fillStyle = `rgba(239, 68, 68, ${alpha})`;
                } else if (risk > 0.35) {
                    ctx.fillStyle = `rgba(245, 158, 11, ${alpha})`;
                } else {
                    ctx.fillStyle = `rgba(6, 182, 212, ${alpha})`;
                }
                ctx.fillRect(pt.x, pt.y - sizeY, sizeX + 1, sizeY + 1);
            }
        }
    }

    drawHazards(hazards) {
        const ctx = this.ctx;
        for (const h of hazards) {
            const pt = this.worldToScreen(h.x, h.y);
            const w = h.width * this.scale;
            const l = h.length * this.scale;

            if (h.type === "POTHOLE") {
                ctx.fillStyle = "rgba(30, 41, 59, 0.95)";
                ctx.strokeStyle = "#ef4444";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.ellipse(pt.x, pt.y, w / 2, l / 2, 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();

                ctx.fillStyle = "#ef4444";
                ctx.font = "10px Outfit";
                ctx.textAlign = "center";
                ctx.fillText("POTHOLE", pt.x, pt.y + 3);
            } else if (h.type === "WATERLOGGING") {
                ctx.fillStyle = "rgba(6, 182, 212, 0.4)";
                ctx.strokeStyle = "rgba(6, 182, 212, 0.8)";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.ellipse(pt.x, pt.y, w / 2, l / 2, 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();

                ctx.fillStyle = "#06b6d4";
                ctx.font = "10px Outfit";
                ctx.textAlign = "center";
                ctx.fillText("WATER", pt.x, pt.y + 3);
            }
        }
    }

    drawCorridors(corridors) {
        const ctx = this.ctx;
        for (const c of corridors) {
            if (!c.points || c.points.length < 2) continue;

            ctx.lineWidth = c.is_selected ? 3.5 : 1.2;
            ctx.strokeStyle = c.is_selected ? "#10b981" : "rgba(16, 185, 129, 0.3)";
            ctx.beginPath();

            for (let i = 0; i < c.points.length; i++) {
                const pt = this.worldToScreen(c.points[i][0], c.points[i][1]);
                if (i === 0) ctx.moveTo(pt.x, pt.y);
                else ctx.lineTo(pt.x, pt.y);
            }
            ctx.stroke();
        }
    }

    drawActors(actors) {
        const ctx = this.ctx;
        for (const a of actors) {
            const pt = this.worldToScreen(a.x, a.y);

            // 1. Draw Uncertainty Ellipse
            if (this.showUncertainty && a.uncertainty) {
                const unc = a.uncertainty;
                const semiMajorPx = unc.semi_major * this.scale;
                const semiMinorPx = unc.semi_minor * this.scale;

                ctx.save();
                ctx.translate(pt.x, pt.y);
                ctx.rotate(-unc.angle); // invert for canvas
                ctx.fillStyle = "rgba(245, 158, 11, 0.15)";
                ctx.strokeStyle = "rgba(245, 158, 11, 0.5)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.ellipse(0, 0, semiMinorPx, semiMajorPx, 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
                ctx.restore();
            }

            // 2. Draw Multi-Hypothesis Prediction Ribbons
            if (this.showPredictions && a.hypotheses) {
                for (const hyp of a.hypotheses) {
                    if (!hyp.points || hyp.points.length < 2) continue;

                    ctx.lineWidth = 1.5;
                    ctx.strokeStyle = hyp.type === "SWERVING" ? "rgba(239, 68, 68, 0.6)" : "rgba(99, 102, 241, 0.5)";
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();

                    for (let i = 0; i < hyp.points.length; i++) {
                        const hPt = this.worldToScreen(hyp.points[i][0], hyp.points[i][1]);
                        if (i === 0) ctx.moveTo(hPt.x, hPt.y);
                        else ctx.lineTo(hPt.x, hPt.y);
                    }
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            }

            // 3. Draw Vehicle / Actor Bounding Box
            const w = a.width * this.scale;
            const l = a.length * this.scale;

            ctx.save();
            ctx.translate(pt.x, pt.y);
            ctx.rotate(-a.heading);

            // Actor Colors by Category
            let actorColor = "#94a3b8";
            let label = a.type;

            if (a.type.includes("CATTLE")) {
                actorColor = "#d97706"; // Amber brown
                label = "CATTLE";
            } else if (a.type.includes("RICKSHAW")) {
                actorColor = "#eab308"; // Auto yellow
                label = "AUTO";
            } else if (a.type.includes("MOTORCYCLE") || a.type.includes("TWO_WHEELER")) {
                actorColor = "#38bdf8"; // Cyan
                label = "BIKE";
            } else if (a.type.includes("PEDESTRIAN")) {
                actorColor = "#f43f5e"; // Pink/Rose
                label = "PED";
            } else if (a.type.includes("TRUCK")) {
                actorColor = "#a855f7"; // Purple
                label = "TRUCK";
            }

            ctx.fillStyle = actorColor;
            ctx.fillRect(-w / 2, -l / 2, w, l);
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1;
            ctx.strokeRect(-w / 2, -l / 2, w, l);

            // Heading pointer
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.moveTo(0, -l / 2 - 3);
            ctx.lineTo(-3, -l / 2 + 3);
            ctx.lineTo(3, -l / 2 + 3);
            ctx.fill();

            ctx.restore();

            // Label
            ctx.fillStyle = "#cbd5e1";
            ctx.font = "9px JetBrains Mono";
            ctx.textAlign = "center";
            ctx.fillText(`${label} ${(a.speed * 3.6).toFixed(0)}k`, pt.x, pt.y - l / 2 - 4);
        }
    }

    drawEgoVehicle(ego) {
        const ctx = this.ctx;
        const pt = this.worldToScreen(ego.x, ego.y);

        // 1. Draw Active Path
        if (ego.path && ego.path.length > 1) {
            ctx.lineWidth = 3.5;
            ctx.strokeStyle = "#06b6d4";
            ctx.shadowColor = "#06b6d4";
            ctx.shadowBlur = 10;
            ctx.beginPath();

            for (let i = 0; i < ego.path.length; i++) {
                const pathPt = this.worldToScreen(ego.path[i][0], ego.path[i][1]);
                if (i === 0) ctx.moveTo(pathPt.x, pathPt.y);
                else ctx.lineTo(pathPt.x, pathPt.y);
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
        }

        // 2. Draw Ego Body
        const w = ego.width * this.scale;
        const l = ego.length * this.scale;

        ctx.save();
        ctx.translate(pt.x, pt.y);
        ctx.rotate(-ego.heading);

        // Headlight Cones
        ctx.fillStyle = "rgba(6, 182, 212, 0.15)";
        ctx.beginPath();
        ctx.moveTo(0, -l / 2);
        ctx.lineTo(-w * 1.5, -l / 2 - 45);
        ctx.lineTo(w * 1.5, -l / 2 - 45);
        ctx.closePath();
        ctx.fill();

        // Ego Chassis
        ctx.fillStyle = "#0284c7"; // Electric blue
        ctx.shadowColor = "#0284c7";
        ctx.shadowBlur = 14;
        ctx.fillRect(-w / 2, -l / 2, w, l);
        ctx.shadowBlur = 0;

        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.strokeRect(-w / 2, -l / 2, w, l);

        // Windshield
        ctx.fillStyle = "rgba(15, 23, 42, 0.8)";
        ctx.fillRect(-w * 0.35, -l * 0.3, w * 0.7, l * 0.25);

        ctx.restore();
    }
}

window.addEventListener("DOMContentLoaded", () => {
    window.irisApp = new IRISApp();
});
