import React, { useState, useEffect } from 'react';
import { FullSimulationState } from './types';
import { apiClient } from './api/client';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { SimulationPage } from './pages/SimulationPage';
import { ScenariosPage } from './pages/ScenariosPage';
import { RiskFieldPage } from './pages/RiskFieldPage';
import { SafeSpacePage } from './pages/SafeSpacePage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { ArchitecturePage } from './pages/ArchitecturePage';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [simState, setSimState] = useState<FullSimulationState | null>(null);

  // Poll state continuously (fallback + WebSocket)
  useEffect(() => {
    let isMounted = true;

    // WebSocket attempt
    let ws: WebSocket | null = null;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/simulation`;

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          if (data && data.status === 'running') {
            setSimState(data);
          }
        } catch (e) {}
      };
    } catch (e) {}

    // Polling fallback
    const poll = async () => {
      if (!isMounted) return;
      try {
        const state = await apiClient.getState();
        if (state && state.status === 'running') {
          setSimState(state);
        }
      } catch (err) {}
      setTimeout(poll, 60);
    };

    poll();

    return () => {
      isMounted = false;
      if (ws) ws.close();
    };
  }, []);

  const handleTogglePause = async () => {
    await apiClient.pause();
  };

  const handleReset = async () => {
    await apiClient.reset();
  };

  const handleStep = async () => {
    await apiClient.step();
  };

  const handleSelectScenario = async (sc: string) => {
    await apiClient.startScenario(sc);
  };

  const handleSelectPlanner = async (pl: string) => {
    await apiClient.setPlanner(pl);
  };

  const handleStartDemo = async () => {
    await apiClient.startDemo();
    setActiveTab('dashboard');
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* TOP NAVBAR */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        simState={simState}
        onTogglePause={handleTogglePause}
        onReset={handleReset}
        onStep={handleStep}
        onSelectScenario={handleSelectScenario}
        onSelectPlanner={handleSelectPlanner}
        onStartDemo={handleStartDemo}
      />

      {/* MAIN VIEWPORT */}
      <main className="flex-1 overflow-hidden relative">
        {activeTab === 'dashboard' && <DashboardPage simState={simState} />}
        {activeTab === 'simulation' && (
          <SimulationPage
            simState={simState}
            onTogglePause={handleTogglePause}
            onReset={handleReset}
            onStep={handleStep}
          />
        )}
        {activeTab === 'scenarios' && (
          <ScenariosPage
            onSelectScenario={handleSelectScenario}
            activeScenarioId={simState?.scenario_id ?? 'SUDDEN_CATTLE_CROSSING'}
          />
        )}
        {activeTab === 'risk_field' && <RiskFieldPage simState={simState} />}
        {activeTab === 'safe_space' && <SafeSpacePage simState={simState} />}
        {activeTab === 'analytics' && <AnalyticsPage simState={simState} />}
        {activeTab === 'experiments' && <ExperimentsPage />}
        {activeTab === 'architecture' && <ArchitecturePage />}
      </main>

      {/* BOTTOM SAFETY DISCLAIMER BAR */}
      <footer className="h-6 bg-slate-900/90 border-t border-slate-800/80 px-4 flex items-center justify-between text-[10px] text-slate-500 select-none">
        <span>IRIS: Indian Road Intelligence & Safe-Space Planner • Team KNIGHTS • SIH26037</span>
        <span className="text-amber-500/80 font-medium">IRIS is a research simulation prototype and not a certified autonomous-driving system.</span>
      </footer>
    </div>
  );
}

export default App;
