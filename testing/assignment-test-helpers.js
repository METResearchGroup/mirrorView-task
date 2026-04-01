const path = require('node:path');
const { loadLambdaWithMockedS3, invokeJsonHandler } = require('./lambda-test-harness.js');

const GET_ASSIGNMENTS_LAMBDA_PATH = path.join(__dirname, '..', 'lambda-get-post-assignments.mjs');
const PROD_ASSIGNMENTS_KEY = 'data/prolific/post_assignments.json';
const PROD_PENDING_KEY = 'data/prolific/pending_assignments.json';
const TEST_ASSIGNMENTS_KEY = 'data/test/post_assignments.json';
const TEST_PENDING_KEY = 'data/test/pending_assignments.json';
const CONDITIONS = ['control', 'training', 'training_assisted'];
const TOXICITY_TYPES = [
    'sample_low_toxicity',
    'sample_high_toxicity',
    'sample_middle_toxicity'
];

function buildCatalog({ perCell = 12, stances = ['left', 'right'], toxicityTypes = TOXICITY_TYPES } = {}) {
    const posts = [];
    let counter = 1;

    for (const toxicity of toxicityTypes) {
        for (const stance of stances) {
            for (let i = 0; i < perCell; i += 1) {
                posts.push({
                    post_id: `post-${String(counter).padStart(3, '0')}`,
                    post_number: String(counter),
                    sampled_stance: stance,
                    sample_toxicity_type: toxicity,
                });
                counter += 1;
            }
        }
    }

    return posts;
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
    buildCatalog,
    makePosts,
    createAssignments,
    createParticipant,
    loadGetAssignmentsHandler,
    invokeGetAssignments,
};
