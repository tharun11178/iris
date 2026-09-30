import math
from typing import List, Tuple, Dict, Any, Optional
from world.cell import CellState, GridCell
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator
from world.grid import OccupancyGrid
from configs.sim_config import GOAL_POSITION, ROAD_MARGIN, ROAD_WIDTH, ROAD_LENGTH
from surface.surface_model import SurfaceModel
from surface.surface_hazard import SurfaceHazard, SurfaceHazardType, TraversabilityState


class WorldModel:
    """
    Central spatial world representation facade.
    Synchronizes simulation ground truth into discrete occupancy and drivability grid representation,
    incorporating Phase 5 SurfaceModel.
    """

    def __init__(
        self,
        converter: Optional[CoordinateConverter] = None,
        evaluator: Optional[DrivableSpaceEvaluator] = None,
        goal_pos: Tuple[float, float] = GOAL_POSITION,
    ):
        self.converter = converter if converter is not None else CoordinateConverter()
        self.evaluator = evaluator if evaluator is not None else DrivableSpaceEvaluator()
        self.grid = OccupancyGrid(self.converter, self.evaluator)

        self.goal_position = goal_pos
        self.ego_state: Dict[str, Any] = {}
        self.dynamic_actors: List[Dict[str, Any]] = []
        self.static_hazards: List[Dict[str, Any]] = []
        self.surface_model = SurfaceModel()
        self.prediction_set: Optional[Any] = None
        self.future_occupancies: List[Any] = []
        self.uncertainty_set: Optional[Any] = None
        self.uncertainty_grid: Optional[Any] = None
        self.future_risk_field: Optional[Any] = None

    def set_goal_position(self, x_world: float, y_world: float):
        """
        Sets the navigation goal position in world coordinates.
        """
        self.goal_position = (x_world, y_world)

    def update_from_environment(
        self,
        env,
        perception_manager=None,
        detections=None,
        track_manager=None,
        tracks=None,
        prediction_manager=None,
        prediction_set=None,
        uncertainty_manager=None,
        uncertainty_set=None,
        future_risk_engine=None,
        future_risk_field=None,
    ):
        """
        Populates and rasterizes environment state onto the occupancy grid.
        `env` is an instance of SimulationEnvironment (Phase 1).
        If `track_manager` or `tracks` is provided, dynamic actors are populated from Phase 7 persistent Tracks.
        Else if `perception_manager` or `detections` is provided, populated from perceived DetectedObjects.
        Otherwise falls back to raw simulation ground truth actors.
        Optionally receives Phase 8 Motion Predictions and maps future grid occupancy.
        """
        # 1. Reset Grid & Mark Road Structure
        self.grid.reset_grid()
        self.grid.mark_road_structure(
            road_margin=ROAD_MARGIN,
            road_width=env.road.width,
            road_length=env.road.length,
        )

        # 2. Extract and Rasterize Static Road Surface Hazards into SurfaceModel
        self.static_hazards = []
        self.surface_model.clear()

        for hazard in env.surface_hazards:
            h_type_str = hazard.hazard_type.name if hasattr(hazard.hazard_type, "name") else str(hazard.hazard_type)
            radius = getattr(hazard, "radius", 0.0)
            wx, wy = self.converter.sim_to_world(hazard.x, hazard.y)

            # Map to SurfaceHazardType Enum
            if h_type_str == "POTHOLE":
                s_type = SurfaceHazardType.POTHOLE
            elif h_type_str in ("WATERLOGGED", "WATER"):
                s_type = SurfaceHazardType.WATERLOGGING
            elif h_type_str == "DEPRESSION":
                s_type = SurfaceHazardType.DEPRESSION
            elif h_type_str in ("SPEED_BREAKER", "RAISED_SURFACE", "RAISED"):
                s_type = SurfaceHazardType.RAISED_SURFACE
            elif h_type_str in ("UNEVEN_ROAD", "UNEVEN_TERRAIN", "UNEVEN"):
                s_type = SurfaceHazardType.UNEVEN_SURFACE
            elif h_type_str == "DEBRIS":
                s_type = SurfaceHazardType.DEBRIS
            elif h_type_str == "CONSTRUCTION":
                s_type = SurfaceHazardType.CONSTRUCTION
            else:
                s_type = SurfaceHazardType.POTHOLE

            depth_val = getattr(hazard, "depth", None)
            height_val = getattr(hazard, "height", None)
            rough_val = getattr(hazard, "roughness", None)
            conf_val = 1.0 - getattr(hazard, "uncertainty", 0.1)
            underlying_known = getattr(hazard, "underlying_surface_known", True)

            surf_hazard = SurfaceHazard(
                hazard_id=str(getattr(hazard, "hazard_id", len(self.surface_model.get_hazards()) + 1)),
                hazard_type=s_type,
                position=(wx, wy),
                length=hazard.length,
                width=hazard.width,
                depth=depth_val,
                height=height_val,
                roughness=rough_val,
                severity=hazard.severity,
                confidence=conf_val,
                underlying_surface_known=underlying_known,
                description=f"{s_type.name} at X={wx:.1f}m",
            )
            self.surface_model.add_hazard(surf_hazard)

            h_data = {
                "id": surf_hazard.hazard_id,
                "type": s_type.name,
                "x": wx,
                "y": wy,
                "radius": radius,
                "length": hazard.length,
                "width": hazard.width,
                "severity": surf_hazard.severity,
                "confidence": surf_hazard.confidence,
                "traversability": surf_hazard.traversability.name,
                "surface_risk": surf_hazard.surface_risk,
            }
            self.static_hazards.append(h_data)

            # Determine cell state mapping
            c_state = CellState.OCCUPIED
            if s_type == SurfaceHazardType.POTHOLE:
                c_state = CellState.POTHOLE
            elif s_type == SurfaceHazardType.WATERLOGGING:
                c_state = CellState.WATER
            elif s_type == SurfaceHazardType.RAISED_SURFACE:
                c_state = CellState.RAISED
            elif s_type == SurfaceHazardType.UNEVEN_SURFACE:
                c_state = CellState.UNEVEN_TERRAIN
            elif surf_hazard.traversability == TraversabilityState.NON_TRAVERSABLE:
                c_state = CellState.OCCUPIED

            if radius > 0:
                self.grid.rasterize_circle(
                    center_x=wx,
                    center_y=wy,
                    radius=radius,
                    state=c_state,
                    hazard_type=s_type.name,
                    severity=surf_hazard.severity,
                    confidence=surf_hazard.confidence,
                    is_dynamic=False,
                )
            else:
                self.grid.rasterize_oriented_box(
                    center_x=wx,
                    center_y=wy,
                    length=hazard.length,
                    width=hazard.width,
                    heading=0.0,
                    state=c_state,
                    hazard_type=s_type.name,
                    severity=surf_hazard.severity,
                    confidence=surf_hazard.confidence,
                    is_dynamic=False,
                )

        # 3. Extract and Rasterize Dynamic Traffic Actors (Tracking vs Perception vs Ground Truth)
        self.dynamic_actors = []

        if tracks is None and track_manager is not None:
            tracks = track_manager.get_active_tracks()

        if tracks is not None:
            # Populate dynamic actors from Phase 7 persistent Track objects
            for track in tracks:
                a_type_str = track.object_type.name if hasattr(track.object_type, "name") else str(track.object_type)
                wx, wy = track.current_position
                vx, vy = track.velocity

                a_data = {
                    "id": track.track_id,
                    "track_id": track.track_id,
                    "type": a_type_str,
                    "x": wx,
                    "y": wy,
                    "vx": vx,
                    "vy": vy,
                    "speed": track.speed,
                    "heading": track.heading,
                    "length": track.length,
                    "width": track.width,
                    "confidence": track.confidence,
                    "state": track.state.name if hasattr(track.state, "name") else str(track.state),
                    "history": list(track.history),
                    "track": track,
                }
                self.dynamic_actors.append(a_data)

                self.grid.rasterize_oriented_box(
                    center_x=wx,
                    center_y=wy,
                    length=track.length,
                    width=track.width,
                    heading=track.heading,
                    state=CellState.DYNAMIC_OBJECT,
                    hazard_type=a_type_str,
                    severity=1.0,
                    confidence=track.confidence,
                    entity_id=track.track_id,
                    is_dynamic=True,
                )

        elif detections is not None or perception_manager is not None:
            if detections is None and perception_manager is not None:
                detections = perception_manager.process(env)

            # Populate dynamic actors from perceived DetectedObjects (Phase 6 fallback)
            for det in detections:
                a_type_str = det.object_type.name if hasattr(det.object_type, "name") else str(det.object_type)
                wx, wy = det.position
                vx = det.velocity[0] if det.velocity else 0.0
                vy = det.velocity[1] if det.velocity else 0.0

                a_data = {
                    "id": det.object_id,
                    "type": a_type_str,
                    "x": wx,
                    "y": wy,
                    "vx": vx,
                    "vy": vy,
                    "heading": det.heading,
                    "length": det.length,
                    "width": det.width,
                    "confidence": det.confidence,
                    "detected_object": det,
                }
                self.dynamic_actors.append(a_data)

                self.grid.rasterize_oriented_box(
                    center_x=wx,
                    center_y=wy,
                    length=det.length,
                    width=det.width,
                    heading=det.heading,
                    state=CellState.DYNAMIC_OBJECT,
                    hazard_type=a_type_str,
                    severity=1.0,
                    confidence=det.confidence,
                    entity_id=det.object_id,
                    is_dynamic=True,
                )
        else:
            # Fallback: Ground truth from simulation actors (Phase 1 fallback)
            for actor in env.traffic_actors:
                a_type_str = actor.actor_type.name if hasattr(actor.actor_type, "name") else str(actor.actor_type)
                wx, wy = self.converter.sim_to_world(actor.x, actor.y)
                a_data = {
                    "id": str(actor.actor_id),
                    "type": a_type_str,
                    "x": wx,
                    "y": wy,
                    "vx": actor.velocity * math.cos(actor.heading),
                    "vy": actor.velocity * math.sin(actor.heading),
                    "heading": actor.heading,
                    "length": actor.length,
                    "width": actor.width,
                    "confidence": 1.0,
                }
                self.dynamic_actors.append(a_data)

                self.grid.rasterize_oriented_box(
                    center_x=wx,
                    center_y=wy,
                    length=actor.length,
                    width=actor.width,
                    heading=actor.heading,
                    state=CellState.DYNAMIC_OBJECT,
                    hazard_type=a_type_str,
                    severity=1.0,
                    confidence=1.0,
                    entity_id=str(actor.actor_id),
                    is_dynamic=True,
                )

        # 4. Extract and Rasterize Ego Vehicle
        ego = env.ego_vehicle
        ego_wx, ego_wy = self.converter.sim_to_world(ego.x, ego.y)
        self.ego_state = {
            "x": ego_wx,
            "y": ego_wy,
            "speed": ego.velocity,
            "heading": ego.heading,
            "steering": ego.steering_angle,
            "length": ego.length,
            "width": ego.width,
        }

        self.grid.rasterize_oriented_box(
            center_x=ego_wx,
            center_y=ego_wy,
            length=ego.length,
            width=ego.width,
            heading=ego.heading,
            state=CellState.VEHICLE,
            hazard_type="EGO_VEHICLE",
            severity=0.0,
            confidence=1.0,
            entity_id="EGO",
            is_dynamic=True,
        )

        # 5. Process Phase 8 Motion Predictions and Future Occupancies
        if prediction_set is not None:
            self.prediction_set = prediction_set
            if prediction_manager is not None:
                self.future_occupancies = prediction_manager.convert_to_future_occupancy(
                    prediction_set, self.converter, self.grid.num_cols, self.grid.num_rows, self.grid.grid_res
                )
        elif prediction_manager is not None:
            active_t = tracks if tracks is not None else (track_manager.get_active_tracks() if track_manager else [])
            self.prediction_set = prediction_manager.predict(active_t, timestamp=env.sim_time, road_evaluator=self.is_drivable_at_world)
            self.future_occupancies = prediction_manager.convert_to_future_occupancy(
                self.prediction_set, self.converter, self.grid.num_cols, self.grid.num_rows, self.grid.grid_res
            )

        # 6. Process Phase 9 Uncertainty Set & Grid
        if uncertainty_set is not None:
            self.uncertainty_set = uncertainty_set
            if uncertainty_manager is not None:
                self.uncertainty_grid = uncertainty_manager.build_uncertainty_grid(
                    self.uncertainty_set, self.converter, self.grid.num_cols, self.grid.num_rows, self.grid.grid_res
                )
        elif uncertainty_manager is not None:
            active_t = tracks if tracks is not None else (track_manager.get_active_tracks() if track_manager else [])
            self.uncertainty_set = uncertainty_manager.evaluate_uncertainty(
                active_t, self.prediction_set, current_time=env.sim_time
            )
            self.uncertainty_grid = uncertainty_manager.build_uncertainty_grid(
                self.uncertainty_set, self.converter, self.grid.num_cols, self.grid.num_rows, self.grid.grid_res
            )

        # 7. Process Phase 10 Future Risk Field
        if future_risk_field is not None:
            self.future_risk_field = future_risk_field
        elif future_risk_engine is not None:
            self.future_risk_field = future_risk_engine.compute_future_risk_field(self)





    def is_drivable_at_world(self, x_world: float, y_world: float) -> bool:
        """
        Returns True if the given world coordinate falls inside a drivable grid cell.
        """
        cell = self.grid.get_cell_at_world(x_world, y_world)
        if cell is not None:
            return cell.is_drivable
        return False
