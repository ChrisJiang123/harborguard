import type { StaticBuoy } from './mapGeometry'

// Proposed demonstration deployment, NOT installed Port of Los Angeles devices.
// Checked against H12617 water samples and offset from the demo vessel corridor.
// Nominal range is a display assumption, not a measured acoustic mask.
export const PROPOSED_SONARS = [
  { id: 'B1', lat: 33.7145, lon: -118.2705, role: 'Southern approach watch' },
  { id: 'B2', lat: 33.7163, lon: -118.2720, role: 'Western approach flank' },
  { id: 'B3', lat: 33.7182, lon: -118.2656, role: 'Outer bend east flank' },
  { id: 'B4', lat: 33.7200, lon: -118.2672, role: 'Outer bend west flank' },
  { id: 'B5', lat: 33.7212, lon: -118.2656, role: 'Waterside approach watch' },
  { id: 'B6', lat: 33.7240, lon: -118.2643, role: 'Inner corridor west flank' },
  { id: 'B7', lat: 33.7258, lon: -118.2605, role: 'Inner corridor east flank' },
  { id: 'B8', lat: 33.7276, lon: -118.2626, role: 'Northern corridor flank' },
  { id: 'B9', lat: 33.7305, lon: -118.2576, role: 'Inner bend approach watch' },
  { id: 'B10', lat: 33.7320, lon: -118.2575, role: 'Terminal-side water approach' },
].map(point => ({ ...point, range_m: 600, head_depth_m: 3 }))

/** Annotate only this exact proposal. Never relocate incoming backend/replay data. */
export function proposedSonar(buoy: StaticBuoy) {
  return PROPOSED_SONARS.find(point => point.id === buoy.id && Math.abs(point.lat-buoy.lat) < 1e-7 && Math.abs(point.lon-buoy.lon) < 1e-7)
}
