import React from 'react';
import { FullSimulationState } from '../types';
import { CanvasVisualizer } from '../components/CanvasVisualizer';
import { FutureRiskPanel } from '../components/FutureRiskPanel';
import { TelemetrySidebar } from '../components/TelemetrySidebar';
import { ReplanningEventLog } from '../components/ReplanningEventLog';
import { ShieldCheck, Activity, AlertCircle, Compass, Zap, Layers } from 'lucide-react';

interface DashboardPageProps {
  simState: FullSimulationState | null;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ simState }) => {
  const metrics = simState?.metrics;

  return (
    <div className="flex-1 p-3 flex flex-col gap-3 h-[calc(100vh-64px)] overflow-hidden">
      {/* TOP 3-COLUMN MAIN DASHBOARD ROW */}
      <div className="flex-1 grid grid-cols-[1.4fr_1fr_320px] gap-3 min-h-0 overflow-hidden">
        {/* LEFT: LIVE SIMULATION CANVAS */}
        <section className="flex flex-col h-full overflow-hidden">
          <CanvasVisualizer simState={simState} heightClass="h-full" />
        </section>

        {/* CENTER: FUTURE RISK FIELD */}
        <section className="flex flex-col h-full overflow-hidden">
          <FutureRiskPanel simState={simState} />
        </section>

        {/* RIGHT: VEHICLE INTELLIGENCE */}
        <section className="flex flex-col h-full overflow-hidden">
          <TelemetrySidebar simState={simState} />
        </section>
      </div>

      {/* BOTTOM ROW: METRICS + REPLANNING EVENT LOG */}
      <div className="h-44 grid grid-cols-[1fr_1fr] gap-3 shrink-0">
        {/* METRICS SUMMARY STRIP */}
        <div className="bg-slate-900/90 backdrop-blur-md rounded-xl border border-slate-800 p-3 shadow-xl flex flex-col justify-between overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h4 className="font-heading font-bold text-xs tracking-wider text-slate-200">REAL-TIME MISSION METRICS</h4>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 font-bold">
              Completion: {metrics?.completion_rate?.toFixed(1) ?? '0.0'}%
            </span>
          </div>

          <div className="grid grid-cols-5 gap-2 text-xs font-mono my-1">
            <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
              <span className="text-[9px] text-slate-500 block">Min Clearance</span>
              <span className="text-cyan-400 font-bold text-sm mt-0.5 block">{metrics?.min_clearance?.toFixed(2) ?? '0.00'} m</span>
            </div>
            <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
              <span className="text-[9px] text-slate-500 block">Collisions</span>
              <span className="text-emerald-400 font-bold text-sm mt-0.5 block">{metrics?.collision_count ?? 0}</span>
            </div>
            <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
              <span className="text-[9px] text-slate-500 block">Near Misses</span>
              <span className="text-amber-400 font-bold text-sm mt-0.5 block">{metrics?.near_collision_count ?? 0}</span>
            </div>
            <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
              <span className="text-[9px] text-slate-500 block">Replans</span>
              <span className="text-indigo-400 font-bold text-sm mt-0.5 block">{metrics?.replan_count ?? 0}</span>
            </div>
            <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
              <span className="text-[9px] text-slate-500 block">Smoothness</span>
              <span className="text-slate-200 font-bold text-sm mt-0.5 block">{metrics?.smoothness_score?.toFixed(3) ?? '1.000'}</span>
            </div>
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/60 font-mono">
            <span>Scenario: <strong className="text-slate-200">{simState?.scenario_id ?? 'SUDDEN_CATTLE_CROSSING'}</strong></span>
            <span>Planner: <strong className="text-cyan-400 uppercase">{simState?.planner_mode ?? 'IRIS'}</strong></span>
            <span>Sim Time: <strong className="text-slate-200">{simState?.sim_time?.toFixed(2) ?? '0.00'} s</strong></span>
          </div>
        </div>

        {/* EVENT LOG STREAM */}
        <div className="h-full overflow-hidden">
          <ReplanningEventLog events={simState?.events || []} />
        </div>
      </div>
    </div>
  );
};
