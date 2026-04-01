// testing/e2e.lambda-post-assignments.test.js
// Run with: node --test testing/e2e.lambda-post-assignments.test.js
//
// This is a single "simple E2E" test that tests various invariants
// for the Lambda function lambda-get-post-assignments.mjs.

const test = require('node:test');
const { setupServer, stopServer } = require('./server-lifecycle.js');

test.before(setupServer);
test.after(stopServer);

// Test Batch 1: Condition assignment.
test("Should assign participants equally to 2 conditions, control vs. training-assisted.")

// Test Batch 2: Post assignment
test("Users should be assigned 20 unique posts");

test("Out of the 20 posts assigned to users, 5 should be low toxicity, 5 should be high toxicity, and 10 should be middle toxicity.");
test("Out of the 5 low-toxicity posts given to a user, 3 should be left-stance and 2 should be right-stance.");
test("Out of the 5 high-toxicity posts given to a user, assignment should alternate between 3 left/2 right and 2 left/3 right.");
test("Out of the 10 middle-toxicity posts given to a user, assignment should be split 5/5 between left and right.");

test("Out of 20 posts, users should see 10 left/10 right or 11 left/9 right.");

// Test Batch 3: Prioritizing unseen posts.
test("Unseen posts should be prioritized over seen posts.");

// Test Batch 4: Posts shown in each phase, per condition. Note: should test public/main.js, as this determines what's shown.
test("The 20 posts shown in the study should be split 10/10 between Phase 1 and Phase 2.");
test("In the control condition, users should see single evaluations in Phase 1 AND single evaluations in Phase 2.");
test("In the training-assisted condition, users should see linked fate evaluations in Phase 1 AND mirrored messages, but single evaluations in Phase 2.");

// NOTE: do we care what order the 20 assigned posts are shown in, and in which
// phase they're shown in?

// Test Batch 5: Idempotency
test("Same participant calling twice before save gets the same pending assignment back.");
test("Same participant calling after save gets the same committed assignment back, with already_assigned: true");

// Test Batch 6: Deduplication
test("No participant receives duplicate posts within their 20-post set.");

// Test Batch 7: Error handling
