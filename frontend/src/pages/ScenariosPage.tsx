import React, { useState, useEffect } from 'react';
import { ScenarioItem } from '../types';
import { apiClient } from '../api/client';
import { Play, AlertTriangle, Users, Compass, ShieldAlert } from 'lucide-react';

interface ScenariosPageProps {
  onSelectScenario: (sc: string) => void;
  activeScenarioId: string;
}

export const ScenariosPage: React.FC<ScenariosPageProps> = ({
  onSelectScenario,
  activeScenarioId,
}) => {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [filter, setFilter] = useState<'ALL' | 'Mandatory' | 'Stress Test'>('ALL');

  useEffect(() => {
    apiClient.getScenarios().then((data) => setScenarios(data)).catch(() => {});
  }, []);

  const filteredScenarios = scenarios.filter(
    (s) => filter === 'ALL' || s.category === filter
  );

  const getDifficultyColor = (diff: string) => {
    switch (diff.toLowerCase()) {
      case 'extreme':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
    }
  };

  return (
    <div className="flex-1 p-6 flex flex-col gap-6 h-[calc(100vh-64px)] overflow-y-auto">
      {/* HEADER & FILTER */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading font-extrabold text-2xl text-white">Indian Road Scenarios Suite</h2>
          <p className="text-xs text-slate-400 mt-1">10 Benchmark Environments Designed for Unstructured Indian Road Driving</p>
        </div>

        <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-800">
          {(['ALL', 'Mandatory', 'Stress Test'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                filter === cat
                  ? 'bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* SCENARIO CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredScenarios.map((sc) => {
          const isActive = activeScenarioId === sc.id;
          return (
            <div
              key={sc.id}
              className={`rounded-2xl border p-5 flex flex-col justify-between transition-all duration-300 ${
                isActive
                  ? 'bg-slate-900/90 border-cyan-500 shadow-[0_0_25px_rgba(6,182,212,0.2)]'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                    {sc.category}
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getDifficultyColor(sc.difficulty)}`}>
                    {sc.difficulty}
                  </span>
                </div>

                <h3 className="font-heading font-bold text-lg text-white mb-2">{sc.name}</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">{sc.description}</p>

                {/* HAZARDS & DENSITY */}
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {sc.active_hazards.map((h, i) => (
                    <span key={i} className="text-[10px] bg-slate-950 text-slate-300 px-2 py-0.5 rounded-md border border-slate-800 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      {h}
                    </span>
                  ))}
                  <span className="text-[10px] bg-slate-950 text-slate-300 px-2 py-0.5 rounded-md border border-slate-800 flex items-center gap-1">
                    <Users className="w-3 h-3 text-cyan-400" />
                    {sc.traffic_density} Traffic
                  </span>
                </div>
              </div>

              <button
                onClick={() => onSelectScenario(sc.id)}
                className={`w-full py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                  isActive
                    ? 'bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/25'
                    : 'bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700'
                }`}
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{isActive ? 'CURRENTLY ACTIVE' : 'RUN SCENARIO'}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
