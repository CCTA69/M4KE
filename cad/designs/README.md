# ECHO F1 authored prototype

This is a deliberately authored car build, separate from AI generation and from
the teammate's component library. Its source CAD, purchased reference geometry,
wiring and firmware are not evidence that Qwen completed a fresh design.

This repository distributes the generator, application and test **source**.
Generated `builds/`, native meshes, print projects, local test receipts and vendor
slicer resources are not committed. Historical import/slicing results below
describe the earlier local artifacts only; regenerate and recheck on your own
installation before treating a new build as usable. No test in source-only CI
asserts purchased-part fit or sends a printer job.

## Generate

From the M4KE repository root, in a dedicated Python 3.12 virtual environment:

```sh
python -m pip install cadquery==2.8.0 trimesh==5.1.1 scipy
python cad/designs/echo_f1.py
python cad/designs/echo_f1_package.py
python cad/designs/echo_f1_wiring.py
python cad/designs/echo_f1_package.py
```

On Windows the official Visual C++ runtime is required by the CAD native wheels.
The generator can also use a locally provisioned `.setup/runtime-dlls` directory.
Do not download DLLs from random third-party sites.

Outputs live in `builds/echo-f1-v1`. Open `instructions.html` for the Chinese
build handbook. Print **only** the files in `print/`, at millimetres and 100%
scale. `assembly-parts/` includes purchased reference parts which are **not**
substitutes for actual electronics, bearings, motors or rubber tyres.

## App and tests

```sh
npm run build
npm start
# Open /?build=echo-f1-v1 on the reported local server port.
python firmware/echo-f1/test_controller.py
node --test tests/authored-builds.test.mjs
```

`tests/echo-f1-browser.mjs` exercises the running app. It defaults to port 4176
and Microsoft Edge on Windows; set `ECHO_URL` / `ECHO_BROWSER` to override.
After browser checks, rerun the package builder to include the recorded checks.

The first package pass creates the logical netlist; the wiring pass generates
display routes around the closed assembly, then the final pass embeds and hashes
the report. The viewport only draws routes whose native geometry hashes,
placements, endpoints and radius still match. Missing/stale paths remain 2D-only.
Ports are virtual surface proxies, not verified PCB pins. The 0.65 mm display
radius is checked with 0.15 mm clearance against the simplified native solids;
real connectors, wire insulation, bending radii and wire-to-wire spacing still
need physical layout verification. Opening the shell only affects display.

## Boundaries

- Parametric CadQuery BReps are the source; no image-to-mesh output.
- Checks cover valid solids, watertight STL, winding, volume consistency,
  STEP round-trip and modeled pairwise intersections; selected fastener nut
  envelopes are checked too. They do not certify all fastener/tool clearance.
- Source checks do not establish physical assembly, FEA, calibrated
  sound-pressure measurement, temperature or road-test acceptance. Separate
  historical import/slicing coverage is recorded below.
- Motor bodies, switches and the battery holder require supplier dimension
  confirmation. Purchased parts are explicitly simplified reference geometry.
- Budget allocations are not verified live prices.
- The firmware starts disarmed in a low-speed commissioning profile. Quiet
  sampling windows reduce motor self-triggering but do not prove its absence.
- Inspect the fit coupon before printing full parts. Prototype for supervised
  adult use only; never treat it as a certified children's toy.

## Mainland solderless variant (CN v2)

Independent package; v1 remains intact. Uses Romeo mini DFR1063, a 3.3 V
DFR0034 intensity sensor, factory-wired 6 V N20/PH2.0 motor-wheel sets,
8 AA NiMH through a 5.5 V screw-terminal buck, and a 286 mm split PLA body.
Do not reuse v1 wiring, driver, firmware or its 12 V shopping candidate.
Supplier SKU/size confirmation is explicitly still required; this is not a
claim that every search result in a marketplace is compatible or in stock.

```sh
python cad/designs/echo_f1_cn.py
python cad/designs/echo_f1_cn_package.py
python cad/designs/echo_f1_wiring.py --build echo-f1-cn-v2
python tests/verify-wire-clearance.py --build echo-f1-cn-v2
python cad/designs/echo_f1_cn_package.py
python tests/verify-cn-build.py
python firmware/echo-f1-cn/test_controller.py
```

Open `/?build=echo-f1-cn-v2` on the running app. Output:
`builds/echo-f1-cn-v2/ECHO-F1-build-package.zip`. It includes STL, STEP,
14-wire diagram, BOM, 11-step assembly guide, ESP32-C3 firmware and source.
Purchased meshes are envelopes, not printable substitutes. Physical assembly,
calibrated dB and motor/temperature tests have not been completed. Native
import/slicing coverage for the new print projects is detailed below.

### CN v2 beginner print projects

Open `/?build=echo-f1-cn-v2&view=print`. Choose the actual printer (none is
preselected), download **one multi-plate 3MF**, then open it **as a project** in
Bambu Studio. Projects include 18 printed parts plus a separate first-plate fit
coupon. Red and black parts occupy different plates; manual spool changes
between plates suffice, with no AMS. Individual STL files remain a collapsed
advanced fallback. The guide covers slicing, assembly, wiring, firmware loading,
sound-threshold commissioning and a blank physical-test checklist.

For 0.4 mm / PLA / textured PEI, H2C has 4 plates; P1S, X1C and A1 have 6;
A1 mini has 8. These are editable, unsliced projects, not ready-to-send G-code.
Machine keep-outs and, for H2C, the two-nozzle reachable-area intersection are
respected. Check the actual printer, plate, filament and support preview before
printing. Never scale the whole car to compensate for fit or bed size.

To regenerate plates after changing native geometry, use an official Bambu
Studio resource directory containing `resources/profiles/BBL`:

```sh
python printing/authored_plates.py --slicer-root /path/to/BambuStudio
python cad/designs/echo_f1_cn_package.py
python tests/verify-print-plates.py
node tests/print-plates-browser.mjs
python cad/designs/echo_f1_cn_package.py
python tests/verify-cn-build.py
```

Plate generation resets native-validation status. Recheck changed files rather
than reusing old evidence. Optional native import checks for all five projects
and an H2C slicing run (never prints):

```sh
python tests/slice-print-plates.py --slicer /path/to/bambu-studio --slice h2c
python cad/designs/echo_f1_cn_package.py
```

The earlier local CN v2 projects passed native import in Bambu Studio 2.8.2.61.
All four H2C plates completed a local slicing run, with vendor `T` command
parsing warnings recorded in `checks/print-plates-native.json`. The H2C estimate
is 419.2 g / 17.2 hours, **not a measurement**. Other printer projects were
import-tested, not fully sliced. These historical results do not establish
physical print quality, purchased-part fit or road-test success. The generation
and validation commands in this guide do not send print jobs.

After a native recheck, independently inspect the deposited paths, including
arc extrema, support and brim widths (not vendor homing/purge motions):

```sh
python tests/verify-plate-toolpaths.py --run recheck-2026-10-09 --printer h2c
python cad/designs/echo_f1_cn_package.py
python tests/verify-cn-build.py
```

The recorded four-plate H2C recheck passed these deposited-path envelope and
layer-continuity checks; see `checks/print-toolpaths.json`. The three `T`
warnings also occur in the official H2C start/end template commands; those
templates were not modified to suppress the warnings. This does not verify
the firmware on a connected printer. Adhesion, support removal, physical fit
and strength still require actual printing and testing. Current generated files
must have their own checks; historical receipts are not copied into a clean build.
