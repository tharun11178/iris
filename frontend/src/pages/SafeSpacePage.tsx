import React from 'react';
import { FullSimulationState } from '../types';
import { CanvasVisualizer } from '../components/CanvasVisualizer';
import { Zap, CheckCircle, XCircle, Sliders } from 'lucide-react';

interface SafeSpacePageProps {
  simState: FullSimulationState | null;
}

export const SafeSpacePage: React.FC<SafeSpacePageProps> = ({ simState }) => {
  const corridors = simState?.corridors || [];

  return (
    <div className="flex-1 p-6 flex flex-col gap-6 h-[calc(100vh-64px)] overflow-y-auto">
      <div>
        <h2 className="font-heading font-extrabold text-2xl text-white">Safe-Space / Negative-Space Planner</h2>
        <p className="text-xs text-slate-400 mt-1">Extracts Open Drivable Negative Space and Optimizes Proactive Trajectories (Phases 11 & 12)</p>
      </div>

      <div className="grid grid-cols-[1fr_400px] gap-6">
        {/* CENTER VISUALIZER */}
        <div className="flex flex-col gap-4">
          <CanvasVisualizer simState={simState} heightClass="h-[520px]" />
        </div>

        {/* RIGHT CANDIDATE CORRIDOR TABLE & FORMULA */}
        <div className="flex flex-col gap-4">
          <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl">
            <h3 className="font-heading font-bold text-sm text-slate-200 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-emerald-400" />
              Multi-Objective Cost Formulation
            </h3>

            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[11px] text-emerald-300 mb-4 leading-relaxed">
              Cost = w_Risk·FutureRisk + w_Clr·Clearance + w_Unc·Uncertainty + w_Surf·Surface + w_Sm·Smoothness
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Rather than merely detecting obstacle boundaries, IRIS continuously evaluates the topological negative space around moving cattle, rickshaws, and potholes to guarantee lateral safe margins.
            </p>
          </div>

          {/* CANDIDATE CORRIDORS TABLE */}
          <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl flex flex-col flex-1">
            <h3 className="font-heading font-bold text-sm text-slate-200 mb-3">
              Candidate Safe Corridors ({corridors.length})
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                    <th className="pb-2">Corridor</th>
                    <th className="pb-2">Score</th>
                    <th className="pb-2">Min Clr</th>
                    <th className="pb-2 text-right">Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-300">
                  {corridors.map((c, i) => (
                    <tr key={i} className={c.is_selected ? 'bg-emerald-500/10' : ''}>
                      <td className="py-2.5 font-mono">Corridor #{i + 1}</td>
                      <td className="py-2.5 font-mono">{c.score.toFixed(3)}</td>
                      <td className="py-2.5 font-mono">{c.clearance?.toFixed(2) ?? '2.00'}m</td>
                      <td className="py-2.5 text-right">
                        {c.is_selected ? (
                          <span className="inline-flex items-center gap-1 font-bold text-[10px] text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full border border-emerald-500/30">
                            <CheckCircle className="w-3 h-3" /> SELECTED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-semibold text-[10px] text-slate-500">
                            <XCircle className="w-3 h-3" /> REJECTED
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {corridors.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-slate-500 italic text-xs">
                        No candidate corridors generated.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
