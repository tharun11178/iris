"""
IRIS RoadRunner Detailed Scene Specification Generator (Combined Phase 16).
Generates OpenDRIVE / OpenSCENARIO scene specifications for Indian Urban Intersection and Village/Highway Transition.
"""

import json
from typing import Dict, Any


class RoadRunnerSceneSpecGenerator:
    """
    Generates detailed scene specifications for RoadRunner Scene Builder co-simulation.
    """

    @staticmethod
    def generate_scene_1_urban_intersection() -> Dict[str, Any]:
        """
        SCENE 1: Unsignalized Indian Urban Intersection
        Features: 4-way crossing, auto-rickshaws, pedestrians, swerving motorcycles, no traffic light.
        """
        return {
            "scene_id": "ROADRUNNER_SCENE_1_URBAN_INTERSECTION",
            "name": "Indian Unsignalized Urban Intersection",
            "description": "Multi-directional chaotic 4-way intersection without traffic signal. Irregular crossing movement of auto-rickshaws, pedestrians, and motorcycles.",
            "road_type": "URBAN_INTERSECTION",
            "road_dimensions": {
                "width_m": 12.0,
                "length_m": 150.0,
                "num_lanes": 0,  # lane-free
                "lane_markings": False
            },
            "initial_ego_pose": {
                "x": 10.0,
                "y": 0.0,
                "heading_deg": 0.0,
                "speed_kmh": 25.0
            },
            "goal_position": [140.0, 0.0],
            "scenario_duration_s": 30.0,
            "traffic_actors": [
                {
                    "id": 1,
                    "rr_asset": "Vehicle.Rickshaw.Auto",
                    "iris_type": "AUTO_RICKSHAW",
                    "initial_pose": [40.0, 2.5, 0.0],
                    "target_speed_kmh": 18.0,
                    "behavior": "SWERVING"
                },
                {
                    "id": 2,
                    "rr_asset": "Pedestrian.Adult",
                    "iris_type": "PEDESTRIAN",
                    "initial_pose": [50.0, -5.5, 90.0],
                    "target_speed_kmh": 4.5,
                    "behavior": "CROSSING"
                },
                {
                    "id": 3,
                    "rr_asset": "Vehicle.Motorcycle.Standard",
                    "iris_type": "MOTORCYCLE",
                    "initial_pose": [30.0, -1.8, 0.0],
                    "target_speed_kmh": 32.0,
                    "behavior": "SWERVING"
                },
                {
                    "id": 4,
                    "rr_asset": "Vehicle.Car.Hatchback",
                    "iris_type": "CAR",
                    "initial_pose": [70.0, -3.0, 180.0],
                    "target_speed_kmh": 22.0,
                    "behavior": "CRUISE"
                }
            ],
            "surface_hazards": [
                {
                    "id": 1,
                    "rr_asset": "Hazard.Surface.Pothole",
                    "iris_type": "POTHOLE",
                    "position": [45.0, 0.5],
                    "radius_m": 1.2,
                    "severity": 0.6
                }
            ]
        }

    @staticmethod
    def generate_scene_2_village_highway_transition() -> Dict[str, Any]:
        """
        SCENE 2: Indian Village / Highway Transition
        Features: narrow unmarked road, sudden cattle crossing, slow trucks, potholes, waterlogging.
        """
        return {
            "scene_id": "ROADRUNNER_SCENE_2_VILLAGE_HIGHWAY_TRANSITION",
            "name": "Indian Village to Highway Transition",
            "description": "Narrow lane-free village path transitioning into fast highway. Features sudden cattle crossing, potholes, waterlogging, and slow heavy vehicles.",
            "road_type": "UNMARKED_VILLAGE_ROAD",
            "road_dimensions": {
                "width_m": 8.0,
                "length_m": 200.0,
                "num_lanes": 0,
                "lane_markings": False
            },
            "initial_ego_pose": {
                "x": 10.0,
                "y": 0.0,
                "heading_deg": 0.0,
                "speed_kmh": 20.0
            },
            "goal_position": [190.0, 0.0],
            "scenario_duration_s": 35.0,
            "traffic_actors": [
                {
                    "id": 101,
                    "rr_asset": "Animal.Cattle.Cow",
                    "iris_type": "CATTLE",
                    "initial_pose": [65.0, -3.5, 80.0],
                    "target_speed_kmh": 2.0,
                    "behavior": "SUDDEN_CROSSING"
                },
                {
                    "id": 102,
                    "rr_asset": "Vehicle.Truck.Heavy",
                    "iris_type": "BUS_TRUCK",
                    "initial_pose": [110.0, -1.5, 0.0],
                    "target_speed_kmh": 30.0,
                    "behavior": "CRUISE"
                },
                {
                    "id": 103,
                    "rr_asset": "Vehicle.Motorcycle.Standard",
                    "iris_type": "MOTORCYCLE",
                    "initial_pose": [130.0, 2.5, 180.0],
                    "target_speed_kmh": 40.0,
                    "behavior": "WRONG_SIDE"
                }
            ],
            "surface_hazards": [
                {
                    "id": 201,
                    "rr_asset": "Hazard.Surface.Pothole",
                    "iris_type": "POTHOLE",
                    "position": [40.0, 0.2],
                    "radius_m": 1.5,
                    "severity": 0.85
                },
                {
                    "id": 202,
                    "rr_asset": "Hazard.Surface.Waterlogging",
                    "iris_type": "WATERLOGGING",
                    "position": [95.0, -1.0],
                    "radius_m": 2.5,
                    "severity": 0.70
                }
            ]
        }

    @classmethod
    def export_all_scenes(cls, output_dir: str = "integration/roadrunner/scenes") -> Dict[str, str]:
        """Export scene specs to JSON files."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        s1 = cls.generate_scene_1_urban_intersection()
        s2 = cls.generate_scene_2_village_highway_transition()

        p1 = os.path.join(output_dir, "scene_1_urban_intersection.json")
        p2 = os.path.join(output_dir, "scene_2_village_highway_transition.json")

        with open(p1, "w", encoding="utf-8") as f:
            json.dump(s1, f, indent=2)

        with open(p2, "w", encoding="utf-8") as f:
            json.dump(s2, f, indent=2)

        return {"scene_1": p1, "scene_2": p2}
