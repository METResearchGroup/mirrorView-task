// testing/e2e.get-post-assignments.test.js
// Run with: node --test testing/e2e.get-post-assignments.test.js
//
// This is a single "simple E2E" test that:
// 1) boots server-local.js as a real process
// 2) resets test state
// 3) calls POST /get-post-assignments
// 4) verifies basic invariants for one participant

const test = require('node:test');
const { setupServer, stopServer } = require('./server-lifecycle.js');

test.before(setupServer);
test.after(stopServer);

