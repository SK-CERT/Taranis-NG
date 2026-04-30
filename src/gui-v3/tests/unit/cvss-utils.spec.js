import { describe, it, expect, vi } from 'vitest'
import fixtures from '../fixtures/data.json'
import {
  VERSION_CLASSES,
  createInstance,
  stripParentheses,
  detectVersion,
  getSeverityRating,
  calculateScoreItems,
  buildScoreItems
} from '@/components/common/cvss-utils'

// Minimal i18n helpers used by score-building functions
const t = (key) => key
const te = () => true

// ──────────────────────────────────────────────
// VERSION_CLASSES
// ──────────────────────────────────────────────
describe('VERSION_CLASSES', () => {
  it('should map all four supported versions', () => {
    expect(Object.keys(VERSION_CLASSES)).toEqual(['2.0', '3.0', '3.1', '4.0'])
  })

  it.each(['2.0', '3.0', '3.1', '4.0'])('class for %s should be a constructor', (v) => {
    expect(typeof VERSION_CLASSES[v]).toBe('function')
  })
})

// ──────────────────────────────────────────────
// createInstance
// ──────────────────────────────────────────────
describe('createInstance', () => {
  it.each(['2.0', '3.0', '3.1', '4.0'])(
    'should return an instance for version %s without a vector',
    (version) => {
      const inst = createInstance(version)
      expect(inst).toBeDefined()
      expect(typeof inst.calculateScores).toBe('function')
    }
  )

  it('should create a CVSS 3.1 instance from a vector string', () => {
    const inst = createInstance('3.1', fixtures.cvss.vectors.v31_base)
    const scores = inst.calculateScores()
    expect(scores.base).toBe(fixtures.cvss.scores.v31_base)
  })

  it('should create a CVSS 2.0 instance from a vector string', () => {
    const inst = createInstance('2.0', fixtures.cvss.vectors.v2_base)
    const scores = inst.calculateScores()
    expect(scores.base).toBe(fixtures.cvss.scores.v2_base)
  })

  it('should create a CVSS 3.0 instance from a vector string', () => {
    const inst = createInstance('3.0', fixtures.cvss.vectors.v30_base)
    const scores = inst.calculateScores()
    expect(scores.base).toBe(fixtures.cvss.scores.v30_base)
  })

  it('should create a CVSS 4.0 instance from a vector string', () => {
    const inst = createInstance('4.0', fixtures.cvss.vectors.v40_base)
    const scores = inst.calculateScores()
    expect(scores.base).toBeGreaterThan(0)
  })

  it('should throw for an invalid vector', () => {
    expect(() => createInstance('3.1', 'CVSS:3.1/INVALID')).toThrow()
  })
})

// ──────────────────────────────────────────────
// stripParentheses
// ──────────────────────────────────────────────
describe('stripParentheses', () => {
  it('should remove surrounding parentheses', () => {
    expect(stripParentheses('(AV:N/AC:L)')).toBe('AV:N/AC:L')
  })

  it('should return the string unchanged when no parentheses', () => {
    expect(stripParentheses('AV:N/AC:L')).toBe('AV:N/AC:L')
  })

  it('should strip only leading (', () => {
    expect(stripParentheses('(AV:N/AC:L')).toBe('AV:N/AC:L')
  })

  it('should strip only trailing )', () => {
    expect(stripParentheses('AV:N/AC:L)')).toBe('AV:N/AC:L')
  })

  it('should return null/undefined as-is', () => {
    expect(stripParentheses(null)).toBe(null)
    expect(stripParentheses(undefined)).toBe(undefined)
  })

  it('should return empty string as-is', () => {
    expect(stripParentheses('')).toBe('')
  })
})

// ──────────────────────────────────────────────
// detectVersion
// ──────────────────────────────────────────────
describe('detectVersion', () => {
  it('should detect CVSS 4.0', () => {
    expect(detectVersion(fixtures.cvss.vectors.v40_base)).toBe('4.0')
  })

  it('should detect CVSS 3.1', () => {
    expect(detectVersion(fixtures.cvss.vectors.v31_base)).toBe('3.1')
  })

  it('should detect CVSS 3.0', () => {
    expect(detectVersion(fixtures.cvss.vectors.v30_base)).toBe('3.0')
  })

  it('should detect CVSS 2.0 (no prefix — starts with AV:)', () => {
    expect(detectVersion(fixtures.cvss.vectors.v2_base)).toBe('2.0')
  })

  it('should detect version when wrapped in parentheses', () => {
    expect(detectVersion(`(${fixtures.cvss.vectors.v31_base})`)).toBe('3.1')
    expect(detectVersion(`(${fixtures.cvss.vectors.v2_base})`)).toBe('2.0')
  })

  it('should return null for null/undefined/empty', () => {
    expect(detectVersion(null)).toBe(null)
    expect(detectVersion(undefined)).toBe(null)
    expect(detectVersion('')).toBe(null)
  })

  it('should return null for unrecognised strings', () => {
    expect(detectVersion('not a vector')).toBe(null)
    expect(detectVersion('7.5')).toBe(null)
  })
})

// ──────────────────────────────────────────────
// getSeverityRating
// ──────────────────────────────────────────────
describe('getSeverityRating', () => {
  it.each([
    [0, 'none', 'None'],
    [0.0, 'none', 'None'],
    [0.1, 'low', 'Low'],
    [3.9, 'low', 'Low'],
    [4.0, 'medium', 'Medium'],
    [6.9, 'medium', 'Medium'],
    [7.0, 'high', 'High'],
    [8.9, 'high', 'High'],
    [9.0, 'critical', 'Critical'],
    [10.0, 'critical', 'Critical']
  ])('score %f → %s (%s)', (score, expectedName, expectedLabel) => {
    const result = getSeverityRating(score)
    expect(result.name).toBe(expectedName)
    expect(result.label).toBe(expectedLabel)
  })

  it('should return "none" for null, undefined, and NaN', () => {
    expect(getSeverityRating(null).name).toBe('none')
    expect(getSeverityRating(undefined).name).toBe('none')
    expect(getSeverityRating(NaN).name).toBe('none')
  })
})

// ──────────────────────────────────────────────
// calculateScoreItems — end-to-end from vector string
// ──────────────────────────────────────────────
describe('calculateScoreItems', () => {
  it('should return null for empty/null input', () => {
    expect(calculateScoreItems(null, t, te)).toBe(null)
    expect(calculateScoreItems('', t, te)).toBe(null)
    expect(calculateScoreItems(undefined, t, te)).toBe(null)
  })

  it('should return null for unrecognised vector', () => {
    expect(calculateScoreItems('not-a-vector', t, te)).toBe(null)
  })

  it('should return null for an invalid CVSS vector', () => {
    expect(calculateScoreItems('CVSS:3.1/INVALID', t, te)).toBe(null)
  })

  // CVSS 3.1 — base only vector
  describe('CVSS 3.1', () => {
    it('should produce base + temporal (N/A) + environmental (N/A) items', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v31_base, t, te)
      expect(items).toHaveLength(3)
      expect(items[0].name).toBe('base')
      expect(Number(items[0].score)).toBe(10.0)
      expect(items[1].name).toBe('temporal')
      expect(items[1].score).toBe('N/A')
      expect(items[2].name).toBe('environmental')
      expect(items[2].score).toBe('N/A')
    })

    it('should produce defined temporal score when temporal metrics present', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v31_temporal, t, te)
      expect(items).toHaveLength(3)
      expect(items[1].name).toBe('temporal')
      expect(items[1].score).not.toBe('N/A')
    })

    it('should work with medium-severity vectors', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v31_medium, t, te)
      expect(items).toHaveLength(3)
      const baseScore = Number(items[0].score)
      expect(baseScore).toBe(fixtures.cvss.scores.v31_medium_base)
      expect(items[0].severityClass).toBe('severity-low')
    })
  })

  // CVSS 2.0
  describe('CVSS 2.0', () => {
    it('should produce base + temporal (N/A) + environmental (N/A) items', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v2_base, t, te)
      expect(items).toHaveLength(3)
      expect(items[0].name).toBe('base')
      expect(Number(items[0].score)).toBe(10.0)
      expect(items[1].score).toBe('N/A')
      expect(items[2].score).toBe('N/A')
    })

    it('should handle parenthesised CVSS 2.0 vectors', () => {
      const wrapped = `(${fixtures.cvss.vectors.v2_base})`
      const items = calculateScoreItems(wrapped, t, te)
      expect(items).toHaveLength(3)
      expect(Number(items[0].score)).toBe(10.0)
    })

    it('should produce temporal and environmental scores from full vector', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v2_full, t, te)
      expect(items).toHaveLength(3)
      expect(items[1].score).not.toBe('N/A')
      expect(items[2].score).not.toBe('N/A')
    })
  })

  // CVSS 4.0
  describe('CVSS 4.0', () => {
    it('should produce base + threat (N/A) + environmental (N/A) items', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v40_base, t, te)
      expect(items).toHaveLength(3)
      expect(items[0].name).toBe('base')
      expect(items[1].name).toBe('threat')
      expect(items[1].score).toBe('N/A')
      expect(items[2].name).toBe('environmental')
      expect(items[2].score).toBe('N/A')
    })

    it('should produce a defined threat score when E:A is present', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v40_with_threat, t, te)
      expect(items).toHaveLength(3)
      expect(items[1].name).toBe('threat')
      expect(items[1].score).not.toBe('N/A')
    })

    it('should handle low-severity 4.0 vectors', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v40_low, t, te)
      expect(items).toHaveLength(3)
      const baseScore = Number(items[0].score)
      expect(baseScore).toBeLessThan(4.0)
    })
  })

  // CVSS 3.0
  describe('CVSS 3.0', () => {
    it('should produce three items for base-only vector', () => {
      const items = calculateScoreItems(fixtures.cvss.vectors.v30_base, t, te)
      expect(items).toHaveLength(3)
      expect(Number(items[0].score)).toBe(10.0)
    })
  })
})

// ──────────────────────────────────────────────
// buildScoreItems — from pre-calculated scores
// ──────────────────────────────────────────────
describe('buildScoreItems', () => {
  it('should return empty array for null scores', () => {
    expect(buildScoreItems(null, '3.1', t, te)).toEqual([])
  })

  it('should build items for CVSS 3.1 scores with all defined', () => {
    const scores = { base: 9.8, temporal: 9.1, environmental: 8.5 }
    const items = buildScoreItems(scores, '3.1', t, te)
    expect(items).toHaveLength(3)
    expect(items[0]).toMatchObject({ name: 'base', score: '9.8' })
    expect(items[1]).toMatchObject({ name: 'temporal', score: '9.1' })
    expect(items[2]).toMatchObject({ name: 'environmental', score: '8.5' })
  })

  it('should produce N/A items for undefined temporal/environmental', () => {
    const scores = { base: 7.5 }
    const items = buildScoreItems(scores, '3.1', t, te)
    expect(items).toHaveLength(3)
    expect(items[1]).toMatchObject({ name: 'temporal', score: 'N/A', severityClass: 'severity-na' })
    expect(items[2]).toMatchObject({ name: 'environmental', score: 'N/A', severityClass: 'severity-na' })
  })

  it('should build items for CVSS 4.0 scores', () => {
    const scores = { base: 9.0, threat: 8.5, environmental: 7.0 }
    const items = buildScoreItems(scores, '4.0', t, te)
    expect(items).toHaveLength(3)
    expect(items[0]).toMatchObject({ name: 'base', score: '9.0' })
    expect(items[1]).toMatchObject({ name: 'threat', score: '8.5' })
    expect(items[2]).toMatchObject({ name: 'environmental', score: '7.0' })
  })

  it('should produce N/A for undefined 4.0 threat/environmental', () => {
    const scores = { base: 5.0 }
    const items = buildScoreItems(scores, '4.0', t, te)
    expect(items).toHaveLength(3)
    expect(items[1]).toMatchObject({ name: 'threat', score: 'N/A' })
    expect(items[2]).toMatchObject({ name: 'environmental', score: 'N/A' })
  })

  it('should use "overall" as fallback when "base" is missing', () => {
    const scores = { overall: 6.5 }
    const items = buildScoreItems(scores, '2.0', t, te)
    expect(items[0]).toMatchObject({ name: 'base', score: '6.5' })
  })

  it('should set correct severityClass for each score', () => {
    const scores = { base: 0, temporal: 3.5, environmental: 7.2 }
    const items = buildScoreItems(scores, '3.1', t, te)
    expect(items[0].severityClass).toBe('severity-none')
    expect(items[1].severityClass).toBe('severity-low')
    expect(items[2].severityClass).toBe('severity-high')
  })

  it('should include severityLabel from i18n', () => {
    const scores = { base: 9.5 }
    const items = buildScoreItems(scores, '3.1', t, te)
    // t returns the key itself, te returns true, so severityLabel = t('cvss_calculator.critical')
    expect(items[0].severityLabel).toBe('cvss_calculator.critical')
  })
})
