# Nova3D hospital integration — 18 October 2026

The supplied `Hospital messy room (1).zip` has been integrated into the active
`capstone/` build. The existing `START_CAPSTONE.cmd` launches the new appearance.
Use `--scene classic` to select the previous scene; no original source model was
overwritten by this integration.

## What was imported

The archive contains multiple intermediate builds. The final
`out/simulation/scene_spec.json` selects 310 named parts, and the structured visual
package supplies their matching OBJ meshes and procedural textures. Local import
uses this final selection rather than reintroducing older floating headwall
panels. Two ceiling-light parts attached to the omitted south wall are also
omitted locally. The resulting scene imports **308 parts / 98,854 triangles**,
plus a massless presentation plinth and stage.

The imported bed, cabinets, sofa, chair, coffee table, cart, sink, four sorting
receptacle exteriors, linen shelves, wall/window modules, curtains and vinyl floor
remain individually named. Nine procedural texture images are mapped to local
MuJoCo materials. The original robot, all 15 clutter bodies, physical furniture,
bin interiors, joints, actuators and 0.002-second physics step are retained.

The archive's standalone `environment.xml` is not the task model. It contains no
robot/controller and must not be substituted for the existing simulation. Neither
the supplied construction Python nor its bundled runner was executed. Local
conversion only reads geometry, metadata and texture images.

## Fitting and sensing

- Source OBJ coordinates are metres, Z-up and already in world space. Anchors
  are not translated a second time. GLB's axis conversion is not applied to OBJ.
- Sofa, chair and coffee table meshes are rotated about their existing anchors
  and resized to better match the original physical furniture. The cart, bedside
  table, bed and sink also receive recorded visual fit adjustments.
- The bed and table surface skins end 1 mm below existing support tops. The chair
  seat skin is corrected to 0.449 m below its 0.450 m physical top. The original
  pillow, blanket and sofa cushion remain visible, retaining their task supports.
- Imported bed side rails are raised visually to match the existing physical
  rails. The obsolete classic curtain-rail appearance is hidden.
- Converted meshes use geom group 5, `mass=0`, `contype=0`, `conaffinity=0`.
  All current navigation, perception and spawn ray callers use the existing
  group-0 mask, excluding groups 1–5. Navigation uses only contact-enabled geoms.
- Original contact geometry RGB is preserved. Hidden furniture uses alpha 0.001,
  rather than zero, to remain observable to ray sensors. Clutter colours and robot
  visuals remain unchanged.
- The robot's scratch collision model loads the same selected scene as the live
  model. Added world geoms shift numeric geom IDs; matching the selected scene is
  essential. Regression comparisons use physical identity rather than raw IDs.
- Presentation cameras face the open cutaway sides. Camera changes do not change
  any simulated state.

## Files and provenance

| Path within `capstone/` | Purpose |
| --- | --- |
| `models/hospital_nova3d.xml` | Integrated task model |
| `models/hospital_nova3d_visual.xml` | Imported visual include |
| `models/assets/nova3d/` | Fitted OBJ meshes and PNG textures |
| `models/nova3d_integration_manifest.json` | Mesh hashes, part list and fit policy |
| `external_assets/nova3d/source/` | Preserved selected export and editable source |
| `external_assets/nova3d/source_manifest.json` | Supplied archive hash and extracted-file hashes |
| `tools/integrate_nova3d.py` | Reproducible local conversion |
| `docs/nova3d_preview/` | Actual initial MuJoCo renderings |
| `docs/nova3d_integration_verification.json` | Paired integration check results |

Each new measurement manifest records the selected task model and the hash of
the visual asset manifest. Source files are preserved as the user's Nova3D export;
no third-party licensing or clinical fidelity is inferred from the generated
package. Retain the provider's applicable terms when distributing its assets.

## Verification and limits

`tests/test_foundation.py` checks the original dynamics, unfinished-run accounting,
500 Hz sample cadence and camera/placement invariants on the new default scene.
`tests/test_nova3d_integration.py` compares the compiled dynamics and contact
geometry, the initial 15-object distribution, two simulated RGB-D camera frames,
the navigation occupancy grid, and a seed-0 paired 60-second autonomous rollout.
It checks robot positions, velocities, controls, state transitions and object
events against the classic scene, plus the new run's 30,000 measurement rows.
The JSON verification report records actual results, including a pass flag.

This is a visual integration, not a controller reliability improvement. The
previous development run's incomplete clean, drop failures and collisions remain
relevant. The short paired check is not the required baseline/proposed study and
is not evidence of full-room completion or hospital labour savings. Final trial
experiments, business analysis and submission materials remain outstanding.

MuJoCo approximates the exported PBR materials and area lights. Wall fixtures and
soft furnishings are visual geometry excluded from sensors; original simplified
collision shapes remain authoritative. Small differences between decorative
shells and collision surfaces should be disclosed during the defence. Screenshot
rendering speed is not a measured native-viewer frame rate.
