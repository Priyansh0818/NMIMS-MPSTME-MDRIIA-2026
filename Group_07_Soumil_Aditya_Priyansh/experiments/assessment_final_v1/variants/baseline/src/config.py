"""Central configuration for the hospital-cleaning system (MDRIIA Group 07).
Every tunable lives here; nothing about rates, speeds, zones or object classes is hard-coded elsewhere.
"""
import math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENE_MODELS = {
    "classic": os.path.join(ROOT, "models", "hospital_clutter_manipulator.xml"),
    "nova": os.path.join(ROOT, "models", "hospital_nova3d.xml"),
}
DEFAULT_SCENE = "nova"
MODEL_PATH = SCENE_MODELS[DEFAULT_SCENE]
ANALYTICS_DIR = os.path.join(ROOT, "analytics")

# ----------------------------------------------------------------------------------------
# Update rates (Hz).  Physics runs at the MJCF timestep (0.002 s = 500 Hz); everything else is
# scheduled in *simulation* time, so no subsystem runs every physics step.
# ----------------------------------------------------------------------------------------
CONTROL_HZ = 50        # base/arm controller + state machine
PERCEPTION_HZ = 10     # ray-cast RGB-D sensing (only while the state machine asks for it)
TELEMETRY_HZ = 10
RENDER_FPS = 60        # viewer.sync() rate (wall clock)
DEBUG_DRAW_HZ = 15     # debug marker refresh (wall clock)
MAX_CATCHUP_S = 0.10   # never try to catch up more than this much simulated time per frame

# ----------------------------------------------------------------------------------------
# Base motion (SI units).  Wheel actuators are velocity servos in *motor* rad/s with gear 3 and
# 35 N.m Coulomb friction -> wheel rad/s ~= (ctrl - 0.583)/3.   ctrl range +-20 => 0.33 m/s per wheel.
# ----------------------------------------------------------------------------------------
BASE_V_MAX = 0.30        # m/s   (Stretch 3 nominal max)
BASE_W_MAX = 1.10        # rad/s
BASE_A_MAX = 0.60        # m/s^2
BASE_ALPHA_MAX = 2.5     # rad/s^2
BASE_V_FINAL = 0.05      # creep speed for alignment moves
WHEEL_FRICTION_FF = 0.583  # ctrl units that exactly cancel wheel Coulomb friction

# Arm / lift / wrist / gripper speed limits (rate-limited set-points, units per second)
LIFT_SPEED = 0.22
ARM_SPEED = 0.25
WRIST_SPEED = 1.8
HEAD_SPEED = 1.5
GRIPPER_SPEED = 0.12     # ctrl units/s (full stroke 0.06 -> 0.5 s)

# Travel posture: gripper pointing down, arm retracted, lift low -> compact footprint
TRAVEL_LIFT = 0.30
TRAVEL_PITCH = -math.pi / 2
GRIPPER_OPEN = 0.04
GRIPPER_CLOSE = -0.02

# ----------------------------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------------------------
GRID_RES = 0.05
GRID_X = (-2.80, 3.50)
GRID_Y = (-2.50, 2.50)
N_HEADINGS = 24                 # 15 deg heading lattice
FOOTPRINT_MARGIN = 0.07         # extra clearance around the *measured* stowed footprint (m)
ROBOT_Z_MAX = 1.45              # obstacles whose lowest point is above this are ignored
CLUTTER_OBSTACLE_R = 0.07       # un-picked clutter is treated as a small obstacle
REPLAN_LIMIT = 3
SAFETY_LOOKAHEAD = 0.12         # m, reactive stop distance
GOAL_POS_TOL = 0.04
GOAL_YAW_TOL = math.radians(3)

# ----------------------------------------------------------------------------------------
# Grasping (calibrated experimentally in MuJoCo: top-down pinch, pads ~4.5 cm below object top)
# ----------------------------------------------------------------------------------------
GRASP_DEPTH = 0.045             # gripper centre this far below the object top
GRASP_MIN_Z = 0.03              # gripper centre cannot go below this (floor)
HOVER_CLEARANCE = 0.10          # gripper-centre height above object top while approaching
EXT_RANGE = (0.03, 0.50)        # usable arm extension (m)
LIFT_RANGE = (0.02, 1.09)
CARRY_LIFT_EXTRA = 0.18         # extra lift after grasp before retracting
MAX_GRASP_ATTEMPTS = 3
HOLD_SQUEEZE = 0.006           # after contact, command the gripper only this far past the measured aperture (moderate force)
MIN_GRIP_FORCE = 3.0            # N, summed normal force on finger pads
APPROACH_EXTS = (0.30, 0.22, 0.38)
LIFT_VERIFY_RISE = 0.06

# ----------------------------------------------------------------------------------------
# Clutter catalogue.  type -> category; spawn region per object (x0,x1,y0,y1, mode)
# mode 'floor' or 'surface' (height found by ray-cast, so objects sit on tables/bed/sofa)
# ----------------------------------------------------------------------------------------
CATEGORY_OF_TYPE = {
    "cup": "RECYCLABLE", "bottle": "RECYCLABLE", "paper": "RECYCLABLE",
    "wrapper": "TRASH", "plasticpack": "TRASH",
    "glove": "BIO_WASTE", "gauze": "BIO_WASTE",
    "towel": "LAUNDRY", "personal": "ITEM_RETURN",
}
# Known-catalogue prototypes used by the classifier: (height m, width m, rgb)
TYPE_PROTOTYPES = {
    "cup": (0.11, 0.07, (0.95, 0.45, 0.15)), "bottle": (0.18, 0.06, (0.20, 0.50, 0.95)),
    "paper": (0.08, 0.07, (0.97, 0.97, 0.97)), "glove": (0.07, 0.06, (0.30, 0.75, 0.85)),
    "wrapper": (0.13, 0.05, (0.95, 0.85, 0.15)), "plasticpack": (0.08, 0.05, (0.75, 0.90, 0.80)),
    "towel": (0.09, 0.08, (0.15, 0.65, 0.45)), "gauze": (0.09, 0.06, (0.95, 0.55, 0.60)),
    "personal": (0.09, 0.056, (0.25, 0.25, 0.30)),
}
SPAWN = {   # object name -> (x0, x1, y0, y1, mode)
    "cup_1": (0.80, 0.92, 0.20, 0.40, "surface"),     # bedside table
    "cup_2": (-1.10, -0.90, 1.15, 1.40, "floor"),     # near chair
    "bottle_1": (1.28, 1.38, -0.90, -0.50, "floor"),  # beside bed
    "bottle_2": (3.05, 3.25, -0.70, -0.30, "floor"),  # near east wall
    "paper_1": (0.40, 0.80, -1.10, -0.80, "floor"),   # open area
    "paper_2": (-0.95, -0.70, -1.30, -1.00, "floor"), # near sofa
    "glove_1": (-1.35, -1.15, -2.00, -1.85, "floor"), # near sink
    "glove_2": (1.80, 2.20, 0.80, 1.10, "floor"),     # north of bed
    "wrapper_1": (-1.50, -1.40, -0.10, 0.05, "surface"),  # coffee table
    "plasticpack_1": (-1.00, -0.85, 0.55, 0.75, "floor"), # beside chair
    "towel_1": (-1.30, -1.25, -1.28, -1.16, "surface"),   # sofa seat
    "towel_2": (1.80, 2.20, 0.20, 0.35, "surface"),       # foot of bed
    "gauze_1": (-0.08, 0.08, -1.64, -1.58, "surface"),    # cart top
    "personal_1": (-2.50, -2.30, 1.00, 1.40, "floor"),    # near west wall
    "personal_2": (2.90, 3.20, 1.20, 1.50, "floor"),      # NE corner
}
SPAWN_JITTER_YAW = True

# ----------------------------------------------------------------------------------------
# Destination zones.  Edit here to move/rename bins -- nothing else hard-codes them.
# ----------------------------------------------------------------------------------------
ZONES = {
    "trash_bin":      dict(body="trash_bin", ix=0.15, iy=0.15, rim_z=0.40, floor_z=0.02),
    "recycling_bin":  dict(body="recycling_bin", ix=0.15, iy=0.15, rim_z=0.40, floor_z=0.02),
    "laundry_basket": dict(body="laundry_basket", ix=0.18, iy=0.14, rim_z=0.36, floor_z=0.02),
    "return_tray":    dict(body="return_tray", ix=0.17, iy=0.13, rim_z=0.71, floor_z=0.61),
}
CATEGORY_TO_ZONE = {
    "TRASH": "trash_bin", "BIO_WASTE": "trash_bin", "RECYCLABLE": "recycling_bin",
    "LAUNDRY": "laundry_basket", "ITEM_RETURN": "return_tray",
}
DROP_CLEARANCE = 0.05           # object bottom this far above the rim when releasing
DROP_EXTS = (0.30, 0.38, 0.22)

# ----------------------------------------------------------------------------------------
# Robot start
# ----------------------------------------------------------------------------------------
START_POSE = (0.20, -0.40, 0.0)   # x, y, yaw
SCAN_HEAD_TILT = -0.55
SCAN_FOV_DEG = (74.0, 58.0)       # horizontal, vertical (d435i)
SCAN_RAYS = (128, 96)
PRIORITY = "nearest"              # 'nearest' | 'confidence' | 'category'
TASK_TIMEOUT_S = 150.0            # per object, sim time
