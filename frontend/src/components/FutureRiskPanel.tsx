import React, { useState } from 'react';
import { FullSimulationState } from '../types';
import { Shield, Clock, Flame, Activity, Layers } from 'lucide-react';

interface FutureRiskPanelProps {
  simState: FullSimulationState | null;
}

export const FutureRiskPanel: React.FC<FutureRiskPanelProps> = ({ simState }) => {
  const [horizonStep, setHorizonStep] = useState(1.0);
  const risk = simState?.risk;
  const matrix = simState?.risk_matrix || [];

  return (
    <div className="bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 p-4 shadow-xl flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-rose-400" />
          <h3 className="font-heading font-bold text-xs tracking-wider text-slate-200">FUTURE RISK FIELD</h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
          Horizon: 0.0s – 3.0s
        </span>
      </div>

      {/* Real-time Future Risk Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block">Peak Projected Risk</span>
          <span className={`font-mono text-base font-extrabold mt-0.5 block ${
            (risk?.peak_future_risk ?? 0) > 0.6 ? 'text-rose-400' : (risk?.peak_future_risk ?? 0) > 0.35 ? 'text-amber-400' : 'text-cyan-400'
          }`}>
            {risk?.peak_future_risk.toFixed(3) ?? '0.000'}
          </span>
        </div>
        <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block">Current Risk R(t0)</span>
          <span className="font-mono text-base font-extrabold text-cyan-400 mt-0.5 block">
            {risk?.current_risk.toFixed(3) ?? '0.000'}
          </span>
        </div>
      </div>

      {/* 2D Discrete Tensor Heatmap Slice */}
      <div className="flex-1 bg-slate-950 rounded-xl border border-slate-800/90 p-2.5 flex flex-col justify-between overflow-hidden">
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1.5 font-mono">
          <span className="flex items-center gap-1"><Layers className="w-3 h-3 text-cyan-400" /> Spatial Tensor Slice R(x, y | t=+{horizonStep.toFixed(1)}s)</span>
          <span className="text-slate-500">20x60 Grid</span>
        </div>

        {/* Heatmap visualization representation */}
        <div className="flex-1 rounded border border-slate-800/60 overflow-hidden flex flex-col justify-center p-1 bg-slate-900/60">
          {matrix.length > 0 ? (
            <div className="grid gap-[1px] h-full w-full" style={{ gridTemplateRows: `repeat(${matrix.length}, minmax(0, 1fr))` }}>
              {matrix.map((row, rIdx) => (
                <div key={rIdx} className="flex h-full w-full gap-[1px]">
                  {row.map((val, cIdx) => {
                    const scaledVal = Math.min(1.0, val * (1.0 + horizonStep * 0.2));
                    let bg = 'rgba(15, 23, 42, 0.4)';
                    if (scaledVal > 0.6) bg = `rgba(239, 68, 68, ${Math.min(0.9, scaledVal)})`;
                    else if (scaledVal > 0.35) bg = `rgba(245, 158, 11, ${Math.min(0.8, scaledVal)})`;
                    else if (scaledVal > 0.15) bg = `rgba(6, 182, 212, ${Math.min(0.6, scaledVal)})`;
                    return <div key={cIdx} className="flex-1 h-full rounded-[0.5px]" style={{ backgroundColor: bg }} />;
                  })}
                </div>
              ))}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
              Generating Spatiotemporal Risk Field...
            </div>
          )}
        </div>

        {/* Time Slider */}
        <div className="mt-2 pt-2 border-t border-slate-800 flex items-center gap-3">
          <Clock className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <input
            type="range"
            min="0.0"
            max="3.0"
            step="0.2"
            value={horizonStep}
            onChange={(e) => setHorizonStep(parseFloat(e.target.value))}
            className="w-full accent-cyan-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
          <span className="font-mono text-[11px] font-bold text-cyan-400 w-12 text-right">+{horizonStep.toFixed(1)}s</span>
        </div>
      </div>

      {/* Explainability Risk Weight Breakdown */}
      <div className="mt-2.5 grid grid-cols-4 gap-1 text-[9px] font-mono text-center">
        <div className="bg-slate-950/60 p-1 rounded border border-slate-800/60">
          <span className="text-slate-500 block">Traffic</span>
          <span className="text-slate-200 font-bold">40%</span>
        </div>
        <div className="bg-slate-950/60 p-1 rounded border border-slate-800/60">
          <span className="text-slate-500 block">Surface</span>
          <span className="text-slate-200 font-bold">25%</span>
        </div>
        <div className="bg-slate-950/60 p-1 rounded border border-slate-800/60">
          <span className="text-slate-500 block">Collision</span>
          <span className="text-slate-200 font-bold">20%</span>
        </div>
        <div className="bg-slate-950/60 p-1 rounded border border-slate-800/60">
          <span className="text-slate-500 block">Boundary</span>
          <span className="text-slate-200 font-bold">15%</span>
        </div>
      </div>
    </div>
  );
};
