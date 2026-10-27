"""Shared, condition-independent measurement definitions for the frozen study."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np

HANDLING = {'PREGRASP','REFINE','DESCEND','CLOSE','VERIFY_GRIP','LIFT','RECOVER',
            'STOW','PLAN_DROP','NAV_DROP','DROP_DEPLOY','RELEASE','VERIFY_PLACE','RETRACT'}
SUPPORT_CONTACT = {'DESCEND','CLOSE','VERIFY_GRIP','RECOVER','REFINE'}
TRACKING_PHASES = {'PREGRASP','DESCEND','LIFT'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def verify_bundle(study, protocol):
    for name, expected in protocol['frozen_sha256'].items():
        if sha(Path(study) / name) != expected: raise RuntimeError('Frozen file changed: ' + name)


def half_extents(model, data, geom):
    size = model.geom_size[geom]; rotation = data.geom_xmat[geom].reshape(3,3)
    kind = int(model.geom_type[geom]); axis = rotation[:,2]
    if kind == 6: return np.abs(rotation) @ size
    if kind == 2: return np.full(3, size[0])
    if kind == 5: return np.abs(axis)*size[1] + size[0]*np.sqrt(np.maximum(0,1-axis*axis))
    if kind == 3: return size[0] + np.abs(axis)*size[1]
    raise ValueError('Unsupported physical clutter geometry')


def contained(zone, position, half):
    x,y = zone['center']; bottom = position[2]-half[2]
    return bool(abs(position[0]-x)+half[0] <= zone['ix']+.005 and
                abs(position[1]-y)+half[1] <= zone['iy']+.005 and
                bottom >= zone['floor_z']-.005 and position[2] <= zone['rim_z']+.005 and
                bottom < zone['rim_z']-.005)


def evaluate(system, task):
    items = {}
    for name in system.cl.names:
        kind = system.cl.type_of[name]
        zone_name = task['CATEGORY_TO_ZONE'][task['CATEGORY_OF_TYPE'][kind]]
        zone = system.sorter.zone[zone_name]
        position = system.cl.pos(name)
        half = half_extents(system.model, system.data, system.cl.geom[name])
        items[name] = dict(type=kind, destination=zone_name, position_m=position.tolist(),
                           half_extents_m=half.tolist(), contained=contained(zone,position,half))
    return items


def restricted_time(status, elapsed, horizon, all_contained):
    # Early exhaustion is unsuccessful, even if it takes less wall/simulation time.
    return min(float(elapsed), float(horizon)) if status == 'completed' and all_contained else float(horizon)


class ContactAudit:
    """Identical physical contact policy, independent of either controller version."""
    def __init__(self, system):
        self.s = system; model = system.model
        roots = {model.body('link_gripper_finger_left').id, model.body('link_gripper_finger_right').id}
        bodies = set()
        for body in range(model.nbody):
            parent = body
            while parent > 0:
                if parent in roots: bodies.add(body); break
                parent = int(model.body_parentid[parent])
        self.fingers = {g for g in range(model.ngeom) if int(model.geom_bodyid[g]) in bodies}
        self.physical = (model.geom_contype != 0) | (model.geom_conaffinity != 0)
        self.last_hit = -math.inf; self.last_target = None; self.episodes = 0; self.samples = 0

    def step(self, now):
        now=round(float(now),6)  # same canonical clock precision as the raw CSV
        s=self.s; c=s.ctrl; rb=s.rb; m=s.model; d=s.data
        if c.target is not None: self.last_target=c.target.name
        if c.state not in HANDLING and c.target is None: self.last_target=None
        target = c.target.name if c.target is not None else self.last_target if c.state=='RETRACT' else None
        target_geom = s.cl.geom.get(target) if c.state in HANDLING else None
        hit = False
        for i in range(d.ncon):
            contact=d.contact[i]; a,b=int(contact.geom1),int(contact.geom2)
            if rb.geom_robot[a] == rb.geom_robot[b]: continue
            robot,other=(a,b) if rb.geom_robot[a] else (b,a)
            if rb.geom_floor[other]: continue
            if other==target_geom and robot in self.fingers: continue
            support = m.body(int(m.geom_bodyid[other])).name
            if c.state in SUPPORT_CONTACT and robot in self.fingers and support in getattr(c,'support',()):
                continue
            hit=True; break
        if hit:
            if now-self.last_hit > 1.0:
                self.episodes += 1; s.tele.collision(); c.obj_collisions += 1
                c.log('COMMON AUDIT: unexpected robot contact')
            self.last_hit=now; self.samples+=1
        c.collision_active=hit
        return hit
