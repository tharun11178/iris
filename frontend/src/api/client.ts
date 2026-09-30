import { FullSimulationState, ScenarioItem, ExperimentRecord, BenchmarkSummaryItem, ArchitectureNode } from '../types';

const API_BASE = '/api';

export const apiClient = {
  async getStatus() {
    const res = await fetch(`${API_BASE}/system/status`);
    return res.json();
  },

  async start() {
    const res = await fetch(`${API_BASE}/system/start`, { method: 'POST' });
    return res.json();
  },

  async pause() {
    const res = await fetch(`${API_BASE}/system/pause`, { method: 'POST' });
    return res.json();
  },

  async reset() {
    const res = await fetch(`${API_BASE}/system/reset`, { method: 'POST' });
    return res.json();
  },

  async step() {
    const res = await fetch(`${API_BASE}/system/step`, { method: 'POST' });
    return res.json();
  },

  async setSpeed(multiplier: number) {
    const res = await fetch(`${API_BASE}/system/speed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ multiplier }),
    });
    return res.json();
  },

  async getState(): Promise<FullSimulationState> {
    const res = await fetch(`${API_BASE}/simulation/state`);
    return res.json();
  },

  async getScenarios(): Promise<ScenarioItem[]> {
    const res = await fetch(`${API_BASE}/scenarios`);
    return res.json();
  },

  async startScenario(scenarioId: string) {
    const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/start`, { method: 'POST' });
    return res.json();
  },

  async setPlanner(plannerMode: string) {
    const res = await fetch(`${API_BASE}/planner/${plannerMode}/set`, { method: 'POST' });
    return res.json();
  },

  async startDemo() {
    const res = await fetch(`${API_BASE}/demo/start`, { method: 'POST' });
    return res.json();
  },

  async getExperiments(): Promise<{ experiments: ExperimentRecord[]; benchmarks: BenchmarkSummaryItem[] }> {
    const res = await fetch(`${API_BASE}/experiments`);
    return res.json();
  },

  async runExperiment(scenario_id: string, planner_mode: string, seed: number = 42, duration: number = 6.0) {
    const res = await fetch(`${API_BASE}/experiments/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id, planner_mode, seed, duration }),
    });
    return res.json();
  },

  async getArchitecture(): Promise<ArchitectureNode[]> {
    const res = await fetch(`${API_BASE}/system/architecture`);
    return res.json();
  },
};
