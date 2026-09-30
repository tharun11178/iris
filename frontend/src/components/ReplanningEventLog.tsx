import React from 'react';
import { ReplanEvent } from '../types';
import { AlertTriangle, Clock, RefreshCw } from 'lucide-react';

interface ReplanningEventLogProps {
  events: ReplanEvent[];
}

export const ReplanningEventLog: React.FC<ReplanningEventLogProps> = ({ events }) => {
  return (
    <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800/90 p-4 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-cyan-400" />
          <h3 className="font-heading font-bold text-xs tracking-wider text-slate-300">REPLANNING EVENT STREAM</h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">Proactive Risk Triggers</span>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-2 max-h-56 pr-1">
        {events && events.length > 0 ? (
          events
            .slice()
            .reverse()
            .map((ev, idx) => {
              const isHighRisk = ev.risk_before > 0.55;
              return (
                <div
                  key={idx}
                  className={`p-2 rounded-xl border text-xs flex items-center justify-between ${
                    isHighRisk
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-3.5 h-3.5 ${isHighRisk ? 'text-rose-400' : 'text-cyan-400'}`} />
                    <span className="font-bold truncate max-w-[140px]">{ev.reason}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                    <span>{ev.latency_ms.toFixed(1)}ms</span>
                    <span>•</span>
                    <span className="text-slate-300">t = {ev.timestamp.toFixed(2)}s</span>
                  </div>
                </div>
              );
            })
        ) : (
          <div className="flex flex-col items-center justify-center h-28 text-slate-500 text-xs italic">
            <span>No replanning triggers active.</span>
            <span className="text-[10px] text-slate-600 mt-1">Vehicle cruising on optimal path</span>
          </div>
        )}
      </div>
    </div>
  );
};
