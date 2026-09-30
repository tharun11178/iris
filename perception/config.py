"""
IRIS Traffic Perception Configuration (Phase 6).
Centralized parameters for sensor detection range, noise levels, confidence parameters,
and perception pipeline settings.
"""

# Detection Parameters
DETECTION_RANGE: float = 50.0       # Maximum perception sensor detection range in meters
MIN_CONFIDENCE: float = 0.10        # Minimum valid detection confidence threshold
MAX_CONFIDENCE: float = 1.00        # Maximum upper confidence limit

# Simulated Perception Noise Configuration
USE_SIMULATED_NOISE: bool = False   # Set to True to enable realistic sensor noise simulation
POSITION_NOISE_STD: float = 0.25    # Standard deviation of Gaussian position noise (meters)
MISS_PROBABILITY: float = 0.05      # Probability of a visible actor being missed by detector (5%)
CONFIDENCE_RANGE: tuple = (0.75, 0.98) # Random uniform range for confidence when noise is enabled

# Evaluation Parameters
MATCH_DISTANCE_THRESHOLD: float = 1.5 # Maximum distance (m) to match perceived object to ground truth

# Random Seed for Deterministic Testing
RANDOM_SEED: int = 42
