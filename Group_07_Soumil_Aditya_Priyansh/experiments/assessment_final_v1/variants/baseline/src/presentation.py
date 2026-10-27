"""Camera choreography for the real MuJoCo scene; never changes simulation state."""
import math
import numpy as np

CAMERAS = [
    ('Ward overview', (.3,0,.45), 10.1, -45, -37),
    ('Robot close-up', None, 2.8, -40, -26),
    ('Patient suite', (1.65,-.35,.65), 4.8, -65, -28),
    ('Sorting station', (.5,1.65,.3), 4.6, -20, -35),
    ('Plan view', (.3,0,0), 8.5, 90, -88),
]

NOVA_CAMERAS = [
    ('Nova3D ward overview', (.35,0,.65), 10.1, 45, -36),
    ('Robot close-up', None, 2.8, 35, -26),
    ('Patient suite', (1.65,-.5,.65), 4.8, 35, -28),
    ('Sorting station', (.5,1.9,.5), 3.7, 90, -25),
    ('Plan view', (.3,0,0), 8.5, 90, -88),
]


class CameraDirector:
    def __init__(self):
        self.index=0; self.orbit=False; self.cameras=CAMERAS

    def apply(self, camera, system, *, smooth=False):
        self.cameras=NOVA_CAMERAS if system.model_path.endswith('hospital_nova3d.xml') else CAMERAS
        name,look,distance,azimuth,elevation=self.cameras[self.index]
        target=np.asarray(look if look is not None else (*system.rb.base_pose()[:2],.48))
        alpha=.07 if smooth else 1.
        camera.lookat[:] += alpha*(target-camera.lookat)
        camera.distance += alpha*(distance-camera.distance)
        target_az=azimuth + (12*math.sin(system.ctrl.t/18) if self.orbit else 0)
        camera.azimuth += alpha*((target_az-camera.azimuth+180)%360-180)
        camera.elevation += alpha*(elevation-camera.elevation)
        return (np.linalg.norm(camera.lookat-target)<.005 and abs(camera.distance-distance)<.005
                and abs((target_az-camera.azimuth+180)%360-180)<.1 and abs(camera.elevation-elevation)<.1)

    def next(self): self.index=(self.index+1)%len(self.cameras)

    @property
    def name(self): return self.cameras[self.index][0]


def status_text(system, director, fps=0, rtf=0):
    ctrl=system.ctrl
    target=ctrl.target.name.replace('_',' ').title() if ctrl.target else 'Surveying ward'
    return ('WARD 07  |  AUTONOMOUS CARE SUPPORT\n'
            'NMIMS MPSTME  /  MDRIIA CAPSTONE\n\n'
            f'{ctrl.state.replace("_"," ")}\n'
            f'Target: {target}\n'
            f'Placement events: {len(ctrl.cleaned)}   Failed tasks: {len(ctrl.failed)}\n'
            f'Physics 500 Hz   Measurement log 500 Hz\n'
            f'Simulation {ctrl.t:.1f}s   Playback {rtf:.2f}x   Viewer {fps:.0f} fps\n\n'
            f'{director.name}\n'
            'C Camera   O Cinematic motion   D Diagnostics\n'
            'Space Pause   1/2/3 Playback speed')
