import React from 'react';
import { FullSimulationState } from '../types';
import { CanvasVisualizer } from '../components/CanvasVisualizer';
import { Play, Pause, RotateCcw, StepForward, FastForward, Activity, RefreshCw } from 'lucide-react';
import { apiClient } from '../api/client';

interface SimulationPageProps {
  simState: FullSimulationState | null;
  onTogglePause: () => void;
  onReset: () => void;
  onStep: () => void;
}

export const SimulationPage: React.FC<SimulationPageProps> = ({
  simState,
  onTogglePause,
  onReset,
  onStep,
}) => {
  const isPaused = simState?.is_paused ?? false;

  const handleSpeed = async (multiplier: number) => {
    await apiClient.setSpeed(multiplier);
  };

  return (
    <div className="flex-1 p-4 flex flex-col gap-4 h-[calc(100vh-64px)] overflow-hidden">
      {/* TOP CONTROL BAR */}
      <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-3 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-3">
          <button
            onClick={onTogglePause}
            className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-indigo-600 text-slate-950 font-bold px-4 py-2 rounded-xl text-xs shadow-lg shadow-cyan-500/20 hover:scale-105 transition-all"
          >
            {isPaused ? <Play className="w-4 h-4 fill-current" /> : <Pause className="w-4 h-4 fill-current" />}
            <span>{isPaused ? 'Resume Simulation' : 'Pause Simulation'}</span>
          </button>

          <button
            onClick={onStep}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs font-semibold border border-slate-700 transition-all"
          >
            <StepForward className="w-4 h-4" />
            <span>Single Step</span>
          </button>

          <button
            onClick={onReset}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs font-semibold border border-slate-700 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset</span>
          </button>
        </div>

        {/* SPEED MULTIPLIERS */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400">Simulation Speed:</span>
          <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
            {[0.5, 1.0, 2.0, 4.0].map((spd) => (
              <button
                key={spd}
                onClick={() => handleSpeed(spd)}
                className="px-2.5 py-1 rounded-lg text-xs font-bold text-slate-300 hover:text-white hover:bg-slate-800 transition-all"
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* EXPANDED 2D SIMULATION CANVAS */}
      <div className="flex-1 min-h-[460px] relative">
        <CanvasVisualizer simState={simState} heightClass="h-full" />
      </div>
    </div>
  );
};
