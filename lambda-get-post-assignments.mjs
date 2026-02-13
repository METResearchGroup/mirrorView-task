/**
 * AWS Lambda function for assigning posts to participants
 * 
 * This function manages post assignments to ensure each post gets rated by
 * exactly 3 democrats and 3 republicans (6 total).
 * 
 * Uses S3 to store assignment data (same pattern as other Lambda functions).
 */

import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });

// Configuration - matches existing setup
const BUCKET_NAME = 'jspsych-mirror-view';
const POST_ASSIGNMENTS_FILE = 'data/prolific/post_assignments.json';
const POST_ASSIGNMENTS_TEST_FILE = 'data/test/post_assignments.json';
const PENDING_ASSIGNMENTS_FILE = 'data/prolific/pending_assignments.json';
const PENDING_ASSIGNMENTS_TEST_FILE = 'data/test/pending_assignments.json';
const POST_CATALOG_KEY = 'img/all_mirrors_claude.csv';

const NUM_POSTS_PER_PARTICIPANT = 10;
const CONDITIONS = ['control', 'linked_fate'];
const CATEGORY_ORDER = [
    'left__sample_low_toxicity',
    'left__sample_high_toxicity',
    'left__sample_middle_toxicity',
    'right__sample_low_toxicity',
    'right__sample_high_toxicity',
    'right__sample_middle_toxicity'
];

let cachedPostCatalog = null;

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
                    i++;
                } else {
                    inQuotes = false;
                }
            } else {
                currentField += char;
            }
        } else {
            if (char === '"') {
                inQuotes = true;
            } else if (char === ',') {
                currentRow.push(currentField);
                currentField = '';
            } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
                if (char === '\r') i++;
                currentRow.push(currentField);
                currentField = '';

                if (isFirstRow) {
                    headers.push(...currentRow);
                    isFirstRow = false;
                } else if (currentRow.length > 0 && currentRow.some(f => f.trim() !== '')) {
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
    }

    if (currentField !== '' || currentRow.length > 0) {
        currentRow.push(currentField);
        if (currentRow.length > 0 && currentRow.some(f => f.trim() !== '')) {
            const rowObj = {};
            headers.forEach((header, idx) => {
                rowObj[header] = currentRow[idx] || '';
            });
            rows.push(rowObj);
        }
    }

    return rows;
}

async function getPostCatalog() {
    if (cachedPostCatalog && cachedPostCatalog.length > 0) {
        return cachedPostCatalog;
    }

    const data = await s3Client.send(new GetObjectCommand({
        Bucket: BUCKET_NAME,
        Key: POST_CATALOG_KEY
    }));
    const csvText = await data.Body.transformToString();
    const parsed = parseCSV(csvText);
    cachedPostCatalog = parsed
        .filter(row => row.post_primary_key && row.post_number)
        .map(row => ({
            post_id: row.post_primary_key,
            post_number: row.post_number,
            sampled_stance: row.sampled_stance,
            sample_toxicity_type: row.sample_toxicity_type
        }));

    return cachedPostCatalog;
}

export const handler = async (event) => {
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return corsResponse(200, '');
    }

    try {
        // Parse request body
        let body;
        if (typeof event.body === 'string') {
            body = JSON.parse(event.body);
        } else {
            body = event.body || {};
        }

        const { prolific_id, party_group, all_posts, is_test } = body;

        // Validate inputs
        if (!prolific_id) {
            return corsResponse(400, { error: 'Missing prolific_id' });
        }

        if (!party_group || !['democrat', 'republican'].includes(party_group)) {
            return corsResponse(400, { error: 'Invalid party_group. Must be "democrat" or "republican"' });
        }

        let postPool = Array.isArray(all_posts) && all_posts.length > 0 ? all_posts : null;
        if (!postPool) {
            postPool = await getPostCatalog();
        }
        if (!postPool || postPool.length === 0) {
            return corsResponse(400, { error: 'No posts available for assignment' });
        }

        const inferredTest = is_test === true
            || (typeof prolific_id === 'string' && (prolific_id.startsWith('UNKNOWN_') || prolific_id.startsWith('TEST_')));
        const assignmentKey = inferredTest ? POST_ASSIGNMENTS_TEST_FILE : POST_ASSIGNMENTS_FILE;
        const pendingKey = inferredTest ? PENDING_ASSIGNMENTS_TEST_FILE : PENDING_ASSIGNMENTS_FILE;

        // Read current assignments from S3
        let assignments;
        try {
            const data = await s3Client.send(new GetObjectCommand({
                Bucket: BUCKET_NAME,
                Key: assignmentKey
            }));
            assignments = JSON.parse(await data.Body.transformToString());
            console.log(`Loaded ${Object.keys(assignments.posts || {}).length} post assignments`);
        } catch (error) {
            if (error.name === 'NoSuchKey') {
                // Initialize empty assignments structure
                assignments = {
                    posts: {},           // { post_id: { post_number, counts: { control, linked_fate } } }
                    participants: {}     // { prolific_id: { party, condition, posts: [{post_id, post_number}], assigned_at } }
                };
                console.log(`Created new post assignments file: ${assignmentKey}`);
            } else {
                console.error('Error reading post assignments from S3:', error);
                throw error;
            }
        }

        // Initialize structure if missing
        if (!assignments.posts) assignments.posts = {};
        if (!assignments.participants) assignments.participants = {};

        // Read pending assignments
        let pendingAssignments;
        try {
            const pendingData = await s3Client.send(new GetObjectCommand({
                Bucket: BUCKET_NAME,
                Key: pendingKey
            }));
            pendingAssignments = JSON.parse(await pendingData.Body.transformToString());
        } catch (error) {
            if (error.name === 'NoSuchKey') {
                pendingAssignments = {};
                console.log(`Created new pending assignments file: ${pendingKey}`);
            } else {
                console.error('Error reading pending assignments from S3:', error);
                throw error;
            }
        }

        // Check if participant already has completed assignments
        if (assignments.participants[prolific_id] && assignments.participants[prolific_id].posts) {
            const existingPosts = assignments.participants[prolific_id].posts;
            const postIds = existingPosts.map(p => p.post_id || p);
            if (postIds.length >= NUM_POSTS_PER_PARTICIPANT) {
                console.log(`Returning existing assignment for ${prolific_id}`);
                return corsResponse(200, {
                    assigned_post_ids: postIds,
                    already_assigned: true,
                    condition: assignments.participants[prolific_id].condition || 'control',
                    is_test: inferredTest
                });
            }
        }

        // Check pending assignments
        const pending = pendingAssignments[prolific_id];
        if (pending && pending.posts) {
            return corsResponse(200, {
                assigned_post_ids: pending.posts.map(p => p.post_id || p),
                already_assigned: true,
                condition: pending.condition || 'control',
                is_test: inferredTest
            });
        }

        // Assign condition by alternating within party (based on completed count)
        const completedPartyCount = Object.values(assignments.participants)
            .filter(p => p.party === party_group).length;
        const assignedCondition = completedPartyCount % 2 === 0 ? 'control' : 'linked_fate';

        // Find available posts
        const availablePosts = postPool;

        const testNote = inferredTest ? ' [test]' : '';
        console.log(`Available posts for ${party_group}: ${availablePosts.length}/${postPool.length}${testNote}`);

        const sortedPosts = [...availablePosts].sort((a, b) => Number(a.post_number) - Number(b.post_number));
        const completedInCondition = Object.values(assignments.participants || {})
            .filter(participant => participant?.condition === assignedCondition)
            .length;
        const startOffset = completedInCondition % CATEGORY_ORDER.length;

        const getCategoryKey = (post) => {
            const stance = String(post.sampled_stance || '').trim().toLowerCase();
            const tox = String(post.sample_toxicity_type || '').trim().toLowerCase();
            const key = `${stance}__${tox}`;
            return CATEGORY_ORDER.includes(key) ? key : null;
        };

        const getConditionCount = (post) => {
            const assignment = assignments.posts[post.post_id];
            return assignment?.counts?.[assignedCondition] || 0;
        };

        const selectedPosts = [];
        const selectedIds = new Set();

        // Phase 1: unseen posts only
        const unseenBuckets = {};
        CATEGORY_ORDER.forEach(k => { unseenBuckets[k] = []; });
        sortedPosts.forEach(post => {
            const key = getCategoryKey(post);
            if (!key) return;
            if (getConditionCount(post) === 0) {
                unseenBuckets[key].push(post);
            }
        });

        let pickedInPass = true;
        while (selectedPosts.length < NUM_POSTS_PER_PARTICIPANT && pickedInPass) {
            pickedInPass = false;
            for (let i = 0; i < CATEGORY_ORDER.length && selectedPosts.length < NUM_POSTS_PER_PARTICIPANT; i++) {
                const key = CATEGORY_ORDER[(startOffset + i) % CATEGORY_ORDER.length];
                const bucket = unseenBuckets[key];
                if (bucket && bucket.length > 0) {
                    const post = bucket.shift();
                    if (!selectedIds.has(post.post_id)) {
                        selectedIds.add(post.post_id);
                        selectedPosts.push(post);
                        pickedInPass = true;
                    }
                }
            }
        }

        // Phase 2: repeats after unseen are exhausted
        if (selectedPosts.length < NUM_POSTS_PER_PARTICIPANT) {
            const seenBuckets = {};
            CATEGORY_ORDER.forEach(k => { seenBuckets[k] = []; });
            sortedPosts.forEach(post => {
                if (selectedIds.has(post.post_id)) return;
                const key = getCategoryKey(post);
                if (!key) return;
                seenBuckets[key].push(post);
            });
            CATEGORY_ORDER.forEach(key => {
                seenBuckets[key].sort((a, b) => {
                    const aCount = getConditionCount(a);
                    const bCount = getConditionCount(b);
                    if (aCount !== bCount) return aCount - bCount;
                    return Number(a.post_number) - Number(b.post_number);
                });
            });

            pickedInPass = true;
            while (selectedPosts.length < NUM_POSTS_PER_PARTICIPANT && pickedInPass) {
                pickedInPass = false;
                for (let i = 0; i < CATEGORY_ORDER.length && selectedPosts.length < NUM_POSTS_PER_PARTICIPANT; i++) {
                    const key = CATEGORY_ORDER[(startOffset + i) % CATEGORY_ORDER.length];
                    const bucket = seenBuckets[key];
                    if (bucket && bucket.length > 0) {
                        const post = bucket.shift();
                        if (!selectedIds.has(post.post_id)) {
                            selectedIds.add(post.post_id);
                            selectedPosts.push(post);
                            pickedInPass = true;
                        }
                    }
                }
            }
        }

        const shortAssignment = selectedPosts.length < NUM_POSTS_PER_PARTICIPANT;

        pendingAssignments[prolific_id] = {
            party: party_group,
            condition: assignedCondition,
            posts: selectedPosts.map(p => ({ post_id: p.post_id, post_number: p.post_number })),
            assigned_at: new Date().toISOString()
        };

        await s3Client.send(new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: pendingKey,
            Body: JSON.stringify(pendingAssignments, null, 2),
            ContentType: 'application/json'
        }));

        const shortNote = shortAssignment ? ' (short assignment)' : '';
        console.log(`Assigned ${selectedPosts.length} posts to ${prolific_id} (${party_group}, ${assignedCondition})${shortNote}${testNote}: ${selectedPosts.map(p => p.post_number).join(', ')}`);

        return corsResponse(200, {
            assigned_post_ids: selectedPosts.map(p => p.post_id),
            already_assigned: false,
            short_assignment: shortAssignment,
            condition: assignedCondition,
            is_test: inferredTest
        });

    } catch (error) {
        console.error('Error processing request:', error);
        return corsResponse(500, { error: 'Internal server error', message: error.message });
    }
};

/**
 * Create response with CORS headers
 */
function corsResponse(statusCode, body) {
    return {
        statusCode,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        body: typeof body === 'string' ? body : JSON.stringify(body)
    };
}
