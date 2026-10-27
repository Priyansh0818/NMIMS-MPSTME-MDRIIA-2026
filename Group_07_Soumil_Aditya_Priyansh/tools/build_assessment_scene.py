"""Extend the preserved 15-item scene with a rigid hospital-slipper proxy."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def build():
    tree = ET.parse(ROOT / 'models/hospital_nova3d.xml')
    world = tree.getroot().find('worldbody')
    body = ET.SubElement(world, 'body', name='clutter_slipper_1', pos='-0.5 -3.2 .1')
    ET.SubElement(body, 'freejoint', name='slipper_1_free')
    # One explicit box is the authoritative collision, inertia and sensing proxy.
    ET.SubElement(body, 'geom', name='slipper_1_geom', type='box',
                  size='.115 .042 .03', mass='.12', rgba='.52 .22 .65 .001',
                  friction='1.0 .01 .001')
    visual = dict(contype='0', conaffinity='0', mass='0', group='5')
    ET.SubElement(body, 'geom', name='slipper_sole_visual', type='ellipsoid',
                  size='.118 .044 .012', pos='0 0 -.018', rgba='.20 .12 .28 1', **visual)
    ET.SubElement(body, 'geom', name='slipper_upper_visual', type='ellipsoid',
                  size='.060 .042 .028', pos='.035 0 .002', rgba='.52 .22 .65 1', **visual)
    ET.SubElement(body, 'geom', name='slipper_footbed_visual', type='ellipsoid',
                  size='.075 .034 .004', pos='-.035 0 -.003', rgba='.75 .66 .80 1', **visual)
    ET.indent(tree.getroot(), space='  ')
    output = ROOT / 'models/hospital_assessment.xml'
    tree.write(output, encoding='unicode')
    print(output)


if __name__ == '__main__': build()
