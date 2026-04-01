const path = require('node:path');
const fs = require('node:fs');
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

const POST_CATALOG_FILE = path.join(__dirname, '..', 'img', 'all_mirrors_claude.csv');
let cachedCatalog = null;

function parseCSV(csvText) {
    const rows = [];
    const headers = [];
    let currentRow = [];
    let currentField = '';
    let inQuotes = false;
    let isFirstRow = true;

    for (let i = 0; i < csvText.length; i++) {
        const char = csvText[i];
        const nextChar = csvText[i + 1];

        if (inQuotes) {
            if (char === '"') {
                if (nextChar === '"') {
                    currentField += '"';
                    i += 1;
                } else {
                    inQuotes = false;
                }
            } else {
                currentField += char;
            }
        } else if (char === '"') {
            inQuotes = true;
        } else if (char === ',') {
            currentRow.push(currentField);
            currentField = '';
        } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
            if (char === '\r') i += 1;
            currentRow.push(currentField);
            currentField = '';

            if (isFirstRow) {
                headers.push(...currentRow);
                isFirstRow = false;
            } else if (currentRow.length > 0 && currentRow.some((field) => field.trim() !== '')) {
                const rowObj = {};
                headers.forEach((header, idx) => {
                    rowObj[header] = currentRow[idx] || '';
                });
                rows.push(rowObj);
            }
            currentRow = [];
        } else if (char !== '\r') {
            currentField += char;
        }
    }

    if (currentField !== '' || currentRow.length > 0) {
        currentRow.push(currentField);
        if (currentRow.length > 0 && currentRow.some((field) => field.trim() !== '')) {
            const rowObj = {};
            headers.forEach((header, idx) => {
                rowObj[header] = currentRow[idx] || '';
            });
            rows.push(rowObj);
        }
    }

    return rows;
}

function buildCatalog() {
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
    buildCatalog,
    makePosts,
    createAssignments,
    createParticipant,
    loadGetAssignmentsHandler,
    invokeGetAssignments,
};
