import type { LegendPart } from '../lib/browse'
import styles from './Legend.module.css'

/** What the filters leave, in a sentence, with the values chosen in bold. */
export function Legend({ parts }: { parts: LegendPart[] }) {
  return (
    <p className={styles.legend}>
      {parts.map((part, index) =>
        typeof part === 'string' ? part : <strong key={index}>{part.strong}</strong>,
      )}
    </p>
  )
}
