"""
IRIS Vehicle Control Configuration (Combined Phase 13).
Defines control limits for speed, acceleration, braking, steering angle, steering rate,
and Pure Pursuit lookahead parameters.
"""

# Speed limits (m/s)
MAX_SPEED = 12.0                # ~43.2 km/h nominal max speed on Indian city road
NOMINAL_TARGET_SPEED = 8.0      # ~28.8 km/h cruise speed
CAUTION_SPEED = 5.0             # ~18.0 km/h caution target speed
SLOW_SPEED = 2.5                # ~9.0 km/h slow speed
MIN_SPEED = 0.0

# Acceleration & Deceleration limits (m/s²)
MAX_ACCELERATION = 2.5          # Comfort acceleration limit
MAX_DECELERATION = -4.5         # Hard braking limit
EMERGENCY_DECELERATION = -6.0   # Maximum emergency braking limit

# Steering limits (radians)
MAX_STEERING_ANGLE = 0.6        # ~34.4 degrees maximum steering lock
MAX_STEERING_RATE = 1.0         # Maximum steering angle change rate (rad/s)

# Pure Pursuit baseline geometric parameters
WHEELBASE = 2.5                 # Vehicle wheelbase (meters)
LOOKAHEAD_DISTANCE = 5.0        # Default baseline lookahead distance (meters)
MIN_LOOKAHEAD = 3.0             # Minimum lookahead distance floor (meters)
MAX_LOOKAHEAD = 12.0            # Maximum lookahead distance ceiling (meters)
LOOKAHEAD_GAIN = 0.5            # Speed lookahead gain (L_d = min_lookahead + gain * speed)

# Longitudinal P-Controller Gain
KP_LONGITUDINAL = 0.8           # Proportional gain for speed error (a = Kp * (v_target - v_current))
