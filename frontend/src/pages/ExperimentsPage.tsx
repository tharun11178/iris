import React, { useState, useEffect } from 'react';
import { ExperimentRecord, BenchmarkSummaryItem } from '../types';
import { apiClient } from '../api/client';
import { Database, Play, Download, RefreshCw, CheckCircle2 } from 'lucide-react';

export const ExperimentsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummaryItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  // Form State
  const [scenario, setScenario] = useState('SUDDEN_CATTLE_CROSSING');
  const [planner, setPlanner] = useState('iris');
  const [seed, setSeed] = useState(42);
  const [duration, setDuration] = useState(6.0);

  const loadData = async () => {
    try {
      const res = await apiClient.getExperiments();
      setExperiments(res.experiments);
      setBenchmarks(res.benchmarks);
    } catch (err) {}
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunExperiment = async () => {
    setIsRunning(true);
    try {
      await apiClient.runExperiment(scenario, planner, seed, duration);
      await loadData();
    } catch (err) {
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex-1 p-6 flex flex-col gap-6 h-[calc(100vh-64px)] overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading font-extrabold text-2xl text-white">Reproducible Experiment Management</h2>
          <p className="text-xs text-slate-400 mt-1">SQLite Persistent Benchmark Matrix Runs, Seed Control & Dataset Export</p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/api/experiments/export/csv"
            download="iris_experiments.csv"
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs font-bold border border-slate-700 transition-all"
          >
            <Download className="w-4 h-4 text-cyan-400" />
            <span>Export CSV</span>
          </a>

          <a
            href="/api/experiments/export/json"
            download="iris_experiments.json"
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs font-bold border border-slate-700 transition-all"
          >
            <Download className="w-4 h-4 text-indigo-400" />
            <span>Export JSON</span>
          </a>
        </div>
      </div>

      {/* EXPERIMENT LAUNCH FORM */}
      <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl">
        <h3 className="font-heading font-bold text-sm text-slate-200 mb-4 flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          Trigger Automated Benchmark Run
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">Scenario</label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="w-full bg-slate-950 text-slate-200 text-xs font-semibold p-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500"
            >
              <option value="SUDDEN_CATTLE_CROSSING">Sudden Cattle Crossing</option>
              <option value="UNMARKED_VILLAGE_ROAD">Unmarked Village Road</option>
              <option value="DENSE_MARKET">Dense Indian Market</option>
              <option value="COMBINED_SURFACE_HAZARDS">Potholes & Waterlogging</option>
              <option value="UNSIGNALIZED_URBAN_INTERSECTION">Urban Intersection</option>
              <option value="HIGHWAY_MERGE">Highway Merge</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">Planner Mode</label>
            <select
              value={planner}
              onChange={(e) => setPlanner(e.target.value)}
              className="w-full bg-slate-950 text-slate-200 text-xs font-semibold p-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500"
            >
              <option value="iris">IRIS Safe-Space Planner (Full 16-Phase)</option>
              <option value="astar">Baseline A* Grid Search</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">Random Seed</label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
              className="w-full bg-slate-950 text-slate-200 text-xs font-semibold p-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">Duration (Seconds)</label>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(parseFloat(e.target.value) || 6.0)}
              className="w-full bg-slate-950 text-slate-200 text-xs font-semibold p-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <button
          onClick={handleRunExperiment}
          disabled={isRunning}
          className="w-full py-3 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-extrabold text-xs rounded-xl shadow-lg shadow-cyan-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
        >
          {isRunning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
          <span>{isRunning ? 'RUNNING EXPERIMENT SIMULATION...' : 'EXECUTE BENCHMARK EXPERIMENT'}</span>
        </button>
      </div>

      {/* BENCHMARKS SUMMARY TABLE */}
      <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl">
        <h3 className="font-heading font-bold text-sm text-slate-200 mb-3">
          Aggregated Scenario Benchmark Summary
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-2">Scenario</th>
                <th className="pb-2">Planner</th>
                <th className="pb-2">Avg Collisions</th>
                <th className="pb-2">Avg Near-Misses</th>
                <th className="pb-2">Min Clearance</th>
                <th className="pb-2">Peak Risk</th>
                <th className="pb-2">Smoothness</th>
                <th className="pb-2">Total Runs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-slate-300">
              {benchmarks.map((b, i) => (
                <tr key={i}>
                  <td className="py-2.5 font-bold">{b.scenario_id}</td>
                  <td className="py-2.5 font-mono">{b.planner_mode.toUpperCase()}</td>
                  <td className={`py-2.5 font-mono ${b.avg_collisions > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {b.avg_collisions}
                  </td>
                  <td className="py-2.5 font-mono">{b.avg_near_collisions}</td>
                  <td className="py-2.5 font-mono">{b.avg_clearance}m</td>
                  <td className="py-2.5 font-mono">{b.avg_peak_risk}</td>
                  <td className="py-2.5 font-mono text-cyan-400">{b.avg_smoothness}</td>
                  <td className="py-2.5 font-mono text-slate-400">{b.total_runs}</td>
                </tr>
              ))}
              {benchmarks.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-slate-500 italic">
                    No benchmark runs recorded in database yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
