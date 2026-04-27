#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function safeGit(cmd, fallback = '') {
  try {
    return execSync(cmd, { encoding: 'utf8' }).trim();
  } catch {
    return fallback;
  }
}

function toUTCISOString(dateString) {
  // Parse any date string and return UTC ISO string
  const d = new Date(dateString);
  return d.toISOString();
}

const meta = {
  commit: safeGit('git rev-parse --short HEAD'),
  commitDate: toUTCISOString(safeGit('git log -1 --format=%cI HEAD')),
  branchName: safeGit('git rev-parse --abbrev-ref HEAD'),
  buildDate: new Date().toISOString(),
};

const metaPath = path.resolve(__dirname, 'git-info.json');
fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2));
// eslint-disable-next-line no-console
console.log('Wrote git info to git-info.json:', meta);
