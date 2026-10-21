"""Tunable constants for the third-person prototype. Units: metres, seconds, radians."""
import math

# Movement
WALK_SPEED = 2.2
SPRINT_SPEED = 5.0
CROUCH_SPEED = 1.2
AIM_SPEED = 1.6
JUMP_SPEED = 4.6
GRAVITY = 14.0
STEP_HEIGHT = 0.35
BODY_RADIUS = 0.30
STAND_HEIGHT = 1.78
CROUCH_HEIGHT = 1.15
SIT_HEIGHT = 1.10
TURN_RATE = 12.0          # rad/s model turn smoothing
ACCEL = 14.0              # 1/s horizontal velocity smoothing

# Camera
MOUSE_SENS = 0.0025
PITCH_MIN = math.radians(-60)
PITCH_MAX = math.radians(70)
CAM_DISTANCE = 3.2
CAM_DISTANCE_AIM = 1.8
CAM_SHOULDER = 0.55       # +right shoulder offset
CAM_SHOULDER_AIM = 0.75
CAM_HEIGHT_STAND = 1.55
CAM_HEIGHT_CROUCH = 1.00
CAM_HEIGHT_SIT = 0.95
CAM_MIN_DISTANCE = 0.4
FOV_NORMAL = 70.0
FOV_AIM = 52.0
