import React, { useState } from 'react';
import { FullSimulationState } from '../types';
import { CanvasVisualizer } from '../components/CanvasVisualizer';
import { Shield, Clock, Sliders, AlertTriangle } from 'lucide-react';

interface RiskFieldPageProps {
  simState: FullSimulationState | null;
}

export const RiskFieldPage: React.FC<RiskFieldPageProps> = ({ simState }) => {
  const [timeOffset, setTimeOffset] = useState(0.0);

  return (
    <div className="flex-1 p-6 flex flex-col gap-6 h-[calc(100vh-64px)] overflow-y-auto">
      <div>
        <h2 className="font-heading font-extrabold text-2xl text-white">Spatiotemporal Future Risk Field</h2>
        <p className="text-xs text-slate-400 mt-1">4D Risk Tensor R(t, x, y) Projecting Dynamic Collision Risk Across 0.0s to 3.0s Horizon</p>
      </div>

      <div className="grid grid-cols-[1fr_360px] gap-6">
        {/* CENTER VISUALIZER */}
        <div className="flex flex-col gap-4">
          <CanvasVisualizer simState={simState} heightClass="h-[480px]" />

          {/* TIME HORIZON SLIDER */}
          <div className="bg-slate-900/80 backdrop-blur-md p-4 rounded-2xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-cyan-400" />
              <div>
                <span className="text-xs font-bold text-slate-200 block">Horizon Timestep Offset: t = +{timeOffset.toFixed(1)}s</span>
                <span className="text-[10px] text-slate-400">Inspecting projected risk distribution {timeOffset.toFixed(1)}s into the future</span>
              </div>
            </div>

            <div className="flex items-center gap-4 w-64">
              <input
                type="range"
                min="0.0"
                max="3.0"
                step="0.2"
                value={timeOffset}
                onChange={(e) => setTimeOffset(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <span className="font-mono text-xs font-bold text-cyan-400 w-12 text-right">+{timeOffset.toFixed(1)}s</span>
            </div>
          </div>
        </div>

        {/* RIGHT RISK BREAKDOWN CARDS */}
        <div className="flex flex-col gap-4">
          <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl">
            <h3 className="font-heading font-bold text-sm text-slate-200 mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              Risk Formulation (Explainable Fusion)
            </h3>

            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[11px] text-cyan-300 mb-4">
              R(x, y, t) = w_T·Traffic + w_S·Surface + w_C·Collision + w_B·Boundary
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="flex justify-between items-center p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-slate-400">Traffic Dynamic Weight (w_T)</span>
                <span className="font-mono font-bold text-slate-200">0.40</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-slate-400">Surface Hazard Weight (w_S)</span>
                <span className="font-mono font-bold text-slate-200">0.25</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-slate-400">Collision Boundary Weight (w_C)</span>
                <span className="font-mono font-bold text-slate-200">0.20</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-slate-400">Road Boundary Weight (w_B)</span>
                <span className="font-mono font-bold text-slate-200">0.15</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl">
            <h3 className="font-heading font-bold text-sm text-slate-200 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              Real-Time Risk Diagnostics
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-col">
                <span className="text-[10px] text-slate-400">Current Instant Risk</span>
                <span className="font-mono text-xl font-extrabold text-cyan-400 mt-1">
                  {simState?.risk.current_risk.toFixed(3) ?? '0.000'}
                </span>
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-col">
                <span className="text-[10px] text-slate-400">Peak Future Risk</span>
                <span className="font-mono text-xl font-extrabold text-rose-400 mt-1">
                  {simState?.risk.peak_future_risk.toFixed(3) ?? '0.000'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
