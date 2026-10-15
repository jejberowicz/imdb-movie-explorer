/**
 * The map, projected once when the page loads: the shapes never change, only their colors (ADR 0009).
 * Data: Natural Earth, public domain (scripts/build_world_map.py).
 */

import { geoNaturalEarth1, geoPath } from 'd3-geo'
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import points from './small-countries.json'
import world from './world-110m.json'

export const WIDTH = 960

// Antarctica has no movies and would take a fifth of the height.
const land: FeatureCollection<Polygon | MultiPolygon, { code: string; name: string }> = {
  type: 'FeatureCollection',
  features: world.features.filter((feature) => feature.properties.code !== 'AQ'),
}
const projection = geoNaturalEarth1().fitWidth(WIDTH, land)
const path = geoPath(projection)

export const HEIGHT = Math.ceil(path.bounds(land)[1][1])

export interface Shape {
  code: string
  d: string
}

export const SHAPES: Shape[] = land.features.map((feature) => ({ code: feature.properties.code, d: path(feature) ?? '' }))

export interface Dot {
  code: string
  x: number
  y: number
}

/** Countries too small for the shapes (Hong Kong, Singapore, Malta...) are drawn as dots. */
export const DOTS: Dot[] = points.flatMap((point) => {
  const position = projection(point.coordinates)
  return position ? [{ code: point.code, x: position[0], y: position[1] }] : []
})

/** Lower bounds of the color steps: the counts go from 1 to 34.325 (USA), so each step is 10 times the last. */
export const STEPS = [1, 10, 100, 1000, 10000]

/** The color step for a number of movies, or -1 for none. */
export function stepOf(movies: number): number {
  return STEPS.findLastIndex((minimum) => movies >= minimum)
}
