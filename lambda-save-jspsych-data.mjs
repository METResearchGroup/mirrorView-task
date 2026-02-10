// saves experiment data to S3 bucket

import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });

const BUCKET_NAME = 'jspsych-mirror-view';
const DATA_PREFIX_PROLIFIC = 'data/prolific/';
const DATA_PREFIX_TEST = 'data/test/';
const POST_ASSIGNMENTS_FILE = 'data/prolific/post_assignments.json';
const POST_ASSIGNMENTS_TEST_FILE = 'data/test/post_assignments.json';
const PENDING_ASSIGNMENTS_FILE = 'data/prolific/pending_assignments.json';
const PENDING_ASSIGNMENTS_TEST_FILE = 'data/test/pending_assignments.json';

export const handler = async (event) => {
    // parse incoming JSON body
    const body = JSON.parse(event.body);

    if (!body || !body.csv) {
        return {
            statusCode: 400,
            body: JSON.stringify({ error: 'No data provided' }),
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        };
    }

    const prolificId = body.prolific_id;
    const inferredTest = body.is_test === true
        || !prolificId
        || (typeof prolificId === 'string' && (prolificId.startsWith('UNKNOWN_') || prolificId.startsWith('TEST_')));
    const prefix = inferredTest ? DATA_PREFIX_TEST : DATA_PREFIX_PROLIFIC;
    const filename = `data_${Date.now()}.csv`;

    try {
        // write csv data to S3
        await s3Client.send(new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: prefix + filename,
            Body: body.csv,
            ContentType: 'text/csv'
        }));

        // Commit pending assignments after data is saved
        if (prolificId) {
            const assignmentKey = inferredTest ? POST_ASSIGNMENTS_TEST_FILE : POST_ASSIGNMENTS_FILE;
            const pendingKey = inferredTest ? PENDING_ASSIGNMENTS_TEST_FILE : PENDING_ASSIGNMENTS_FILE;

            let assignments;
            try {
                const assignmentsData = await s3Client.send(new GetObjectCommand({
                    Bucket: BUCKET_NAME,
                    Key: assignmentKey
                }));
                assignments = JSON.parse(await assignmentsData.Body.transformToString());
            } catch (error) {
                if (error.name === 'NoSuchKey') {
                    assignments = { posts: {}, participants: {} };
                } else {
                    throw error;
                }
            }

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
                } else {
                    throw error;
                }
            }

            const pending = pendingAssignments[prolificId];
            if (pending && pending.posts && pending.posts.length > 0) {
                pending.posts.forEach(post => {
                    if (!assignments.posts[post.post_id]) {
                        assignments.posts[post.post_id] = {
                            post_number: post.post_number,
                            counts: { control: 0, linked_fate: 0 }
                        };
                    }
                    if (!assignments.posts[post.post_id].counts) {
                        assignments.posts[post.post_id].counts = { control: 0, linked_fate: 0 };
                    }
                    assignments.posts[post.post_id].counts[pending.condition] =
                        (assignments.posts[post.post_id].counts[pending.condition] || 0) + 1;
                });

                assignments.participants[prolificId] = {
                    party: pending.party,
                    condition: pending.condition,
                    posts: pending.posts,
                    assigned_at: pending.assigned_at
                };

                delete pendingAssignments[prolificId];

                await s3Client.send(new PutObjectCommand({
                    Bucket: BUCKET_NAME,
                    Key: assignmentKey,
                    Body: JSON.stringify(assignments, null, 2),
                    ContentType: 'application/json'
                }));

                await s3Client.send(new PutObjectCommand({
                    Bucket: BUCKET_NAME,
                    Key: pendingKey,
                    Body: JSON.stringify(pendingAssignments, null, 2),
                    ContentType: 'application/json'
                }));
            }
        }

        return {
            statusCode: 200,
            body: JSON.stringify({ message: 'Data saved successfully' }),
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        };
    } catch (error) {
        console.error('Error saving data to S3:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Failed to save data to S3' }),
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        };
    }
};
