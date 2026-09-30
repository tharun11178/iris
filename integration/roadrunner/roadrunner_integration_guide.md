# MathWorks RoadRunner Scene Builder Integration Guide — IRIS Phase 16

## Overview
This document describes the workflow for importing RoadRunner OpenDRIVE / OpenSCENARIO scenes and mapping asset catalogs (vehicles, rickshaws, motorcycles, cattle, pushcarts, surface hazards) into Python IRIS simulation environments.

---

## Asset Catalog Mapping Table

| RoadRunner Asset Catalog String | IRIS Object Type | Geometry Bounds | Typical Velocity |
|---|---|---|---|
| `Vehicle.Car.Hatchback` | `ActorType.CAR` | 4.2m x 1.8m | 30–60 km/h |
| `Vehicle.Motorcycle.Standard` | `ActorType.MOTORCYCLE` | 2.0m x 0.8m | 25–50 km/h |
| `Vehicle.Rickshaw.Auto` | `ActorType.AUTO_RICKSHAW` | 2.6m x 1.3m | 15–30 km/h |
| `Vehicle.Truck.Heavy` | `ActorType.BUS_TRUCK` | 8.5m x 2.5m | 20–40 km/h |
| `Pedestrian.Adult` | `ActorType.PEDESTRIAN` | 0.5m x 0.5m | 3–6 km/h |
| `Animal.Cattle.Cow` | `ActorType.CATTLE` | 2.2m x 0.9m | 1–3 km/h |
| `Hazard.Surface.Pothole` | `SurfaceHazardType.POTHOLE` | Radius 0.5–2.0m | Static |
| `Hazard.Surface.Waterlogging` | `SurfaceHazardType.WATERLOGGING` | Radius 1.5–4.0m | Static |

---

## RoadRunner Scenario Specifications

### Scene 1: Indian Unsignalized Urban Intersection
- **OpenDRIVE Export**: `scene_1_urban_intersection.xodr`
- **OpenSCENARIO Export**: `scene_1_urban_intersection.xosc`
- **Features**: 12m wide 4-way intersection without traffic signal, crossing Rickshaw swarms, swerving motorcycles, pedestrian foot traffic.

### Scene 2: Indian Village to Highway Transition
- **OpenDRIVE Export**: `scene_2_village_highway_transition.xodr`
- **OpenSCENARIO Export**: `scene_2_village_highway_transition.xosc`
- **Features**: 8m narrow lane-free village path with sudden cattle crossing, potholes, waterlogged sections, transitioning into open highway.

---

## Python Exporter Usage

```python
from integration.roadrunner.roadrunner_scene_spec import RoadRunnerSceneSpecGenerator
from integration.roadrunner.roadrunner_actor_mapping import RoadRunnerActorMapper

# Export scene specifications
exported_paths = RoadRunnerSceneSpecGenerator.export_all_scenes("integration/roadrunner/scenes")

# Map RoadRunner Asset
actor_type = RoadRunnerActorMapper.map_roadrunner_asset("Vehicle.Rickshaw.Auto")
# Returns ActorType.AUTO_RICKSHAW
```
