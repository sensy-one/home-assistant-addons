# Changelog

## 2025-10-09 — v1.0.0
- Initial release of the Sensy-One Zone Editor add-on

## 2025-10-13 — v1.1.0
- Switched from HTTP communication to HA API integration
- Added automatic device discovery
- Added drag-and-drop zone editing

## 2025-10-14 — v1.1.1
- Added responsive, viewport-based UI scaling

## 2025-11-12 — v1.1.2
- Switch from basic grid-count heatmap to tuned KDE (Kernel Density Estimation) — replaces blocky cell counting with a smooth continuous density field for more realistic, noise-reduced heatmaps.

## 2025-11-19 — v1.2.2
- Added 3D viewer for zones, live 3D target, and KDE map

## 2025-11-24 — v1.2.3
- Fixed UI reload loop when device_entities returns 400 error

## 2025-11-24 — v1.2.4
- Improved zone editing by allowing users to insert new points directly on existing edges and remove points using right-click.

## 2025-11-25 — v1.2.5
- Fixed Home Assistant template crash caused by non-serializable datetime attributes by enforcing JSON conversion.
- Added unified 2D / 3D toggle for both Live and Heatmap modes.
- Preserved selected view dimension when switching between Live and Heatmap.
- Enabled live target visualization in Heatmap 2D mode.