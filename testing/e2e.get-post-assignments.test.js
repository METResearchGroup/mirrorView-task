// testing/e2e.get-post-assignments.test.js
// Run with: node --test testing/e2e.get-post-assignments.test.js
//
// This is a single "simple E2E" test that:
// 1) boots server-local.js as a real process
// 2) resets test state
// 3) calls POST /get-post-assignments
// 4) verifies basic invariants for one participant

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const path = require('node:path');

const BASE_URL = 'http://localhost:3000';

const SERVER_PATH = path.join(__dirname, '..', 'server-local.js');

let serverProc;

async function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
}

