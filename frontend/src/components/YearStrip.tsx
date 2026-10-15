import styles from './YearStrip.module.css'

interface YearStripProps {
  decade: number
  /** The years of the decade with movies; all ten until the API answers. */
  years?: number[]
  chosen?: number
  /** A year, or undefined for the whole decade. */
  onChoose: (year: number | undefined) => void
}

/** With a single decade chosen, its years below the bar, as in Letterboxd: one of them narrows the list. */
export function YearStrip({ decade, years, chosen, onChoose }: YearStripProps) {
  const shown = years ?? Array.from({ length: 10 }, (_, index) => decade + index)
  return (
    <div className={styles.strip} role="group" aria-label={`Años de los ${decade}s`}>
      <button type="button" aria-pressed={chosen === undefined} onClick={() => onChoose(undefined)}>
        {decade}s
      </button>
      {shown.map((year) => (
        <button
          key={year}
          type="button"
          aria-pressed={year === chosen}
          // The chosen year again goes back to the whole decade, like the menus.
          onClick={() => onChoose(year === chosen ? undefined : year)}
        >
          {year}
        </button>
      ))}
    </div>
  )
}
