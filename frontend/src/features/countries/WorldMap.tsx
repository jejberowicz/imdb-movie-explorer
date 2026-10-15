import { type MouseEvent, useRef, useState } from 'react'
import { countryLabel, type Region } from '../../lib/countries'
import { countMovies, formatNumber } from '../../lib/format'
import { DOTS, HEIGHT, SHAPES, STEPS, stepOf, WIDTH } from './geometry'
import styles from './WorldMap.module.css'

interface WorldMapProps {
  regions: Map<string, Region>
  onSelect: (region: Region) => void
}

interface Hover {
  region: Region
  x: number
  y: number
  flip: boolean
}

/**
 * Each country with a tone by its number of movies; the former ones add up on their successor (ADR 0009).
 * It is for the mouse: the list below the map has the same data and works with the keyboard and screen readers.
 */
export function WorldMap({ regions, onSelect }: WorldMapProps) {
  const box = useRef<HTMLElement>(null)
  const [hover, setHover] = useState<Hover | null>(null)

  const regionAt = (event: MouseEvent) => {
    const code = (event.target as Element).getAttribute('data-code')
    return code ? regions.get(code) : undefined
  }

  function onMove(event: MouseEvent) {
    const region = regionAt(event)
    const rect = box.current?.getBoundingClientRect()
    if (!region || !rect) {
      setHover(null)
      return
    }
    const x = event.clientX - rect.left
    setHover({ region, x, y: event.clientY - rect.top, flip: x > rect.width * 0.6 })
  }

  const highlighted = hover && SHAPES.find((shape) => shape.code === hover.region.code)
  const highlightedDot = hover && DOTS.find((dot) => dot.code === hover.region.code)

  return (
    <figure className={styles.map} ref={box}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Mapa del mundo con un tono por país según su cantidad de películas. La lista de abajo tiene los mismos datos."
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        onClick={(event) => {
          const region = regionAt(event)
          if (region) onSelect(region)
        }}
      >
        {SHAPES.map((shape, index) => {
          const region = regions.get(shape.code)
          return (
            <path
              key={index}
              d={shape.d}
              className={styles.shape}
              data-code={region ? shape.code : undefined}
              data-step={stepOf(region?.movies ?? 0)}
            />
          )
        })}
        {DOTS.map((dot) => {
          const region = regions.get(dot.code)
          return (
            region && (
              <circle
                key={dot.code}
                cx={dot.x}
                cy={dot.y}
                r={3.5}
                className={styles.dot}
                data-code={dot.code}
                data-step={stepOf(region.movies)}
              />
            )
          )
        })}
        {highlighted && <path d={highlighted.d} className={styles.highlight} />}
        {highlightedDot && <circle cx={highlightedDot.x} cy={highlightedDot.y} r={3.5} className={styles.highlight} />}
      </svg>

      {hover && (
        <div
          className={hover.flip ? `${styles.tooltip} ${styles.flip}` : styles.tooltip}
          style={{ left: hover.x, top: hover.y }}
          aria-hidden="true"
        >
          <strong>{hover.region.name}</strong>
          {hover.region.members.length === 1 && countryLabel(hover.region.members[0]) === hover.region.name ? (
            <span>{countMovies(hover.region.members[0].movies)}</span>
          ) : (
            hover.region.members.map((member) => (
              <span key={member.name}>
                {countryLabel(member)}: {countMovies(member.movies)}
              </span>
            ))
          )}
        </div>
      )}

      <figcaption className={styles.legend}>
        <span>Películas por país</span>
        <ol>
          <li>
            <span className={styles.swatch} data-step={-1} />
            Ninguna
          </li>
          {STEPS.map((minimum, index) => (
            <li key={minimum}>
              <span className={styles.swatch} data-step={index} />
              {index + 1 < STEPS.length
                ? `${formatNumber(minimum)}–${formatNumber(STEPS[index + 1] - 1)}`
                : `${formatNumber(minimum)} o más`}
            </li>
          ))}
        </ol>
      </figcaption>
    </figure>
  )
}
