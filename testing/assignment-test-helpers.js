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
 * Load and normalize posts from the real mirror CSV fixture.
 *
 * Source: `img/all_mirrors_claude.csv`.
 * Output shape: `{ post_id, post_number, sampled_stance, sample_toxicity_type }`,
 * matching what the assignment Lambda expects.
 * Results are memoized after first read for faster test runs.
 *
 * @returns {Array<{
 *   post_id: string,
 *   post_number: string,
 *   sampled_stance: string,
 *   sample_toxicity_type: string
 * }>}
 */
function loadPostsFromMirrorCsv() {
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

/* Creates a list of posts with a given prefix and count.

@param {string} prefix - The prefix to use for the post IDs.
@param {number} count - The number of posts to create.
@returns {Array<{ post_id: string, post_number: string }>}
*/
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

/* Loads the assignments lambda handler with a mocked S3 client. 

@param {Object} initialStore - Initial S3 state to mock. initialStore is a
plain JavaScript object representing the initial mock state of S3 buckets/keys,
used to simulate S3 storage for tests.
@returns {Promise<{ handler: Function, store: Map, putCalls: Array }>}
*/
async function loadGetAssignmentsHandler(initialStore = {}) {
    return loadLambdaWithMockedS3({
        modulePath: GET_ASSIGNMENTS_LAMBDA_PATH,
        initialStore,
    });
}

async function runGetAssignmentsHandler(handler, body) {
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
    loadPostsFromMirrorCsv,
    makePosts,
    createAssignments,
    createParticipant,
    loadGetAssignmentsHandler,
    runGetAssignmentsHandler,
};
