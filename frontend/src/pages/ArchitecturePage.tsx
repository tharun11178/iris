import React, { useState, useEffect } from 'react';
import { ArchitectureNode } from '../types';
import { apiClient } from '../api/client';
import { GitMerge, ArrowDown, CheckCircle2, Layers, Cpu, Shield, Zap } from 'lucide-react';

export const ArchitecturePage: React.FC = () => {
  const [nodes, setNodes] = useState<ArchitectureNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<ArchitectureNode | null>(null);

  useEffect(() => {
    apiClient.getArchitecture().then((data) => {
      setNodes(data);
      if (data.length > 0) setSelectedNode(data[0]);
    }).catch(() => {});
  }, []);

  return (
    <div className="flex-1 p-6 flex flex-col gap-6 h-[calc(100vh-64px)] overflow-y-auto">
      <div>
        <h2 className="font-heading font-extrabold text-2xl text-white">System Architecture & Pipeline Connectivity</h2>
        <p className="text-xs text-slate-400 mt-1">Interactive 16-Phase End-to-End Closed-Loop Autonomous Driving Pipeline</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-6">
        {/* LEFT: 16-PHASE CLICKABLE PIPELINE FLOW */}
        <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl flex flex-col gap-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-heading font-bold text-sm text-slate-200">Continuous Closed-Loop Pipeline</h3>
            <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              16 PHASES SYNCHRONIZED
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {nodes.map((node, i) => {
              const isSelected = selectedNode?.id === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className={`p-3.5 rounded-xl border text-left transition-all duration-200 flex items-center justify-between cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-500/15 border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
                      : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center font-mono font-bold text-[10px] text-cyan-400">
                      {i + 1}
                    </div>
                    <div>
                      <span className="font-heading font-bold text-xs text-white block">{node.name}</span>
                      <span className="text-[10px] text-slate-400 block truncate max-w-[220px]">{node.algorithm}</span>
                    </div>
                  </div>
                  <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                    ACTIVE
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* RIGHT: SELECTED NODE SPECIFICATION CARD */}
        {selectedNode && (
          <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
                  Subsystem Specification
                </span>
                <span className="text-[10px] font-mono font-bold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> {selectedNode.status}
                </span>
              </div>

              <h3 className="font-heading font-extrabold text-xl text-white mb-3">{selectedNode.name}</h3>

              <div className="flex flex-col gap-4 text-xs">
                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Core Purpose</span>
                  <p className="text-slate-200 leading-relaxed">{selectedNode.purpose}</p>
                </div>

                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Algorithm & Method</span>
                  <p className="text-cyan-300 font-mono text-[11px] leading-relaxed">{selectedNode.algorithm}</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Inputs</span>
                    <p className="text-slate-300 text-[11px]">{selectedNode.inputs}</p>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Outputs</span>
                    <p className="text-slate-300 text-[11px]">{selectedNode.outputs}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span>IRIS Team KNIGHTS</span>
              <span>Closed-Loop Rate: 20 Hz</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
