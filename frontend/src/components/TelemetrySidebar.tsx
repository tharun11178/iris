import React from 'react';
import { FullSimulationState } from '../types';
import { Gauge, Compass, ShieldAlert, Cpu, CheckCircle2, ShieldCheck, Activity, AlertTriangle, Radio } from 'lucide-react';

interface TelemetrySidebarProps {
  simState: FullSimulationState | null;
}

export const TelemetrySidebar: React.FC<TelemetrySidebarProps> = ({ simState }) => {
  const ego = simState?.ego;
  const metrics = simState?.metrics;
  const decisionState = ego?.decision_state || 'NORMAL_DRIVING';
  const condition = ego?.condition || 'NORMAL';
  const planner = simState?.planner_mode || 'IRIS_SAFE_SPACE';

  const getConditionColor = (cond: string) => {
    switch (cond) {
      case 'OFF_ROAD':
      case 'NEAR_COLLISION':
      case 'COLLISION_RISK':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse';
      case 'CAUTION':
      case 'SLOW_DOWN':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'SAFETY_HOLD':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/40';
      case 'GOAL_REACHED':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
    }
  };

  return (
    <aside className="w-80 flex flex-col gap-3 overflow-y-auto pr-1 h-full">
      {/* 1. VEHICLE INTELLIGENCE & TELEMETRY HEADER */}
      <div className="bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 p-4 shadow-xl">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
            <h3 className="font-heading font-bold text-xs tracking-wider text-slate-200">VEHICLE INTELLIGENCE</h3>
          </div>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getConditionColor(condition)} font-mono uppercase`}>
            {condition}
          </span>
        </div>

        {/* Circular Speedometer Gauge */}
        <div className="flex justify-center my-2">
          <div className="w-28 h-28 rounded-full bg-slate-950 border-4 border-cyan-500/40 shadow-[0_0_20px_rgba(6,182,212,0.25)] flex flex-col items-center justify-center relative">
            <span className="font-heading font-extrabold text-2xl text-white tracking-tighter">
              {ego ? ego.speed_kmh.toFixed(1) : '0.0'}
            </span>
            <span className="text-[9px] font-bold text-cyan-400 tracking-widest mt-[-2px]">KM/H</span>
            <span className="text-[8px] text-slate-400 mt-0.5 font-mono">
              Target: {ego ? (ego.target_speed * 3.6).toFixed(1) : '0.0'}
            </span>
          </div>
        </div>

        {/* 6-Core Intelligence Telemetry Grid */}
        <div className="grid grid-cols-2 gap-2 mt-2">
          <div className="bg-slate-950/70 p-2 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Steering Angle</span>
            <span className="font-mono text-xs font-bold text-amber-400 mt-0.5 block">
              {ego ? `${(ego.steering_angle * 57.2958).toFixed(1)}°` : '0.0°'}
            </span>
          </div>

          <div className="bg-slate-950/70 p-2 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Acceleration / Brake</span>
            <span className={`font-mono text-xs font-bold mt-0.5 block ${
              (ego?.acceleration ?? 0) < 0 ? 'text-rose-400' : 'text-emerald-400'
            }`}>
              {ego ? `${ego.acceleration >= 0 ? '+' : ''}${ego.acceleration.toFixed(2)} m/s²` : '0.00 m/s²'}
            </span>
          </div>

          <div className="bg-slate-950/70 p-2 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Time to Collision (TTC)</span>
            <span className={`font-mono text-xs font-bold mt-0.5 block ${
              (ego?.ttc ?? 99) < 2.0 ? 'text-rose-400' : 'text-slate-200'
            }`}>
              {ego?.ttc && ego.ttc < 50 ? `${ego.ttc.toFixed(1)} s` : '> 5.0 s'}
            </span>
          </div>

          <div className="bg-slate-950/70 p-2 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Min Clearance</span>
            <span className="font-mono text-xs font-bold text-cyan-400 mt-0.5 block">
              {ego ? `${ego.clearance.toFixed(2)} m` : '0.00 m'}
            </span>
          </div>

          <div className="bg-slate-950/70 p-2 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Decision State</span>
            <span className="font-mono text-[10px] font-bold text-indigo-400 mt-0.5 block truncate">
              {decisionState}
            </span>
          </div>

          <div className="bg-slate-950/70 p-2 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Active Planner</span>
            <span className="font-mono text-[10px] font-bold text-emerald-400 mt-0.5 block truncate uppercase">
              {planner}
            </span>
          </div>
        </div>
      </div>

      {/* 2. REAL-TIME SAFETY & BENCHMARK COUNTERS */}
      <div className="bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 p-4 shadow-xl">
        <h4 className="text-[11px] font-bold text-slate-300 mb-2.5 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          SAFETY ENFORCEMENT AUDIT
        </h4>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 flex justify-between items-center">
            <span className="text-slate-400 text-[10px]">Collisions:</span>
            <span className="font-bold text-emerald-400">{metrics?.collision_count ?? 0}</span>
          </div>
          <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 flex justify-between items-center">
            <span className="text-slate-400 text-[10px]">Near Misses:</span>
            <span className="font-bold text-amber-400">{metrics?.near_collision_count ?? 0}</span>
          </div>
          <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 flex justify-between items-center">
            <span className="text-slate-400 text-[10px]">Replanning:</span>
            <span className="font-bold text-cyan-400">{metrics?.replan_count ?? 0}</span>
          </div>
          <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 flex justify-between items-center">
            <span className="text-slate-400 text-[10px]">Loop Latency:</span>
            <span className="font-bold text-slate-200">{metrics?.loop_latency_ms?.toFixed(1) ?? '12.4'} ms</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
