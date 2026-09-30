"""
IRIS Multi-Sensor Pipeline Interface Abstraction (Combined Phase 16).
Provides camera, LiDAR, and Radar sensor data stream wrappers maintaining
Sensor ➔ Perception ➔ WorldModel control flow architecture.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import math


@dataclass
class CameraFrame:
    """Camera image stream container."""
    timestamp: float
    width: int = 1920
    height: int = 1080
    channels: int = 3
    detected_bounding_boxes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LiDARPointCloud:
    """LiDAR 3D point cloud point set."""
    timestamp: float
    num_points: int = 0
    points_xyz: List[Tuple[float, float, float]] = field(default_factory=list)
    intensity: List[float] = field(default_factory=list)


@dataclass
class RadarTarget:
    """Radar target track point."""
    target_id: int
    range_m: float
    azimuth_rad: float
    doppler_speed_ms: float
    snr_db: float


@dataclass
class RadarScan:
    """Radar scan target array."""
    timestamp: float
    targets: List[RadarTarget] = field(default_factory=list)


class SensorPipeline:
    """
    Multi-sensor interface wrapper providing sensor fusion inputs (Camera, LiDAR, Radar)
    to PerceptionManager without overriding standard simulation ground truth detector.
    """

    def __init__(self, camera_enabled: bool = True, lidar_enabled: bool = True, radar_enabled: bool = True):
        self.camera_enabled = camera_enabled
        self.lidar_enabled = lidar_enabled
        self.radar_enabled = radar_enabled

    def process_sensor_streams(self, env: Any) -> Dict[str, Any]:
        """
        Synthesize multi-sensor telemetry frames from environment ground truth.
        """
        sim_t = float(env.sim_time)
        ego = env.ego_vehicle

        # 1. Camera Frame Synthesis
        cam_boxes = []
        for actor in env.traffic_actors:
            dx = actor.x - ego.x
            dy = actor.y - ego.y
            if 0.0 < dx < 60.0 and abs(dy) < 15.0:  # FOV check
                cam_boxes.append({
                    "actor_id": actor.actor_id,
                    "type": str(actor.actor_type.name if hasattr(actor.actor_type, 'name') else actor.actor_type),
                    "bbox_2d": [int(100 + dx * 10), int(200 + dy * 10), 50, 40]
                })
        cam_frame = CameraFrame(timestamp=sim_t, detected_bounding_boxes=cam_boxes)

        # 2. LiDAR Point Cloud Synthesis
        pts = []
        for actor in env.traffic_actors:
            dx = actor.x - ego.x
            dy = actor.y - ego.y
            dist = math.hypot(dx, dy)
            if dist < 80.0:
                for angle in [-0.2, 0.0, 0.2]:
                    pts.append((float(actor.x + math.cos(angle)), float(actor.y + math.sin(angle)), 0.5))
        lidar_cloud = LiDARPointCloud(timestamp=sim_t, num_points=len(pts), points_xyz=pts)

        # 3. Radar Scan Synthesis
        radar_targets = []
        for actor in env.traffic_actors:
            dx = actor.x - ego.x
            dy = actor.y - ego.y
            r = math.hypot(dx, dy)
            if r < 100.0:
                az = math.arctan2(dy, dx) if hasattr(math, "arctan2") else math.atan2(dy, dx)
                dop = float(actor.velocity * math.cos(actor.heading) - ego.velocity * math.cos(ego.heading))
                radar_targets.append(RadarTarget(
                    target_id=actor.actor_id,
                    range_m=float(r),
                    azimuth_rad=float(az),
                    doppler_speed_ms=float(dop),
                    snr_db=25.0
                ))
        radar_scan = RadarScan(timestamp=sim_t, targets=radar_targets)

        return {
            "camera": cam_frame,
            "lidar": lidar_cloud,
            "radar": radar_scan,
            "active_sensors": {
                "camera": self.camera_enabled,
                "lidar": self.lidar_enabled,
                "radar": self.radar_enabled
            }
        }
