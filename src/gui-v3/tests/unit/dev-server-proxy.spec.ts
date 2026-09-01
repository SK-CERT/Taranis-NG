// @vitest-environment node
/**
 * The `npm run dev` contract.
 *
 * This runs the real `npm run dev` against a throwaway backend, so a change that
 * breaks local development fails here instead of on the next developer's machine.
 * It is a child process rather than an in-process `createServer()` because a Vite
 * dev server installs process-wide exit handlers (stdin end / SIGTERM -> close and
 * `process.exit()`); inside a vitest worker those fire at unpredictable moments and
 * kill the worker mid-run. A child process also means this covers the npm script
 * itself, which is what the developer actually types.
 *
 * The specific regression under guard: `changeOrigin: true` rewrites the outgoing
 * Host to the backend but leaves the browser's Origin (http://localhost:4444) alone.
 * Core's `_is_same_origin_request()` (src/core/api/auth.py) compares the two and
 * answered 403 to every POST /api/v1/auth/redeem, which the login page issues on
 * each mount - a failed request in the console and a spurious error banner on the
 * login screen. The proxy is the origin as far as the backend is concerned, so it
 * has to present Host and Origin consistently.
 */
import { spawn } from 'node:child_process'
import type { ChildProcess } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { createServer as createHttpServer } from 'node:http'
import type { IncomingHttpHeaders, Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { fileURLToPath } from 'node:url'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'

type RecordedRequest = { url: string; headers: IncomingHttpHeaders }

const root = fileURLToPath(new URL('../../', import.meta.url))
const STARTUP_TIMEOUT_MS = 60_000

const received: RecordedRequest[] = []

let backend: Server
let backendOrigin = ''
let dev: ChildProcess
let devOrigin = ''
let devOutput = ''

const listenOnEphemeralPort = (server: Server): Promise<number> =>
    new Promise((resolve, reject) => {
        server.once('error', reject)
        server.listen(0, '127.0.0.1', () => {
            resolve((server.address() as AddressInfo).port)
        })
    })

/**
 * Claim a free port by taking one and handing it straight back.
 *
 * VITE_PORT=0 does not mean "any port" to Vite - it falls back to the default 5173,
 * which is both a port other Vite projects use and one editors watch for and open in
 * a browser. A stray page load against this server would pollute the recorded
 * requests. The dev server is started with --strictPort, so if something claims the
 * port in between it fails loudly here instead of drifting onto another one.
 */
const reserveFreePort = async (): Promise<number> => {
    const placeholder = createHttpServer()
    const port = await listenOnEphemeralPort(placeholder)
    await new Promise<void>((resolve) => placeholder.close(() => resolve()))
    return port
}

/**
 * Wait until the dev server answers on the port it was given.
 *
 * Readiness is probed over HTTP rather than read off stdout. Vite prints its URL with
 * the port wrapped in ANSI colour codes whenever the runner asks for colour (an
 * editor's test runner does, a pipe does not), so parsing that line passes from a
 * terminal and times out inside the IDE. --strictPort means the port is either ours
 * or the process dies, so there is nothing to parse: an answer on it IS the server.
 * The output is still collected, to say what went wrong if it never comes up.
 */
const waitForDevServer = async (): Promise<void> => {
    const deadline = Date.now() + STARTUP_TIMEOUT_MS

    while (Date.now() < deadline) {
        if (dev.exitCode !== null) {
            throw new Error(`the dev server exited with ${dev.exitCode}:\n${devOutput}`)
        }
        try {
            const response = await fetch(`${devOrigin}/v2/`)
            await response.text()
            if (response.ok) {
                return
            }
        } catch {
            // not listening yet
        }
        await new Promise((resolve) => setTimeout(resolve, 50))
    }

    throw new Error(`the dev server did not answer on ${devOrigin} within ${STARTUP_TIMEOUT_MS} ms:\n${devOutput}`)
}

beforeAll(async () => {
    backend = createHttpServer((req, res) => {
        received.push({ url: req.url ?? '', headers: req.headers })
        res.writeHead(204)
        res.end()
    })
    backendOrigin = `http://127.0.0.1:${await listenOnEphemeralPort(backend)}`

    const devPort = await reserveFreePort()
    devOrigin = `http://localhost:${devPort}`

    dev = spawn('npm', ['run', 'dev', '--', '--strictPort'], {
        cwd: root,
        // VITE_PORT keeps the test off 4444, where a developer's own dev server lives,
        // and off 5173. The three backend variables are pinned at the stub so that
        // whatever sits in the developer's docker/.env - which vite.config.js loads
        // through `loadEnv(mode, dockerEnvDir, '')` - cannot change where these
        // requests end up.
        env: {
            ...process.env,
            VITE_PORT: String(devPort),
            VITE_DEV_BACKEND_ORIGIN: backendOrigin,
            VITE_APP_TARANIS_NG_CORE_API: `${backendOrigin}/api/v1`,
            VITE_APP_TARANIS_NG_CORE_SSE: `${backendOrigin}/sse`
        },
        stdio: ['ignore', 'pipe', 'pipe'],
        // Own process group: npm forks vite, and killing npm alone would orphan it.
        detached: true
    })
    dev.stdout?.setEncoding('utf8')
    dev.stderr?.setEncoding('utf8')
    dev.stdout?.on('data', (chunk: string) => (devOutput += chunk))
    dev.stderr?.on('data', (chunk: string) => (devOutput += chunk))

    await waitForDevServer()
}, STARTUP_TIMEOUT_MS + 10_000)

afterAll(async () => {
    if (dev?.pid && dev.exitCode === null) {
        const exited = new Promise<void>((resolve) => dev.once('exit', () => resolve()))
        process.kill(-dev.pid, 'SIGTERM')
        await exited
    }
    await new Promise<void>((resolve) => backend.close(() => resolve()))
})

/**
 * Send one request through the dev proxy and return what the backend saw of it.
 *
 * Each probe carries its own marker rather than trusting the last recorded request:
 * the dev server is a real one, and the browser page, the Vite client or a retry
 * could otherwise slip a request in between the call and the assertion.
 */
const probe = async (path: string, init?: RequestInit): Promise<{ request: RecordedRequest; response: Response }> => {
    const marker = `probe=${randomUUID()}`
    const response = await fetch(`${devOrigin}${path}${path.includes('?') ? '&' : '?'}${marker}`, init)
    const request = received.find((entry) => entry.url.includes(marker))
    if (!request) {
        throw new Error(`the dev server did not forward ${path} to the backend`)
    }
    return { request, response }
}

/** The path the backend was asked for, without the probe marker. */
const pathOf = (request: RecordedRequest): string => request.url.split('?')[0] ?? ''

describe('npm run dev', () => {
    it('serves the app shell under the /v2 base', async () => {
        const response = await fetch(`${devOrigin}/v2/`)

        expect(response.status).toBe(200)
        expect(await response.text()).toContain('<div id="app">')
    })

    it('forwards /api to the backend with the path intact', async () => {
        const { request, response } = await probe('/api/v1/auth/redeem', { method: 'POST' })

        expect(response.status).toBe(204)
        expect(pathOf(request)).toBe('/api/v1/auth/redeem')
    })

    it('sends an Origin that agrees with the rewritten Host', async () => {
        // What the browser sends from the dev server's own page.
        const { request } = await probe('/api/v1/auth/redeem', {
            method: 'POST',
            headers: { 'Origin': devOrigin, 'Sec-Fetch-Site': 'same-origin' }
        })

        expect(request.headers['host']).toBe(new URL(backendOrigin).host)
        expect(request.headers['origin']).toBe(backendOrigin)
    })

    it('does not invent an Origin the browser never sent', async () => {
        const { request } = await probe('/api/v1/auth/methods')

        expect(request.headers['origin']).toBeUndefined()
    })

    it('forwards /sse to the backend as well', async () => {
        const { request } = await probe('/sse/events')

        expect(pathOf(request)).toBe('/sse/events')
    })
})
