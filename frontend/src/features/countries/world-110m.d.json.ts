// The type of world-110m.json, so TypeScript doesn't infer it from 170 KB of coordinates.
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'

declare const world: FeatureCollection<Polygon | MultiPolygon, { code: string; name: string }>
export default world
