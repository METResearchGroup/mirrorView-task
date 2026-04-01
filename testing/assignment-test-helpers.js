const path = require('node:path');
const fs = require('node:fs');
const { loadLambdaWithMockedS3, invokeJsonHandler } = require('./lambda-test-harness.js');
const { parseCSV } = require('./csv-reader.js');
const {
    GET_ASSIGNMENTS_LAMBDA_PATH,
    PROD_ASSIGNMENTS_KEY,
    PROD_PENDING_KEY,
    TEST_ASSIGNMENTS_KEY,
    TEST_PENDING_KEY,
    CONDITIONS,
    TOXICITY_TYPES,
} = require('./constants.js');

const POST_CATALOG_FILE = path.join(__dirname, '..', 'img', 'all_mirrors_claude.csv');
let cachedCatalog = null;

/**
 * Load assignment-ready posts from the real CSV source used by the app.
 *
 * Reads `img/all_mirrors_claude.csv`, parses CSV rows, and normalizes each
 * eligible row into the assignment shape expected by the Lambda:
 * `{ post_id, post_number, sampled_stance, sample_toxicity_type }`.
 * Results are cached after first load to keep tests fast and deterministic.
 *
 * @returns {Array<{
 *   post_id: string,
 *   post_number: string,
 *   sampled_stance: string,
 *   sample_toxicity_type: string
 * }>}
 */
function loadPostsForAssignment() {
    if (cachedCatalog) return cachedCatalog;

    const csvText = fs.readFileSync(POST_CATALOG_FILE, 'utf8');
    const parsed = parseCSV(csvText);
    cachedCatalog = parsed
        .filter((row) => row.post_primary_key && row.post_number)
        .map((row) => ({
            post_id: row.post_primary_key,
            post_number: row.post_number,
            sampled_stance: row.sampled_stance,
            sample_toxicity_type: row.sample_toxicity_type,
        }));

    return cachedCatalog;
}

function makePosts(prefix, count = 20) {
    return Array.from({ length: count }, (_, index) => ({
        post_id: `${prefix}-${String(index + 1).padStart(2, '0')}`,
        post_number: String(index + 1),
    }));
}

function createAssignments(participants = {}, posts = {}) {
    return { posts, participants };
}

function createParticipant({ party, condition, posts = [], assignedAt = '2026-04-01T00:00:00.000Z' }) {
    return {
        party,
        condition,
        posts,
        assigned_at: assignedAt,
    };
}

async function loadGetAssignmentsHandler(initialStore = {}) {
    return loadLambdaWithMockedS3({
        modulePath: GET_ASSIGNMENTS_LAMBDA_PATH,
        initialStore,
    });
}

async function invokeGetAssignments(handler, body) {
    return invokeJsonHandler(handler, body);
}

module.exports = {
    CONDITIONS,
    GET_ASSIGNMENTS_LAMBDA_PATH,
    PROD_ASSIGNMENTS_KEY,
    PROD_PENDING_KEY,
    TEST_ASSIGNMENTS_KEY,
    TEST_PENDING_KEY,
    TOXICITY_TYPES,
    loadPostsForAssignment,
    makePosts,
    createAssignments,
    createParticipant,
    loadGetAssignmentsHandler,
    invokeGetAssignments,
};
