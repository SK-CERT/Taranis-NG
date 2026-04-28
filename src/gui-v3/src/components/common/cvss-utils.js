import { Cvss2, Cvss3P0, Cvss3P1, Cvss4P0 } from 'ae-cvss-calculator'

export const VERSION_CLASSES = {
  '2.0': Cvss2,
  '3.0': Cvss3P0,
  '3.1': Cvss3P1,
  '4.0': Cvss4P0
}

export function createInstance(version, vector) {
  const CvssClass = VERSION_CLASSES[version]
  if (vector) {
    return new CvssClass(vector)
  }
  return new CvssClass()
}

export function stripParentheses(vector) {
  if (!vector) return vector
  return vector.replace(/^\(/, '').replace(/\)$/, '')
}

export function detectVersion(vector) {
  if (!vector) return null
  const v = stripParentheses(vector)
  if (v.startsWith('CVSS:4.0')) return '4.0'
  if (v.startsWith('CVSS:3.1')) return '3.1'
  if (v.startsWith('CVSS:3.0')) return '3.0'
  if (v.match(/^AV:[NAL]/)) return '2.0'
  return null
}

export function getSeverityRating(score) {
  if (score === undefined || score === null || isNaN(score))
    return { name: 'none', label: 'None' }
  if (score === 0) return { name: 'none', label: 'None' }
  if (score <= 3.9) return { name: 'low', label: 'Low' }
  if (score <= 6.9) return { name: 'medium', label: 'Medium' }
  if (score <= 8.9) return { name: 'high', label: 'High' }
  return { name: 'critical', label: 'Critical' }
}

/**
 * Build score display items for a given CVSS vector string.
 * @param {string} value - The CVSS vector string (with or without parentheses)
 * @param {Function} t - i18n translate function
 * @param {Function} te - i18n key-exists function
 * @returns {Array|null} Array of score items or null if invalid
 */
export function calculateScoreItems(value, t, te) {
  if (!value) return null
  const version = detectVersion(value)
  if (!version) return null

  const cleaned = stripParentheses(value)
  const CvssClass = VERSION_CLASSES[version]
  try {
    const instance = new CvssClass(cleaned)
    return buildScoreItems(instance.calculateScores(), version, t, te)
  } catch {
    return null
  }
}

/**
 * Build score display items from pre-calculated scores and version.
 * Used by the calculator which already has a live instance.
 * @param {Object} scores - Result of calculateScores()
 * @param {string} version - CVSS version string
 * @param {Function} t - i18n translate function
 * @param {Function} te - i18n key-exists function
 * @returns {Array} Array of score items
 */
export function buildScoreItems(scores, version, t, te) {
  if (!scores) return []

  const items = []
  const isV4 = version === '4.0'

  // Base score - always present
  const baseScore = scores.base !== undefined ? scores.base : scores.overall
  items.push(makeScoreItem('base', t('cvss_calculator.base_score'), baseScore, t, te))

  if (isV4) {
    // CVSS 4.0: Threat, Environmental (no Supplemental score)
    if (scores.threat !== undefined) {
      items.push(
        makeScoreItem('threat', t('cvss_calculator.threat_score'), scores.threat, t, te)
      )
    } else {
      items.push(makeNAScoreItem('threat', t('cvss_calculator.threat_score')))
    }

    if (scores.environmental !== undefined) {
      items.push(
        makeScoreItem(
          'environmental',
          t('cvss_calculator.environmental_score'),
          scores.environmental,
          t,
          te
        )
      )
    } else {
      items.push(
        makeNAScoreItem('environmental', t('cvss_calculator.environmental_score'))
      )
    }
  } else {
    // CVSS 2.0/3.x: Temporal, Environmental
    if (scores.temporal !== undefined) {
      items.push(
        makeScoreItem(
          'temporal',
          t('cvss_calculator.temporal_score'),
          scores.temporal,
          t,
          te
        )
      )
    } else {
      items.push(makeNAScoreItem('temporal', t('cvss_calculator.temporal_score')))
    }

    if (scores.environmental !== undefined) {
      items.push(
        makeScoreItem(
          'environmental',
          t('cvss_calculator.environmental_score'),
          scores.environmental,
          t,
          te
        )
      )
    } else {
      items.push(
        makeNAScoreItem('environmental', t('cvss_calculator.environmental_score'))
      )
    }
  }

  return items
}

function makeScoreItem(name, label, score, t, te) {
  const scoreNum = Number(score).toFixed(1)
  const severity = getSeverityRating(Number(scoreNum))
  return {
    name,
    label,
    score: scoreNum,
    severityClass: `severity-${severity.name}`,
    severityLabel: te(`cvss_calculator.${severity.name}`)
      ? t(`cvss_calculator.${severity.name}`)
      : severity.label
  }
}

function makeNAScoreItem(name, label) {
  return {
    name,
    label,
    score: 'N/A',
    severityClass: 'severity-na',
    severityLabel: ''
  }
}
