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

const NUM_POSTS_PER_PARTICIPANT = 10;
const CONDITIONS = ['control', 'linked_fate'];

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

        if (!all_posts || !Array.isArray(all_posts) || all_posts.length === 0) {
            return corsResponse(400, { error: 'Missing or invalid all_posts array' });
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
        const availablePosts = all_posts;

        const testNote = inferredTest ? ' [test]' : '';
        console.log(`Available posts for ${party_group}: ${availablePosts.length}/${all_posts.length}${testNote}`);

        const getCounts = (post) => {
            const assignment = assignments.posts[post.post_id];
            const conditionCount = assignment?.counts?.[assignedCondition] || 0;
            const totalCount = assignment?.counts
                ? Object.values(assignment.counts).reduce((sum, count) => sum + count, 0)
                : 0;
            return { conditionCount, totalCount };
        };

        const sortByLeastViewed = (a, b) => {
            const aCounts = getCounts(a);
            const bCounts = getCounts(b);
            if (aCounts.conditionCount !== bCounts.conditionCount) return aCounts.conditionCount - bCounts.conditionCount;
            if (aCounts.totalCount !== bCounts.totalCount) return aCounts.totalCount - bCounts.totalCount;
            return Math.random() - 0.5;
        };

        // Select lowest-viewed posts first for the assigned condition
        const selectedPosts = [...availablePosts]
            .sort(sortByLeastViewed)
            .slice(0, NUM_POSTS_PER_PARTICIPANT);

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

        const shortNote = shortAssignment ? ' (short assignment: under-cap posts exhausted)' : '';
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
