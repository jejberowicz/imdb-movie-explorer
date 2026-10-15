import styles from './YearStrip.module.css'

interface YearStripProps {
  decade: number
  /** The years of the decade with movies; all ten until the API answers. */
  years?: number[]
  /** The years chosen; none is the whole decade. */
  chosen: number[]
  /** A year to add or take out, or undefined for the whole decade. */
  onChoose: (year: number | undefined) => void
}

/** With a single decade chosen, its years below the bar, as in Letterboxd: each one chosen narrows the list. */
export function YearStrip({ decade, years, chosen, onChoose }: YearStripProps) {
  const shown = years ?? Array.from({ length: 10 }, (_, index) => decade + index)
  return (
    <div className={styles.strip} role="group" aria-label={`Años de los ${decade}s`}>
      <button type="button" aria-pressed={chosen.length === 0} onClick={() => onChoose(undefined)}>
        {decade}s
      </button>
      {shown.map((year) => (
        <button
          key={year}
          type="button"
          aria-pressed={chosen.includes(year)}
          // Like the menus that allow several: a chosen year again takes it out.
          onClick={() => onChoose(year)}
        >
          {year}
        </button>
      ))}
    </div>
  )
}
