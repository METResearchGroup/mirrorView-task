/**
 * @file Server lifecycle helpers for server E2E tests
 */

const path = require('node:path');
const { spawn } = require('node:child_process');
const { BASE_URL, SERVER_PATH } = require('./constants.js');
let serverProc = null;

/**
 * Waits for the local server to be ready by polling a debug endpoint.
 * Throws an error if the server does not respond within the timeout.
 * @param {number} [timeoutMs=15000] - Maximum wait time in milliseconds.
 * @throws {Error} If server isn't ready in the allotted time.
 * @returns {Promise<void>} Resolves when the server is ready.
 */
async function waitForServerReady(timeoutMs = 15000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        try {
            const res = await fetch(`${BASE_URL}/debug/assignments`);
            if (res.ok) return;
        } catch (_) {
            // server not up yet.
        }
        await sleep(200);
    }
    throw new Error('server-local.js did not become ready in time.');
}

async function startServer() {
    serverProc = spawn(process.execPath, [SERVER_PATH], {
        stdio: 'inherit',
        cwd: path.join(__dirname, '..'),
      });
}

async function setupServer() {
    await startServer();
    await waitForServerReady();
}

async function stopServer() {
    if (serverProc && !serverProc.killed) {
        serverProc.kill('SIGINT');
        serverProc = null;
    }
}

module.exports = {
    setupServer,
    stopServer,
}