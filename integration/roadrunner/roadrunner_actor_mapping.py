"""
IRIS RoadRunner Asset Mapping & OpenSCENARIO Converter (Combined Phase 16).
Maps RoadRunner actor catalogs, vehicles, pedestrians, animals, and surface hazards to IRIS objects.
"""

from typing import Dict, Any, Optional
from simulation.entities import ActorType, HazardType


class RoadRunnerActorMapper:
    """
    Bi-directional asset catalog mapper between MathWorks RoadRunner and IRIS simulation objects.
    """

    ROADRUNNER_TO_IRIS = {
        "Vehicle.Car.Hatchback": ActorType.CAR,
        "Vehicle.Car.Sedan": ActorType.CAR,
        "Vehicle.Motorcycle.Standard": ActorType.MOTORCYCLE,
        "Vehicle.Rickshaw.Auto": ActorType.AUTO_RICKSHAW,
        "Vehicle.Truck.Heavy": ActorType.BUS_TRUCK,
        "Vehicle.Bus.City": ActorType.BUS_TRUCK,
        "Vehicle.Bicycle.Standard": ActorType.BICYCLE,
        "Vehicle.Pushcart.Manual": ActorType.PUSHCART,
        "Pedestrian.Adult": ActorType.PEDESTRIAN,
        "Pedestrian.Child": ActorType.PEDESTRIAN,
        "Animal.Cattle.Cow": ActorType.CATTLE,
        "Animal.Cattle.Bull": ActorType.CATTLE,
    }

    SURFACE_HAZARD_MAP = {
        "Hazard.Surface.Pothole": HazardType.POTHOLE,
        "Hazard.Surface.Waterlogging": HazardType.WATERLOGGED,
        "Hazard.Surface.DeepWater": HazardType.WATERLOGGED,
        "Hazard.Surface.UnevenTerrain": HazardType.ROAD_DEPRESSION,
        "Hazard.Surface.SpeedBreaker": HazardType.SPEED_BREAKER,
        "Hazard.Surface.Debris": HazardType.DEBRIS,
        "Hazard.Surface.Construction": HazardType.DEBRIS,
    }

    @classmethod
    def map_roadrunner_asset(cls, rr_asset_id: str) -> ActorType:
        """Map RoadRunner asset string to IRIS ActorType."""
        for key, val in cls.ROADRUNNER_TO_IRIS.items():
            if key.lower() in rr_asset_id.lower():
                return val
        return ActorType.CAR

    @classmethod
    def map_roadrunner_hazard(cls, rr_hazard_id: str) -> HazardType:
        """Map RoadRunner hazard string to IRIS HazardType."""
        for key, val in cls.SURFACE_HAZARD_MAP.items():
            if key.lower() in rr_hazard_id.lower():
                return val
        return HazardType.POTHOLE

    @classmethod
    def export_mapping_schema(cls) -> Dict[str, Any]:
        """Export mapping schema for RoadRunner OpenSCENARIO exporter."""
        return {
            "actor_catalog_mappings": {k: v.name for k, v in cls.ROADRUNNER_TO_IRIS.items()},
            "surface_hazard_mappings": {k: v.name for k, v in cls.SURFACE_HAZARD_MAP.items()}
        }
