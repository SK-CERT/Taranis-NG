#!/usr/bin/env node
/**
 * Free port 4444 of any leftover `dev:remote` (or GUI dev task) before the
 * Vite webServer spawns a fresh Vite.
 *
 * WHY: the Playwright `webServer` for Vite uses `reuseExistingServer:false` —
 * Playwright must OWN Vite's lifecycle so the run exits promptly after the
 * last test (otherwise Vite-as-reused can't be terminated → hang). But
 * `reuseExistingServer:false` aborts the run with "http://localhost:4444 is
 * already used" when a leftover Vite from a prior aborted run is still bound.
 * This preflight closes that gap.
 *
 * WHY AT THIS POINT (not as a Playwright globalSetup): an earlier attempt used
 * `globalSetup`, which runs BEFORE the webServer spawns and races it — the
 * kill-then-return sequence sent SIGTERM and returned before the port was
 * actually free, then the webServer spawned into a still-held port. Doing the
 * preflight as `&& node scripts/free-port-4444.cjs && npm run dev:remote` in
 * the SAME shell command kills any leftover Vite and IMMEDIATELY spawns the
 * fresh one — the OS runs them sequentially in one process tree, so there is
 * no race window between kill and spawn. The script also waits for the port
 * to actually be free before exiting (polls `net.createServer().listen`),
 * which closes the async-SIGTERM-release gap.
 *
 * Runs in plain Node (no ESM, no transpile) so it can be invoked from the
 * shell `command` in playwright.config.js without node_modules resolution.
 */
const net = require('node:net')
const { execSync } = require('node:child_process')

const PORT = 4444
const POLL_MS = 100
const MAX_WAIT_MS = 10_000

/** PIDs listening on PORT (TCP LISTEN). Empty array if lsof missing or none. */
function pidsOnPort(port) {
    try {
        const out = execSync(`lsof -t -iTCP:${port} -sTCP:LISTEN`, {
            encoding: 'utf8',
            stdio: ['ignore', 'pipe', 'ignore'],
        })
        return out
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean)
            .map(Number)
            .filter((n) => Number.isFinite(n) && n > 0)
    } catch {
        return []
    }
}

/** True if PORT can be bound right now (i.e. nothing is listening on it). */
function isPortFree(port) {
    return new Promise((resolve) => {
        const srv = net.createServer()
        srv.once('error', () => resolve(false))
        srv.once('listening', () => {
            srv.close(() => resolve(true))
        })
        srv.listen(port)
    })
}

async function main() {
    const pids = pidsOnPort(PORT)
    if (!pids.length) {
        // Nothing to free — still confirm the port is bindable before yielding,
        // so a TIME_WAIT socket from a recently-killed process doesn't trip Vite.
        // (Cheap: one quick listen check.)
        if (await isPortFree(PORT)) return
        // If not free but no PID was reported by lsof (race with shutdown),
        // fall through to the wait loop below.
    } else {
        // Send SIGTERM (graceful). Vite has a few hundred ms of teardown to do.
        for (const pid of pids) {
            try {
                process.kill(pid, 'SIGTERM')
            } catch {
                // Already gone — best-effort.
            }
        }
        console.log(`[free-port-4444] sent SIGTERM to PID(s): ${pids.join(', ')}`)
    }

    // Wait for the port to actually be bindable. SIGTERM is async; the process
    // doesn't release the port instantly. Returning before it's free races the
    // subsequent `npm run dev:remote` (Vite's --strictPort exits if still held).
    const deadline = Date.now() + MAX_WAIT_MS
    let escalated = false
    while (Date.now() < deadline) {
        if (await isPortFree(PORT)) {
            console.log('[free-port-4444] port is now free')
            return
        }
        // After 3s with no progress, escalate to SIGKILL on any survivors.
        if (!escalated && Date.now() > deadline - MAX_WAIT_MS + 3000) {
            const stragglers = pidsOnPort(PORT)
            if (stragglers.length) {
                console.log(`[free-port-4444] escalating to SIGKILL: ${stragglers.join(', ')}`)
                for (const pid of stragglers) {
                    try {
                        process.kill(pid, 'SIGKILL')
                    } catch {
                        // best-effort
                    }
                }
                escalated = true
            }
        }
        await new Promise((r) => setTimeout(r, POLL_MS))
    }
    // If still not free after MAX_WAIT_MS, exit non-zero — better to make the
    // failure loud than to spawn Vite into a stuck port and have the webServer
    // time out 120s later with a confusing message.
    console.error(`[free-port-4444] FAILED to free port ${PORT} within ${MAX_WAIT_MS}ms`)
    process.exit(1)
}

main().catch(() => process.exit(1))
