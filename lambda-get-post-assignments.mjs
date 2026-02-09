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

const NUM_POSTS_PER_PARTICIPANT = 5;
const MAX_RATINGS_PER_PARTY = 3;

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
                    posts: {},           // { post_id: { post_number, democrat: count, republican: count } }
                    participants: {}     // { prolific_id: { party, posts: [{post_id, post_number}], assigned_at } }
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

        // Check if participant already has assignments
        if (assignments.participants[prolific_id] && assignments.participants[prolific_id].posts) {
            console.log(`Returning existing assignment for ${prolific_id}`);
            // Return just post_ids (handle both old format and new format)
            const existingPosts = assignments.participants[prolific_id].posts;
            const postIds = existingPosts.map(p => p.post_id || p); // Handle both formats
            return corsResponse(200, {
                assigned_post_ids: postIds,
                already_assigned: true,
                is_test: inferredTest
            });
        }

        // Find available posts (where party count < max)
        const availablePosts = all_posts.filter(post => {
            const assignment = assignments.posts[post.post_id];
            if (!assignment) return true;
            return (assignment[party_group] || 0) < MAX_RATINGS_PER_PARTY;
        });

        const testNote = inferredTest ? ' [test]' : '';
        console.log(`Available posts for ${party_group}: ${availablePosts.length}/${all_posts.length}${testNote}`);

        const getCounts = (post) => {
            const assignment = assignments.posts[post.post_id];
            const partyCount = assignment ? (assignment[party_group] || 0) : 0;
            const totalCount = assignment ? ((assignment.democrat || 0) + (assignment.republican || 0)) : 0;
            return { partyCount, totalCount };
        };

        const sortByLeastViewed = (a, b) => {
            const aCounts = getCounts(a);
            const bCounts = getCounts(b);
            if (aCounts.partyCount !== bCounts.partyCount) return aCounts.partyCount - bCounts.partyCount;
            if (aCounts.totalCount !== bCounts.totalCount) return aCounts.totalCount - bCounts.totalCount;
            return Math.random() - 0.5;
        };

        // Select lowest-viewed posts first for the participant's party
        // NOTE: We intentionally do NOT exceed MAX_RATINGS_PER_PARTY.
        const selectedPosts = [...availablePosts]
            .sort(sortByLeastViewed)
            .slice(0, NUM_POSTS_PER_PARTICIPANT);

        const shortAssignment = selectedPosts.length < NUM_POSTS_PER_PARTICIPANT;

        // Update post assignments (store both post_id and post_number)
        selectedPosts.forEach(post => {
            if (!assignments.posts[post.post_id]) {
                assignments.posts[post.post_id] = { 
                    post_number: post.post_number,
                    democrat: 0, 
                    republican: 0 
                };
            }
            assignments.posts[post.post_id][party_group]++;
        });

        // Save participant assignment (store both post_id and post_number)
        assignments.participants[prolific_id] = {
            party: party_group,
            posts: selectedPosts.map(p => ({ post_id: p.post_id, post_number: p.post_number })),
            assigned_at: new Date().toISOString()
        };

        // Write updated assignments back to S3
        await s3Client.send(new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: assignmentKey,
            Body: JSON.stringify(assignments, null, 2),
            ContentType: 'application/json'
        }));

        const shortNote = shortAssignment ? ' (short assignment: under-cap posts exhausted)' : '';
        console.log(`Assigned ${selectedPosts.length} posts to ${prolific_id} (${party_group})${shortNote}${testNote}: ${selectedPosts.map(p => p.post_number).join(', ')}`);

        return corsResponse(200, {
            assigned_post_ids: selectedPosts.map(p => p.post_id),
            already_assigned: false,
            short_assignment: shortAssignment,
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
