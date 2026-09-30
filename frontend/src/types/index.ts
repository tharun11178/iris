export interface EgoVehicleState {
  x: number;
  y: number;
  heading: number;
  heading_deg?: number;
  velocity: number;
  speed_kmh: number;
  target_speed: number;
  target_speed_kmh?: number;
  steering_angle: number;
  steering_angle_deg?: number;
  steering_command?: number;
  acceleration: number;
  brake?: number;
  length: number;
  width: number;
  clearance: number;
  left_clearance?: number;
  right_clearance?: number;
  min_road_clearance?: number;
  min_obstacle_clearance?: number;
  ttc?: number;
  condition?: string;
  is_safe?: boolean;
  decision_state: string;
  lookahead_point?: [number, number];
  current_waypoint?: [number, number];
  footprint?: [number, number][];
  safety_hold?: boolean;
  path: [number, number][];
}

export interface PredictionHypothesis {
  type: string;
  probability: number;
  points: [number, number][];
}

export interface UncertaintyEllipse {
  semi_major: number;
  semi_minor: number;
  angle: number;
  total_uncertainty: number;
}

export interface TrafficActorState {
  id: string | number;
  type: string;
  x: number;
  y: number;
  heading: number;
  speed: number;
  length: number;
  width: number;
  corners?: [number, number][];
  hypotheses?: PredictionHypothesis[];
  uncertainty?: UncertaintyEllipse | null;
}

export interface SurfaceHazardState {
  id: number | string;
  type: string;
  x: number;
  y: number;
  length: number;
  width: number;
  severity: number;
  is_traversable: boolean;
}

export interface SafeCorridor {
  points: [number, number][];
  score: number;
  is_selected: boolean;
  clearance?: number;
}

export interface ReplanEvent {
  timestamp: number;
  reason: string;
  latency_ms: number;
  risk_before: number;
  risk_after: number;
}

export interface SystemMetrics {
  completion_rate: number;
  scenario_completed: boolean;
  collision_count: number;
  near_collision_count: number;
  min_clearance: number;
  smoothness_score: number;
  replan_count: number;
  avg_replan_latency_ms: number;
  loop_latency_ms: number;
}

export interface RoadGeometry {
  length: number;
  width: number;
  safe_margin?: number;
  safe_width?: number;
  lanes: number;
}

export interface FullSimulationState {
  status: string;
  sim_time: number;
  step_count: number;
  is_paused: boolean;
  is_demo_mode: boolean;
  scenario_id: string;
  planner_mode: string;
  road: RoadGeometry;
  ego: EgoVehicleState;
  actors: TrafficActorState[];
  hazards: SurfaceHazardState[];
  corridors: SafeCorridor[];
  events: ReplanEvent[];
  risk: {
    peak_future_risk: number;
    current_risk: number;
  };
  risk_matrix: number[][];
  metrics: SystemMetrics;
  latencies: Record<string, number>;
}

export interface ScenarioItem {
  id: string;
  name: string;
  category: string;
  description: string;
  difficulty: string;
  traffic_density: string;
  active_hazards: string[];
}

export interface ExperimentRecord {
  id: number;
  experiment_name: string;
  scenario_id: string;
  planner_mode: string;
  seed: number;
  duration: number;
  config: Record<string, any>;
  metrics: Record<string, any>;
  timestamp: string;
}

export interface BenchmarkSummaryItem {
  scenario_id: string;
  planner_mode: string;
  avg_collisions: number;
  avg_near_collisions: number;
  avg_clearance: number;
  avg_peak_risk: number;
  avg_smoothness: number;
  avg_replans: number;
  avg_replan_latency: number;
  avg_completion: number;
  total_runs: number;
}

export interface ArchitectureNode {
  id: string;
  name: string;
  purpose: string;
  inputs: string;
  outputs: string;
  algorithm: string;
  status: string;
}
