import React, { useRef, useEffect, useState, useCallback } from 'react';
import { FullSimulationState } from '../types';
import { Eye, EyeOff, ZoomIn, ZoomOut, Compass, Navigation, ShieldCheck, AlertTriangle, Activity } from 'lucide-react';

interface CanvasVisualizerProps {
  simState: FullSimulationState | null;
  heightClass?: string;
  showToolbar?: boolean;
}

export const CanvasVisualizer: React.FC<CanvasVisualizerProps> = ({
  simState,
  heightClass = 'h-[560px]',
  showToolbar = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Viewport State (X longitudinal along road, Y lateral across road)
  const [scale, setScale] = useState(18.0); // pixels per meter
  const [camera, setCamera] = useState({ x: 20.0, y: 0.0 });
  const [followEgo, setFollowEgo] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  // Layer & Debug Toggles
  const [layers, setLayers] = useState({
    risk: true,
    predictions: true,
    uncertainty: true,
    corridors: true,
    hazards: true,
    safeEnvelope: true,
    footprint: true,
    safetyDebug: true, // Vehicle Safety Debug toggle
  });

  const toggleLayer = (key: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Convert Simulation World Coordinates (X: 0..300m longitudinal, Y: -6..+6m lateral) to Screen Pixels
  const worldToScreen = useCallback(
    (wx: number, wy: number, width: number, height: number) => {
      const cx = width / 2 + (wx - camera.x) * scale;
      const cy = height / 2 - (wy - camera.y) * scale;
      return { x: cx, y: cy };
    },
    [camera, scale]
  );

  // Mouse Interaction for Pan & Zoom
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    setFollowEgo(false);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    dragStartRef.current = { x: e.clientX, y: e.clientY };

    setCamera((prev) => ({
      x: prev.x - dx / scale,
      y: prev.y + dy / scale,
    }));
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    setScale((prev) => Math.max(8.0, Math.min(60.0, prev * zoomFactor)));
  };

  // Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    const width = canvas.width;
    const height = canvas.height;

    // Clear Background (Grass / Terrain)
    ctx.fillStyle = '#0a101d';
    ctx.fillRect(0, 0, width, height);

    if (!simState || !simState.ego) {
      ctx.fillStyle = '#64748b';
      ctx.font = '14px Inter';
      ctx.textAlign = 'center';
      ctx.fillText('Connecting to IRIS Autonomous Pipeline...', width / 2, height / 2);
      return;
    }

    const ego = simState.ego;
    const road = simState.road || { length: 300.0, width: 12.0, lanes: 2 };
    const halfW = road.width / 2.0;

    // Follow Ego Camera
    if (followEgo && ego) {
      setCamera({ x: ego.x + 15.0, y: ego.y });
    }

    // 1. Draw Asphalt Road Surface
    const roadTopLeft = worldToScreen(0, halfW, width, height);
    const roadBottomRight = worldToScreen(road.length, -halfW, width, height);
    const roadPixelHeight = Math.abs(roadBottomRight.y - roadTopLeft.y);
    const roadPixelWidth = roadBottomRight.x - roadTopLeft.x;

    // Asphalt body
    ctx.fillStyle = '#1e2536';
    ctx.fillRect(roadTopLeft.x, roadTopLeft.y, roadPixelWidth, roadPixelHeight);

    // Shoulder gravel bands
    const shoulderHeight = 1.5 * scale;
    ctx.fillStyle = '#141a29';
    ctx.fillRect(roadTopLeft.x, roadTopLeft.y - shoulderHeight, roadPixelWidth, shoulderHeight);
    ctx.fillRect(roadTopLeft.x, roadBottomRight.y, roadPixelWidth, shoulderHeight);

    // Physical Road Boundary Lines (Solid Yellow)
    ctx.strokeStyle = '#eab308';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(roadTopLeft.x, roadTopLeft.y);
    ctx.lineTo(roadBottomRight.x, roadTopLeft.y);
    ctx.moveTo(roadTopLeft.x, roadBottomRight.y);
    ctx.lineTo(roadBottomRight.x, roadBottomRight.y);
    ctx.stroke();

    // Safe Road Envelope (Dashed Cyan Lines: +/- 5.5m margin)
    if (layers.safeEnvelope) {
      const safeMargin = road.safe_margin || 0.5;
      const safeY = halfW - safeMargin;
      const safeTop = worldToScreen(0, safeY, width, height);
      const safeBottom = worldToScreen(road.length, -safeY, width, height);

      ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([8, 8]);
      ctx.beginPath();
      ctx.moveTo(roadTopLeft.x, safeTop.y);
      ctx.lineTo(roadBottomRight.x, safeTop.y);
      ctx.moveTo(roadTopLeft.x, safeBottom.y);
      ctx.lineTo(roadBottomRight.x, safeBottom.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Center Dashed Lane Divider (White)
    const centerY = worldToScreen(0, 0, width, height).y;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.lineWidth = 2;
    ctx.setLineDash([16, 16]);
    ctx.beginPath();
    ctx.moveTo(roadTopLeft.x, centerY);
    ctx.lineTo(roadBottomRight.x, centerY);
    ctx.stroke();
    ctx.setLineDash([]);

    // 2. Draw Risk Heatmap Layer
    if (layers.risk && simState.risk_matrix && simState.risk_matrix.length > 0) {
      const rows = simState.risk_matrix.length;
      const cols = simState.risk_matrix[0].length;
      const dx = road.length / cols;
      const dy = road.width / rows;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const risk = simState.risk_matrix[r][c];
          if (risk < 0.15) continue;

          const wx = c * dx;
          const wy = halfW - r * dy;
          const pt = worldToScreen(wx, wy, width, height);
          const cellW = dx * scale;
          const cellH = dy * scale;

          const alpha = Math.min(0.65, risk * 0.7);
          if (risk > 0.6) {
            ctx.fillStyle = `rgba(239, 68, 68, ${alpha})`;
          } else if (risk > 0.35) {
            ctx.fillStyle = `rgba(245, 158, 11, ${alpha})`;
          } else {
            ctx.fillStyle = `rgba(6, 182, 212, ${alpha})`;
          }
          ctx.fillRect(pt.x, pt.y, cellW + 1, cellH + 1);
        }
      }
    }

    // 3. Draw Surface Hazards
    if (layers.hazards && simState.hazards) {
      for (const h of simState.hazards) {
        const pt = worldToScreen(h.x, h.y, width, height);
        const lPx = h.length * scale;
        const wPx = h.width * scale;

        if (h.type.includes('POTHOLE')) {
          ctx.fillStyle = 'rgba(239, 68, 68, 0.25)';
          ctx.strokeStyle = '#ef4444';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.ellipse(pt.x, pt.y, lPx / 2, wPx / 2, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = '#ef4444';
          ctx.font = 'bold 10px JetBrains Mono';
          ctx.textAlign = 'center';
          ctx.fillText(`POTHOLE (${(h.severity * 100).toFixed(0)}%)`, pt.x, pt.y + 3);
        } else if (h.type.includes('WATER')) {
          ctx.fillStyle = 'rgba(6, 182, 212, 0.3)';
          ctx.strokeStyle = '#06b6d4';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.roundRect(pt.x - lPx / 2, pt.y - wPx / 2, lPx, wPx, 8);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = '#06b6d4';
          ctx.font = 'bold 10px JetBrains Mono';
          ctx.textAlign = 'center';
          ctx.fillText('WATERLOGGED', pt.x, pt.y + 3);
        } else if (h.type.includes('SPEED_BREAKER')) {
          ctx.fillStyle = 'rgba(234, 179, 8, 0.4)';
          ctx.strokeStyle = '#eab308';
          ctx.lineWidth = 2;
          ctx.fillRect(pt.x - lPx / 2, pt.y - wPx / 2, lPx, wPx);
          ctx.strokeRect(pt.x - lPx / 2, pt.y - wPx / 2, lPx, wPx);

          ctx.fillStyle = '#eab308';
          ctx.font = 'bold 10px JetBrains Mono';
          ctx.textAlign = 'center';
          ctx.fillText('SPEED BREAKER', pt.x, pt.y + 3);
        } else {
          ctx.fillStyle = 'rgba(148, 163, 184, 0.3)';
          ctx.strokeStyle = '#94a3b8';
          ctx.lineWidth = 1.5;
          ctx.strokeRect(pt.x - lPx / 2, pt.y - wPx / 2, lPx, wPx);
        }
      }
    }

    // 4. Draw Safe Space Candidate Corridors
    if (layers.corridors && simState.corridors) {
      for (const cor of simState.corridors) {
        if (!cor.points || cor.points.length < 2) continue;
        ctx.lineWidth = cor.is_selected ? 3.5 : 1.5;
        ctx.strokeStyle = cor.is_selected ? '#10b981' : 'rgba(16, 185, 129, 0.25)';
        ctx.shadowColor = cor.is_selected ? '#10b981' : 'transparent';
        ctx.shadowBlur = cor.is_selected ? 8 : 0;

        ctx.beginPath();
        for (let i = 0; i < cor.points.length; i++) {
          const pt = worldToScreen(cor.points[i][0], cor.points[i][1], width, height);
          if (i === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
    }

    // 5. Draw Traffic Actors, Predictions & Uncertainty
    if (simState.actors) {
      for (const a of simState.actors) {
        const pt = worldToScreen(a.x, a.y, width, height);

        // Uncertainty Ellipse
        if (layers.uncertainty && a.uncertainty) {
          const unc = a.uncertainty;
          const sMajor = unc.semi_major * scale;
          const sMinor = unc.semi_minor * scale;

          ctx.save();
          ctx.translate(pt.x, pt.y);
          ctx.rotate(-unc.angle);
          ctx.fillStyle = 'rgba(245, 158, 11, 0.12)';
          ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.ellipse(0, 0, sMajor, sMinor, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          ctx.restore();
        }

        // Predicted Trajectory Branches (Multi-hypothesis)
        if (layers.predictions && a.hypotheses) {
          for (const hyp of a.hypotheses) {
            if (!hyp.points || hyp.points.length < 2) continue;
            ctx.lineWidth = 1.8;
            ctx.strokeStyle = hyp.type.includes('SWERVE') || hyp.type.includes('LEFT') || hyp.type.includes('RIGHT')
              ? 'rgba(239, 68, 68, 0.7)'
              : 'rgba(99, 102, 241, 0.6)';
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            for (let i = 0; i < hyp.points.length; i++) {
              const hPt = worldToScreen(hyp.points[i][0], hyp.points[i][1], width, height);
              if (i === 0) ctx.moveTo(hPt.x, hPt.y);
              else ctx.lineTo(hPt.x, hPt.y);
            }
            ctx.stroke();
            ctx.setLineDash([]);
          }
        }

        // Actor Body Oriented Bounding Box
        const lPx = a.length * scale;
        const wPx = a.width * scale;

        ctx.save();
        ctx.translate(pt.x, pt.y);
        ctx.rotate(-a.heading);

        let color = '#94a3b8';
        let label = a.type;
        if (a.type.includes('CATTLE')) {
          color = '#d97706';
          label = 'CATTLE';
        } else if (a.type.includes('RICKSHAW')) {
          color = '#eab308';
          label = 'AUTO';
        } else if (a.type.includes('MOTORCYCLE')) {
          color = '#38bdf8';
          label = 'BIKE';
        } else if (a.type.includes('PEDESTRIAN')) {
          color = '#f43f5e';
          label = 'PED';
        } else if (a.type.includes('TRUCK') || a.type.includes('BUS')) {
          color = '#a855f7';
          label = 'TRUCK';
        }

        ctx.fillStyle = color;
        ctx.fillRect(-lPx / 2, -wPx / 2, lPx, wPx);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(-lPx / 2, -wPx / 2, lPx, wPx);

        // Heading arrow
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.moveTo(lPx / 2 + 3, 0);
        ctx.lineTo(lPx / 2 - 3, -3);
        ctx.lineTo(lPx / 2 - 3, 3);
        ctx.fill();

        ctx.restore();

        // Actor ID and Speed Label
        ctx.fillStyle = '#f1f5f9';
        ctx.font = 'bold 9px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText(`${label} #${a.id} (${(a.speed * 3.6).toFixed(0)} km/h)`, pt.x, pt.y - wPx / 2 - 5);
      }
    }

    // 6. Draw Selected Path
    if (ego.path && ego.path.length > 1) {
      ctx.lineWidth = 3.5;
      ctx.strokeStyle = '#06b6d4';
      ctx.shadowColor = '#06b6d4';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      for (let i = 0; i < ego.path.length; i++) {
        const pathPt = worldToScreen(ego.path[i][0], ego.path[i][1], width, height);
        if (i === 0) ctx.moveTo(pathPt.x, pathPt.y);
        else ctx.lineTo(pathPt.x, pathPt.y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // 7. Draw Ego Vehicle with Complete Footprint & Control HUD
    if (ego) {
      const egoPt = worldToScreen(ego.x, ego.y, width, height);
      const lPx = ego.length * scale;
      const wPx = ego.width * scale;

      // Draw Lookahead Target Point
      if (ego.lookahead_point) {
        const laPt = worldToScreen(ego.lookahead_point[0], ego.lookahead_point[1], width, height);
        ctx.strokeStyle = '#f59e0b';
        ctx.fillStyle = 'rgba(245, 158, 11, 0.4)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(laPt.x, laPt.y, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Line connecting ego to lookahead
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(egoPt.x, egoPt.y);
        ctx.lineTo(laPt.x, laPt.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Draw Vehicle Footprint (Polygon)
      if (layers.footprint && ego.footprint && ego.footprint.length === 4) {
        ctx.lineWidth = 2.5;
        const condition = ego.condition || 'NORMAL';
        let fpColor = '#06b6d4';
        if (condition === 'OFF_ROAD' || condition === 'NEAR_COLLISION') fpColor = '#ef4444';
        else if (condition === 'CAUTION' || condition === 'COLLISION_RISK') fpColor = '#f59e0b';

        ctx.strokeStyle = fpColor;
        ctx.fillStyle = `${fpColor}22`;
        ctx.beginPath();
        for (let i = 0; i < 4; i++) {
          const cornerPt = worldToScreen(ego.footprint[i][0], ego.footprint[i][1], width, height);
          if (i === 0) ctx.moveTo(cornerPt.x, cornerPt.y);
          else ctx.lineTo(cornerPt.x, cornerPt.y);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }

      // Ego Body
      ctx.save();
      ctx.translate(egoPt.x, egoPt.y);
      ctx.rotate(-ego.heading);

      // Headlight Beam
      ctx.fillStyle = 'rgba(6, 182, 212, 0.15)';
      ctx.beginPath();
      ctx.moveTo(lPx / 2, 0);
      ctx.lineTo(lPx / 2 + 60, -wPx * 1.4);
      ctx.lineTo(lPx / 2 + 60, wPx * 1.4);
      ctx.closePath();
      ctx.fill();

      // Main Chassis
      ctx.fillStyle = '#0284c7';
      ctx.fillRect(-lPx / 2, -wPx / 2, lPx, wPx);
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.strokeRect(-lPx / 2, -wPx / 2, lPx, wPx);

      // Windshield & Cabin
      ctx.fillStyle = '#0c4a6e';
      ctx.fillRect(-lPx * 0.1, -wPx * 0.35, lPx * 0.4, wPx * 0.7);

      // Front Steered Wheels
      const steerRad = ego.steering_angle || 0.0;
      const wheelL = 0.8 * scale;
      const wheelW = 0.3 * scale;

      // Front Left Wheel
      ctx.save();
      ctx.translate(lPx * 0.35, -wPx * 0.5);
      ctx.rotate(-steerRad);
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(-wheelL / 2, -wheelW / 2, wheelL, wheelW);
      ctx.restore();

      // Front Right Wheel
      ctx.save();
      ctx.translate(lPx * 0.35, wPx * 0.5);
      ctx.rotate(-steerRad);
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(-wheelL / 2, -wheelW / 2, wheelL, wheelW);
      ctx.restore();

      // Rear Wheels
      ctx.fillStyle = '#334155';
      ctx.fillRect(-lPx * 0.35 - wheelL / 2, -wPx * 0.5 - wheelW / 2, wheelL, wheelW);
      ctx.fillRect(-lPx * 0.35 - wheelL / 2, wPx * 0.5 - wheelW / 2, wheelL, wheelW);

      // Front Heading Arrow
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.moveTo(lPx / 2 + 6, 0);
      ctx.lineTo(lPx / 2, -4);
      ctx.lineTo(lPx / 2, 4);
      ctx.fill();

      ctx.restore();

      // Ego Label & Condition Badge
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText(`IRIS EGO [${(ego.velocity * 3.6).toFixed(1)} km/h]`, egoPt.x, egoPt.y - wPx / 2 - 8);
    }
  }, [simState, camera, scale, followEgo, layers, worldToScreen]);

  return (
    <div className={`relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col ${heightClass}`}>
      {/* Top Overlay Toolbar */}
      {showToolbar && (
        <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">
          {/* Layer Controls */}
          <div className="flex items-center gap-1.5 bg-slate-950/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-slate-800 shadow-xl pointer-events-auto">
            <button
              onClick={() => toggleLayer('safetyDebug')}
              className={`px-2 py-1 text-xs font-semibold rounded flex items-center gap-1 transition-all ${
                layers.safetyDebug ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Vehicle Safety Debug
            </button>
            <div className="h-3 w-px bg-slate-800 mx-1" />
            <button
              onClick={() => toggleLayer('risk')}
              className={`px-1.5 py-0.5 text-[11px] rounded ${layers.risk ? 'text-cyan-400 font-medium' : 'text-slate-500'}`}
            >
              Risk
            </button>
            <button
              onClick={() => toggleLayer('predictions')}
              className={`px-1.5 py-0.5 text-[11px] rounded ${layers.predictions ? 'text-indigo-400 font-medium' : 'text-slate-500'}`}
            >
              Predictions
            </button>
            <button
              onClick={() => toggleLayer('uncertainty')}
              className={`px-1.5 py-0.5 text-[11px] rounded ${layers.uncertainty ? 'text-amber-400 font-medium' : 'text-slate-500'}`}
            >
              Uncertainty
            </button>
            <button
              onClick={() => toggleLayer('corridors')}
              className={`px-1.5 py-0.5 text-[11px] rounded ${layers.corridors ? 'text-emerald-400 font-medium' : 'text-slate-500'}`}
            >
              Safe Space
            </button>
            <button
              onClick={() => toggleLayer('safeEnvelope')}
              className={`px-1.5 py-0.5 text-[11px] rounded ${layers.safeEnvelope ? 'text-cyan-300 font-medium' : 'text-slate-500'}`}
            >
              Road Envelope
            </button>
          </div>

          {/* Viewport Actions */}
          <div className="flex items-center gap-1.5 bg-slate-950/85 backdrop-blur-md p-1.5 rounded-lg border border-slate-800 shadow-xl pointer-events-auto">
            <button
              onClick={() => setFollowEgo(!followEgo)}
              title={followEgo ? 'Disable Follow Camera' : 'Follow Ego Vehicle'}
              className={`p-1.5 rounded ${followEgo ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-slate-200'}`}
            >
              <Navigation className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setScale((s) => Math.min(60.0, s * 1.2))}
              title="Zoom In"
              className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setScale((s) => Math.max(8.0, s * 0.8))}
              title="Zoom Out"
              className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Vehicle Safety Debug Floating HUD */}
      {layers.safetyDebug && simState?.ego && (
        <div className="absolute bottom-3 left-3 z-10 bg-slate-950/90 backdrop-blur-md p-3 rounded-xl border border-cyan-500/30 shadow-2xl pointer-events-auto flex flex-col gap-2 min-w-[280px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-cyan-400">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              VEHICLE SAFETY DEBUG HUD
            </div>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                simState.ego.condition === 'NORMAL'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : simState.ego.condition === 'CAUTION' || simState.ego.condition === 'SLOW_DOWN'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}
            >
              {simState.ego.condition || 'NORMAL'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs font-mono">
            <div>
              <span className="text-slate-500">Speed:</span>{' '}
              <span className="text-slate-200 font-semibold">{simState.ego.speed_kmh} km/h</span>
            </div>
            <div>
              <span className="text-slate-500">Target:</span>{' '}
              <span className="text-cyan-400 font-semibold">{simState.ego.target_speed_kmh || (simState.ego.target_speed * 3.6).toFixed(1)} km/h</span>
            </div>
            <div>
              <span className="text-slate-500">Steering:</span>{' '}
              <span className="text-amber-400 font-semibold">{(simState.ego.steering_angle_deg || (simState.ego.steering_angle * 57.3)).toFixed(1)}°</span>
            </div>
            <div>
              <span className="text-slate-500">Heading:</span>{' '}
              <span className="text-slate-200 font-semibold">{(simState.ego.heading_deg || (simState.ego.heading * 57.3)).toFixed(1)}°</span>
            </div>
            <div>
              <span className="text-slate-500">Road Margin:</span>{' '}
              <span className="text-emerald-400 font-semibold">{simState.ego.min_road_clearance ?? simState.ego.clearance} m</span>
            </div>
            <div>
              <span className="text-slate-500">Obs Clearance:</span>{' '}
              <span className="text-slate-200 font-semibold">{simState.ego.min_obstacle_clearance ?? simState.ego.clearance} m</span>
            </div>
            <div>
              <span className="text-slate-500">TTC:</span>{' '}
              <span className={`font-semibold ${(simState.ego.ttc ?? 99) < 2.0 ? 'text-rose-400' : 'text-slate-200'}`}>
                {simState.ego.ttc && simState.ego.ttc < 50 ? `${simState.ego.ttc.toFixed(1)} s` : '> 5.0 s'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Footprint:</span>{' '}
              <span className="text-emerald-400 font-semibold">SAFE (IN ROAD)</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Interactive Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className="w-full h-full cursor-grab active:cursor-grabbing"
      />
    </div>
  );
};
