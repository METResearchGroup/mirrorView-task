const path = require('node:path');

const GET_ASSIGNMENTS_LAMBDA_PATH = path.join(__dirname, '..', 'lambda-get-post-assignments.mjs');
const PROD_ASSIGNMENTS_KEY = 'data/prolific/post_assignments.json';
const PROD_PENDING_KEY = 'data/prolific/pending_assignments.json';
const TEST_ASSIGNMENTS_KEY = 'data/test/post_assignments.json';
const TEST_PENDING_KEY = 'data/test/pending_assignments.json';
const CONDITIONS = ['control', 'training', 'training_assisted'];
const TOXICITY_TYPES = [
    'sample_low_toxicity',
    'sample_high_toxicity',
    'sample_middle_toxicity',
];

module.exports = {
    GET_ASSIGNMENTS_LAMBDA_PATH,
    PROD_ASSIGNMENTS_KEY,
    PROD_PENDING_KEY,
    TEST_ASSIGNMENTS_KEY,
    TEST_PENDING_KEY,
    CONDITIONS,
    TOXICITY_TYPES,
};
