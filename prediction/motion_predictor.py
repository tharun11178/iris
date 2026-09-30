"""
IRIS Motion Predictor Module (Phase 8).
Implements Constant Velocity, Constant Acceleration, Multi-Hypothesis generation,
and geometric prediction envelopes for dynamic road participants.
"""

import math
from typing import List, Tuple, Optional, Any
from tracking.track import Track
from perception.object_classes import ObjectClass
from prediction.trajectory import PredictedTrajectory, PredictionHypothesis
from prediction.behavior_model import get_behavior_profile, classify_motion_pattern, BehaviorCategory
from prediction.config import (
    PREDICTION_HORIZON,
    PREDICTION_TIME_STEP,
    STOP_SPEED_THRESHOLD,
    CONFIDENCE_DECAY_RATE,
    ROAD_CONSTRAINT_ENABLED,
)


class MotionPredictor:
    """
    Core trajectory prediction engine executing baseline motion models and multi-hypothesis branching.
    """

    def __init__(
        self,
        horizon: float = PREDICTION_HORIZON,
        time_step: float = PREDICTION_TIME_STEP,
        decay_rate: float = CONFIDENCE_DECAY_RATE,
        stop_speed_threshold: float = STOP_SPEED_THRESHOLD,
    ):
        self.horizon = horizon
        self.time_step = time_step
        self.decay_rate = decay_rate
        self.stop_speed_threshold = stop_speed_threshold

    def generate_time_steps(self, start_timestamp: float) -> Tuple[List[float], List[float]]:
        """
        Generates relative time offsets and absolute simulation timestamps.
        
        :param start_timestamp: Current simulation timestamp t0.
        :return: Tuple of (offsets_list, timestamps_list).
        """
        offsets = []
        timestamps = []
        t_curr = self.time_step
        while t_curr <= self.horizon + 1e-5:
            offsets.append(round(t_curr, 2))
            timestamps.append(round(start_timestamp + t_curr, 2))
            t_curr += self.time_step
        return offsets, timestamps

    def estimate_heading(self, track: Track) -> float:
        """
        Estimates motion heading yaw angle in radians from velocity vector,
        falling back to track heading if speed is near zero.
        """
        if track.speed >= self.stop_speed_threshold and (track.velocity[0] != 0.0 or track.velocity[1] != 0.0):
            return math.atan2(track.velocity[1], track.velocity[0])
        return track.heading

    def predict_constant_velocity(
        self,
        track: Track,
        start_timestamp: float = 0.0,
        road_evaluator: Optional[Any] = None,
    ) -> PredictedTrajectory:
        """
        Generates baseline Constant Velocity trajectory prediction:
        x(t) = x0 + vx * t, y(t) = y0 + vy * t.
        
        :param track: Input persistent Track object.
        :param start_timestamp: Current simulation timestamp.
        :param road_evaluator: Optional road drivability or boundary checker function.
        :return: PredictedTrajectory instance.
        """
        x0, y0 = track.current_position
        vx, vy = track.velocity
        profile = get_behavior_profile(track.object_type)
        heading = self.estimate_heading(track)

        # Stopped object check
        if track.speed < self.stop_speed_threshold:
            vx, vy = 0.0, 0.0

        offsets, timestamps = self.generate_time_steps(start_timestamp)
        predicted_positions = []
        plausibility = []

        for dt in offsets:
            px = x0 + vx * dt
            py = y0 + vy * dt
            predicted_positions.append((px, py))

            # Check road boundary plausibility
            is_valid = True
            if ROAD_CONSTRAINT_ENABLED and road_evaluator is not None:
                is_valid = road_evaluator(px, py)
            plausibility.append(is_valid)

        # Horizon confidence decay: c(t_final) = max(0.1, c_track * (1 - decay * horizon))
        final_conf = max(0.1, track.confidence * (1.0 - self.decay_rate * self.horizon))

        return PredictedTrajectory(
            track_id=track.track_id,
            object_type=track.object_type,
            start_position=(x0, y0),
            predicted_positions=predicted_positions,
            timestamps=timestamps,
            prediction_horizon=self.horizon,
            time_step=self.time_step,
            confidence=round(final_conf, 3),
            model_name="constant_velocity",
            envelope_margins=(profile.lateral_margin, profile.longitudinal_margin),
            road_plausibility=plausibility,
            heading=heading,
        )

    def predict_constant_acceleration(
        self,
        track: Track,
        start_timestamp: float = 0.0,
        road_evaluator: Optional[Any] = None,
    ) -> PredictedTrajectory:
        """
        Generates optional Constant Acceleration trajectory prediction:
        x(t) = x0 + vx * t + 0.5 * ax * t^2, y(t) = y0 + vy * t + 0.5 * ay * t^2.
        
        :param track: Input persistent Track object.
        :param start_timestamp: Current simulation timestamp.
        :param road_evaluator: Optional road boundary checker.
        :return: PredictedTrajectory instance.
        """
        x0, y0 = track.current_position
        vx, vy = track.velocity
        ax, ay = track.acceleration if track.acceleration else (0.0, 0.0)
        profile = get_behavior_profile(track.object_type)
        heading = self.estimate_heading(track)

        if track.speed < self.stop_speed_threshold:
            vx, vy, ax, ay = 0.0, 0.0, 0.0, 0.0

        offsets, timestamps = self.generate_time_steps(start_timestamp)
        predicted_positions = []
        plausibility = []

        for dt in offsets:
            px = x0 + vx * dt + 0.5 * ax * (dt ** 2)
            py = y0 + vy * dt + 0.5 * ay * (dt ** 2)
            predicted_positions.append((px, py))

            is_valid = True
            if ROAD_CONSTRAINT_ENABLED and road_evaluator is not None:
                is_valid = road_evaluator(px, py)
            plausibility.append(is_valid)

        final_conf = max(0.1, track.confidence * (1.0 - self.decay_rate * self.horizon))

        return PredictedTrajectory(
            track_id=track.track_id,
            object_type=track.object_type,
            start_position=(x0, y0),
            predicted_positions=predicted_positions,
            timestamps=timestamps,
            prediction_horizon=self.horizon,
            time_step=self.time_step,
            confidence=round(final_conf, 3),
            model_name="constant_acceleration",
            envelope_margins=(profile.lateral_margin, profile.longitudinal_margin),
            road_plausibility=plausibility,
            heading=heading,
        )

    def predict_multi_hypothesis(
        self,
        track: Track,
        start_timestamp: float = 0.0,
        road_evaluator: Optional[Any] = None,
    ) -> List[PredictionHypothesis]:
        """
        Generates multi-hypothesis trajectories for irregular/unstructured road users (e.g., Cattle, Pedestrians).
        Branching:
        - H1: FORWARD (nominal direction)
        - H2: TURN_LEFT (+30 deg deflection)
        - H3: TURN_RIGHT (-30 deg deflection)
        
        :param track: Input persistent Track object.
        :param start_timestamp: Current simulation timestamp.
        :param road_evaluator: Optional road checker function.
        :return: List of PredictionHypothesis instances.
        """
        profile = get_behavior_profile(track.object_type)
        x0, y0 = track.current_position
        speed = track.speed
        heading = self.estimate_heading(track)
        offsets, timestamps = self.generate_time_steps(start_timestamp)

        hypotheses = []

        # Define 3 plausible motion branching angles (in radians)
        branches = [
            ("H1", "FORWARD", 0.0, 0.50),
            ("H2", "TURN_LEFT", math.radians(30.0), 0.25),
            ("H3", "TURN_RIGHT", math.radians(-30.0), 0.25),
        ]

        for h_id, b_type, angle_offset, prob in branches:
            branch_heading = heading + angle_offset
            if speed >= self.stop_speed_threshold:
                b_vx = speed * math.cos(branch_heading)
                b_vy = speed * math.sin(branch_heading)
            else:
                # If stopped, generate small exploratory shift for irregular objects
                step_val = 0.5 if b_type != "FORWARD" else 0.0
                b_vx = step_val * math.cos(branch_heading)
                b_vy = step_val * math.sin(branch_heading)

            predicted_positions = []
            plausibility = []

            for dt in offsets:
                px = x0 + b_vx * dt
                py = y0 + b_vy * dt
                predicted_positions.append((px, py))

                is_valid = True
                if ROAD_CONSTRAINT_ENABLED and road_evaluator is not None:
                    is_valid = road_evaluator(px, py)
                plausibility.append(is_valid)

            final_conf = max(0.1, track.confidence * (1.0 - self.decay_rate * self.horizon) * prob * 2.0)

            traj = PredictedTrajectory(
                track_id=track.track_id,
                object_type=track.object_type,
                start_position=(x0, y0),
                predicted_positions=predicted_positions,
                timestamps=timestamps,
                prediction_horizon=self.horizon,
                time_step=self.time_step,
                confidence=round(final_conf, 3),
                model_name=f"multi_hypothesis_{b_type.lower()}",
                envelope_margins=(profile.lateral_margin, profile.longitudinal_margin),
                road_plausibility=plausibility,
                heading=branch_heading,
            )

            hypo = PredictionHypothesis(
                track_id=track.track_id,
                hypothesis_id=h_id,
                trajectory=traj,
                probability_placeholder=prob,
                behavior_type=b_type,
                confidence=round(final_conf, 3),
            )
            hypotheses.append(hypo)

        return hypotheses
