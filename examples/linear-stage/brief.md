# Linear stage: build, revise, inspect

## Initial request

Design a small screw-driven linear stage with 80 mm working travel. Include a base, two guide rods, a moving platform, a lead screw and nut holder, end supports, a motor mounting plate, and a coupling. The platform must expose four Ø5.5 through holes on a 36 × 32 mm pattern. Use a 31 × 31 mm motor mounting pattern. Export a named assembly and individual parts as STEP.

## Revision request

Increase working travel to 120 mm. Keep the moving platform's mounting pattern and the motor mounting interface unchanged. Update the required parts and placements. Rebuild the original 80 mm version with the final code and check both versions, including the two endpoints and intermediate travel positions.

## Modeling decisions recorded before execution

- X is the motion axis; Z is up. All dimensions are millimeters.
- Moving platform: 52 × 82 × 8 mm, with two separate guide housings and a nut holder beneath it.
- Two Ø8 guide rods at Y = ±28, Z = 30; screw nominal Ø8 at Y = 0, Z = 28.
- The screw axis and motor axis coincide at Z = 28. The two guide rods sit 2 mm higher.
- Support inner faces sit 6 mm beyond the moving platform at each travel endpoint.
- Base and shaft lengths derive from travel; moving parts retain their local geometry.
- Motor is a geometric envelope with a 31 mm mounting pattern, not a downloaded vendor part.
- Screw and threaded fasteners use nominal cylindrical envelopes. The nut and bearings use simplified bores; no thread contact, rolling elements, or motor internals are simulated.
- Interference tests use solid intersection volume with a 0.00001 mm³ tolerance, at nine carriage positions including both endpoints. They do not certify load capacity, tolerances, or continuous-motion safety.

## Execution provenance

This example is authored and executed by Codex in the repository-maintenance conversation, using local Python/build123d commands. It is not a run of MAC, AI-CAD, or text-to-cad. The run directory holds source snapshots, command output, checks, and revision comparisons from this execution.
