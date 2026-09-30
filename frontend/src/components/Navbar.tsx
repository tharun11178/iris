import React from 'react';
import { Play, Pause, RotateCcw, StepForward, Activity, Zap, Shield, Layers, BarChart3, Database, GitMerge, Award } from 'lucide-react';
import { FullSimulationState } from '../types';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  simState: FullSimulationState | null;
  onTogglePause: () => void;
  onReset: () => void;
  onStep: () => void;
  onSelectScenario: (sc: string) => void;
  onSelectPlanner: (pl: string) => void;
  onStartDemo: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  simState,
  onTogglePause,
  onReset,
  onStep,
  onSelectScenario,
  onSelectPlanner,
  onStartDemo,
}) => {
  const isPaused = simState?.is_paused ?? false;
  const isDemo = simState?.is_demo_mode ?? false;
  const currentScenario = simState?.scenario_id ?? 'SUDDEN_CATTLE_CROSSING';
  const currentPlanner = simState?.planner_mode ?? 'iris';

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'simulation', label: 'Simulation', icon: Play },
    { id: 'scenarios', label: 'Scenarios', icon: Layers },
    { id: 'risk_field', label: 'Risk Field', icon: Shield },
    { id: 'safe_space', label: 'Safe Space', icon: Zap },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'experiments', label: 'Experiments', icon: Database },
    { id: 'architecture', label: 'Architecture', icon: GitMerge },
  ];

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur-xl border-b border-slate-800 flex items-center justify-between px-6 z-30 select-none">
      {/* BRAND & LOGO */}
      <div className="flex items-center gap-3">
        <div className="relative w-8 h-8 flex items-center justify-center">
          <div className="w-3.5 h-3.5 rounded-full bg-gradient-to-br from-cyan-400 to-indigo-500 shadow-[0_0_15px_#06b6d4]"></div>
          <div className="absolute inset-0 border-2 border-cyan-500/40 rounded-full border-t-transparent animate-spin"></div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading font-extrabold text-lg tracking-wider text-white">IRIS <span className="text-[10px] bg-gradient-to-r from-cyan-500 to-indigo-600 px-1.5 py-0.5 rounded text-white font-semibold">PRO</span></h1>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700 font-mono">KNIGHTS</span>
          </div>
          <p className="text-[10px] text-slate-400 font-medium">SIH26037 • Unstructured Indian Roads</p>
        </div>
      </div>

      {/* NAVIGATION TABS */}
      <nav className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800/80">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-lg shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* RIGHT ACTION CONTROLS */}
      <div className="flex items-center gap-3">
        {/* SCENARIO SELECTOR */}
        <select
          value={currentScenario}
          onChange={(e) => onSelectScenario(e.target.value)}
          className="bg-slate-800/90 text-xs font-semibold text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
        >
          <option value="SUDDEN_CATTLE_CROSSING">Cattle Crossing</option>
          <option value="UNMARKED_VILLAGE_ROAD">Village Road</option>
          <option value="DENSE_MARKET">Dense Market</option>
          <option value="COMBINED_SURFACE_HAZARDS">Potholes & Water</option>
          <option value="UNSIGNALIZED_URBAN_INTERSECTION">Urban Intersection</option>
          <option value="HIGHWAY_MERGE">Highway Merge</option>
          <option value="WRONG_SIDE_MOTORCYCLE">Wrong-Side Bike</option>
          <option value="TRAFFIC_CHAOS">Traffic Chaos</option>
        </select>

        {/* PLANNER TOGGLE */}
        <div className="flex bg-slate-950/80 p-0.5 rounded-lg border border-slate-800">
          <button
            onClick={() => onSelectPlanner('iris')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-all ${
              currentPlanner === 'iris'
                ? 'bg-cyan-500 text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            IRIS Safe-Space
          </button>
          <button
            onClick={() => onSelectPlanner('astar')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-all ${
              currentPlanner === 'astar'
                ? 'bg-amber-500 text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Baseline A*
          </button>
        </div>

        {/* DEMO MODE BUTTON */}
        <button
          onClick={onStartDemo}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
            isDemo
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
          }`}
          title="Run 5-Scenario Automated Demo"
        >
          <Award className="w-3.5 h-3.5" />
          <span>{isDemo ? 'Demo Running' : 'Demo Mode'}</span>
        </button>

        {/* PLAY/PAUSE */}
        <button
          onClick={onTogglePause}
          className="flex items-center gap-1.5 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-bold px-3 py-1.5 rounded-lg text-xs shadow-md shadow-cyan-500/25 transition-all"
        >
          {isPaused ? <Play className="w-3.5 h-3.5 fill-current" /> : <Pause className="w-3.5 h-3.5 fill-current" />}
          <span>{isPaused ? 'Resume' : 'Pause'}</span>
        </button>

        {/* STEP */}
        <button
          onClick={onStep}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-all"
          title="Step Single Frame"
        >
          <StepForward className="w-4 h-4" />
        </button>

        {/* RESET */}
        <button
          onClick={onReset}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-all"
          title="Reset Scenario"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
