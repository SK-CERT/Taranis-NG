#!/usr/bin/env node

/**
 * Generate git-info.json with build and git metadata.
 * This script is run before building (prebuild hook).
 * Matches the approach used by the Vue 2 GUI (src/gui/git-info.js).
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')

function safeGit(cmd, fallback = '') {
  try {
    return execSync(cmd, { encoding: 'utf8' }).trim()
  } catch {
    return fallback
  }
}

function toUTCISOString(dateString) {
  const d = new Date(dateString)
  return d.toISOString()
}

// Read version from VERSION.md
const possibleVersionPaths = [
  path.join(__dirname, '../../../VERSION.md'),
  path.join(__dirname, '../../VERSION.md'),
  '/app/VERSION.md'
]

let version = '26.02.1'
for (const p of possibleVersionPaths) {
  if (fs.existsSync(p)) {
    try {
      version = fs.readFileSync(p, 'utf-8').trim()
    } catch {
      // keep default
    }
    break
  }
}

const meta = {
  version,
  commit: safeGit('git rev-parse --short HEAD'),
  commitDate: toUTCISOString(safeGit('git log -1 --format=%cI HEAD')),
  branchName: safeGit('git rev-parse --abbrev-ref HEAD'),
  buildDate: new Date().toISOString()
}

const metaPath = path.resolve(__dirname, '..', 'git-info.json')
fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2))
console.log('Wrote git info to git-info.json:', meta)
