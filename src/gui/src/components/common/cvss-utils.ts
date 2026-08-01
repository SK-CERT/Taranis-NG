import { Cvss2, Cvss3P0, Cvss3P1, Cvss4P0 } from 'ae-cvss-calculator'

type CvssVersion = '2.0' | '3.0' | '3.1' | '4.0'

type CvssCalculatorInstance = {
    calculateScores: () => CvssScores
}

type CvssCalculatorCtor = new (vector?: string) => CvssCalculatorInstance

type SeverityName = 'none' | 'low' | 'medium' | 'high' | 'critical'

type Translate = (key: string) => string
type TranslateExists = (key: string) => boolean

export interface CvssScores {
    base?: number
    overall?: number
    temporal?: number
    threat?: number
    environmental?: number
    [key: string]: number | undefined
}

export const SEVERITY_COLORS = {
    none: '#53aa33',
    low: '#ffcb0d',
    medium: '#f9a009',
    high: '#df3d03',
    critical: '#cc0500',
    na: '#9e9e9e'
} as const

export interface ScoreItem {
    name: string
    label: string
    score: string
    color: string
    severityClass: string
    severityLabel: string
}

export const VERSION_CLASSES: Record<CvssVersion, CvssCalculatorCtor> = {
    '2.0': Cvss2 as unknown as CvssCalculatorCtor,
    '3.0': Cvss3P0 as unknown as CvssCalculatorCtor,
    '3.1': Cvss3P1 as unknown as CvssCalculatorCtor,
    '4.0': Cvss4P0 as unknown as CvssCalculatorCtor
}

export function createInstance(version: CvssVersion, vector?: string): CvssCalculatorInstance {
    const CvssClass = VERSION_CLASSES[version]
    if (vector) {
        return new CvssClass(vector)
    }
    return new CvssClass()
}

export function stripParentheses(vector: string | null | undefined): string | null | undefined {
    if (!vector) return vector
    return vector.replace(/^\(/, '').replace(/\)$/, '')
}

export function detectVersion(vector: string | null | undefined): CvssVersion | null {
    if (!vector) return null
    const v = stripParentheses(vector)
    if (!v) return null
    if (v.startsWith('CVSS:4.0')) return '4.0'
    if (v.startsWith('CVSS:3.1')) return '3.1'
    if (v.startsWith('CVSS:3.0')) return '3.0'
    if (v.match(/^AV:[NAL]/)) return '2.0'
    return null
}

export function getSeverityRating(score: number | null | undefined): { name: SeverityName; label: string } {
    if (score === undefined || score === null || Number.isNaN(score)) return { name: 'none', label: 'None' }
    if (score === 0) return { name: 'none', label: 'None' }
    if (score <= 3.9) return { name: 'low', label: 'Low' }
    if (score <= 6.9) return { name: 'medium', label: 'Medium' }
    if (score <= 8.9) return { name: 'high', label: 'High' }
    return { name: 'critical', label: 'Critical' }
}

/**
 * Build score display items for a given CVSS vector string.
 * @param value - The CVSS vector string (with or without parentheses)
 * @param t - i18n translate function
 * @param te - i18n key-exists function
 * @returns Array of score items or null if invalid
 */
export function calculateScoreItems(value: string | null | undefined, t: Translate, te: TranslateExists): ScoreItem[] | null {
    if (!value) return null
    const version = detectVersion(value)
    if (!version) return null

    const cleaned = stripParentheses(value)
    if (!cleaned) return null

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
 */
export function buildScoreItems(scores: CvssScores | null | undefined, version: CvssVersion, t: Translate, te: TranslateExists): ScoreItem[] {
    if (!scores) return []

    const items: ScoreItem[] = []
    const isV4 = version === '4.0'

    // Base score - always present
    const baseScore = scores.base !== undefined ? scores.base : scores.overall
    items.push(makeScoreItem('base', t('cvss_calculator.base_score'), baseScore, t, te))

    if (isV4) {
        // CVSS 4.0: Threat, Environmental (no Supplemental score)
        if (scores.threat !== undefined) {
            items.push(makeScoreItem('threat', t('cvss_calculator.threat_score'), scores.threat, t, te))
        } else {
            items.push(makeNAScoreItem('threat', t('cvss_calculator.threat_score')))
        }

        if (scores.environmental !== undefined) {
            items.push(makeScoreItem('environmental', t('cvss_calculator.environmental_score'), scores.environmental, t, te))
        } else {
            items.push(makeNAScoreItem('environmental', t('cvss_calculator.environmental_score')))
        }
    } else {
        // CVSS 2.0/3.x: Temporal, Environmental
        if (scores.temporal !== undefined) {
            items.push(makeScoreItem('temporal', t('cvss_calculator.temporal_score'), scores.temporal, t, te))
        } else {
            items.push(makeNAScoreItem('temporal', t('cvss_calculator.temporal_score')))
        }

        if (scores.environmental !== undefined) {
            items.push(makeScoreItem('environmental', t('cvss_calculator.environmental_score'), scores.environmental, t, te))
        } else {
            items.push(makeNAScoreItem('environmental', t('cvss_calculator.environmental_score')))
        }
    }

    return items
}

function makeScoreItem(name: string, label: string, score: number | undefined, t: Translate, te: TranslateExists): ScoreItem {
    const scoreNum = Number(score).toFixed(1)
    const severity = getSeverityRating(Number(scoreNum))
    return {
        name,
        label,
        score: scoreNum,
        color: SEVERITY_COLORS[severity.name as keyof typeof SEVERITY_COLORS] ?? SEVERITY_COLORS.na,
        severityClass: `severity-${severity.name}`,
        severityLabel: te(`cvss_calculator.${severity.name}`) ? t(`cvss_calculator.${severity.name}`) : severity.label
    }
}

function makeNAScoreItem(name: string, label: string): ScoreItem {
    return {
        name,
        label,
        score: 'N/A',
        color: SEVERITY_COLORS.na,
        severityClass: 'severity-na',
        severityLabel: ''
    }
}
