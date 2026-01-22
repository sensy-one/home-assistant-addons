# Changelog

## 2026-01-22 — v1.4.9
* Added full ceiling (top-down) and wall-mounted FoV support in preparation for the E1 Pro Multi Sense launch.
* Extended live target tracking from 3 to 5 simultaneous targets to support E1 Pro capabilities.
* Refined Live Targets and Heatmap views for a calmer visual presentation by removing unnecessary grids and overlays.
* Fixed Heatmap legend + / − buttons so they behave as momentary controls instead of remaining visually pressed.
* Improved Floorplan editing UX:
  * Grid is now visible only while drawing walls, placing sensors, or drawing zones.
  * Sensor FoVs are shown only during active edit modes and hidden during normal viewing.
  * Overall floorplan view feels cleaner and more compact outside edit modes.
* Simplified zone behavior to allow fully free zone drawing without FoV or range constraints.
* Reduced visual clutter and removed legacy state leakage between sensors, ensuring consistent per-sensor behavior.
* Various internal optimizations and UI cleanups to improve stability, predictability, and responsiveness.

## 2026-01-20 — v1.3.9
- Fix canvas background rendering on Windows by explicitly filling the canvas instead of relying on CSS background

## 2025-12-26 — v1.3.8
- Remember last selected view, floorplan, and device between sessions

## 2025-12-14 — v1.3.7
- New 2D/3D floorplan editor for sensor placement and zone configuration

## 2025-12-03 — v1.2.7
- Mobile controls have been refined: all view and zoom buttons now fit cleanly within the layout and keep equal spacing.
- 3D view now starts from an improved default angle, giving a clearer forward-facing perspective right away.

## 2025-11-25 — v1.2.6
- Radar background is now immune to Windows transparency and high contrast settings.

## 2025-11-25 — v1.2.5
- Fixed Home Assistant template crash caused by non-serializable datetime attributes by enforcing JSON conversion.
- Added unified 2D / 3D toggle for both Live and Heatmap modes.
- Preserved selected view dimension when switching between Live and Heatmap.
- Enabled live target visualization in Heatmap 2D mode.

## 2025-11-24 — v1.2.4
- Improved zone editing by allowing users to insert new points directly on existing edges and remove points using right-click.

## 2025-11-24 — v1.2.3
- Fixed UI reload loop when device_entities returns 400 error

## 2025-11-19 — v1.2.2
- Added 3D viewer for zones, live 3D target, and KDE map

## 2025-11-12 — v1.1.2
- Switch from basic grid-count heatmap to tuned KDE (Kernel Density Estimation) — replaces blocky cell counting with a smooth continuous density field for more realistic, noise-reduced heatmaps.

## 2025-10-14 — v1.1.1
- Added responsive, viewport-based UI scaling

## 2025-10-13 — v1.1.0
- Switched from HTTP communication to HA API integration
- Added automatic device discovery
- Added drag-and-drop zone editing

## 2025-10-09 — v1.0.0
- Initial release of the Sensy-One Zone Editor add-on
