"""
IRIS Simulation Configuration Specification.
Contains visual parameters, vehicle dynamics constraints, road geometry definitions,
and entity default dimensions for Phase 1 simulation foundation.
"""

# Screen & Display Settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
PPM = 16.0  # Pixels Per Meter (1 meter = 16 pixels)

# World & Road Geometry (Continuous coordinates in meters)
# X-axis runs along the road (longitudinal), Y-axis runs laterally across the road width.
ROAD_LENGTH = 300.0   # Total length of simulated road stretch in meters
ROAD_WIDTH = 12.0     # Total drivable road width in meters (unstructured 2-lane / multi-use)
ROAD_MARGIN = 3.0     # Off-road shoulder width on each side in meters

# Ego Vehicle Parameters
EGO_LENGTH = 4.6      # meters
EGO_WIDTH = 2.0       # meters
EGO_MAX_SPEED = 25.0  # m/s (~90 km/h)
EGO_MIN_SPEED = -5.0  # m/s (reverse max)
EGO_MAX_ACCEL = 4.0   # m/s^2
EGO_MAX_BRAKE = 8.0   # m/s^2
EGO_MAX_STEER = 0.5   # radians (~28 degrees)

# Traffic Actor Typical Dimensions (meters)
ACTOR_SPECS = {
    "CAR": {"length": 4.5, "width": 1.8, "max_speed": 22.0},
    "BUS_TRUCK": {"length": 9.0, "width": 2.5, "max_speed": 15.0},
    "AUTO_RICKSHAW": {"length": 2.8, "width": 1.3, "max_speed": 12.0},
    "MOTORCYCLE": {"length": 2.0, "width": 0.8, "max_speed": 20.0},
    "BICYCLE": {"length": 1.8, "width": 0.6, "max_speed": 6.0},
    "PEDESTRIAN": {"length": 0.6, "width": 0.6, "max_speed": 2.0},
    "CATTLE": {"length": 2.2, "width": 1.1, "max_speed": 3.0},
    "PUSHCART": {"length": 2.2, "width": 1.2, "max_speed": 3.0},
}

# Color Palette (RGB)
COLOR_BACKGROUND = (30, 32, 38)
COLOR_GRASS = (42, 58, 44)
COLOR_ASPHALT = (45, 48, 56)
COLOR_ROAD_EDGE = (210, 215, 220)
COLOR_UNMARKED_CENTER = (100, 105, 115)

# Entity Colors
COLOR_EGO = (58, 134, 255)         # Vibrant Electric Blue
COLOR_CAR = (76, 201, 240)         # Cyan
COLOR_BUS_TRUCK = (247, 37, 133)    # Deep Magenta / Pink
COLOR_AUTO_RICKSHAW = (255, 183, 3) # Bright Auto Yellow / Amber
COLOR_MOTORCYCLE = (230, 57, 70)    # Crimson Red
COLOR_PEDESTRIAN = (144, 224, 239)  # Light Sky Blue
COLOR_CATTLE = (186, 115, 54)       # Earthy Brown
COLOR_PUSHCART = (138, 154, 91)     # Olive Green

# Surface Hazard Colors
COLOR_POTHOLE = (28, 20, 18)        # Dark Craggy Pothole
COLOR_WATERLOGGED = (42, 123, 155)  # Water Blue
COLOR_SPEED_BREAKER = (220, 160, 40) # Yellow-black stripe representation
COLOR_DEBRIS = (120, 110, 100)      # Grayish rubble

# Phase 2 Grid & World Model Parameters
GRID_RESOLUTION = 0.5   # Meters per grid cell (e.g. 0.5m x 0.5m cell)
GOAL_POSITION = (250.0, 9.0) # (X_meters, Y_meters) Target destination goal in World Grid frame

# Grid Overlay Colors (RGB with transparency support in Pygame)
GRID_COLOR_DRIVABLE = (46, 204, 113, 80)     # Soft Emerald Green
GRID_COLOR_OCCUPIED = (231, 76, 60, 120)     # Crimson Red
GRID_COLOR_POTHOLE = (230, 126, 34, 120)     # Orange
GRID_COLOR_WATER = (52, 152, 219, 120)       # Blue
GRID_COLOR_UNEVEN = (241, 196, 15, 120)      # Yellow
GRID_COLOR_OUTSIDE = (50, 50, 50, 120)       # Dark Gray
GRID_COLOR_BOUNDARY = (149, 165, 166, 120)   # Light Gray
GRID_COLOR_VEHICLE = (155, 89, 182, 160)     # Purple / Magenta
GRID_COLOR_GOAL = (255, 215, 0, 200)         # Bright Gold

# Default Drivability Rules (Cell state -> is_drivable)
DEFAULT_DRIVABILITY_RULES = {
    "FREE": True,
    "OCCUPIED": False,
    "POTHOLE": False,
    "WATER": False,
    "UNEVEN_TERRAIN": True,   # Restricted (drivable with speed penalty)
    "RAISED": True,           # Restricted (drivable with speed penalty)
    "ROAD_BOUNDARY": False,
    "OUTSIDE_ROAD": False,
    "VEHICLE": False,
    "DYNAMIC_OBJECT": False,
}

