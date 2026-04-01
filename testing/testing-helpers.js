/**
 * @file Testing helpers for server E2E tests
 */

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
    }
    throw new Error('server-local.js did not become ready in time.');
}

/**
 * Sends a POST request with a JSON body and returns status and parsed response.
 * @param {string} url - The request URL.
 * @param {Object} body - The request payload.
 * @returns {Promise<{status: number, ok: boolean, json: any}>}
 */
async function postJSON(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const json = await res.json().catch(() => ({}));
    return { status: res.status, ok: res.ok, json };
}
