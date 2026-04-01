/**
 * @file Testing helpers for server E2E tests
 */

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

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
