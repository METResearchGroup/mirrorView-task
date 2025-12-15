// gets participant IDs extracted from frontend

import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });

const BUCKET_NAME = 'jspsych-rate-tweets';
const ASSIGNMENTS_FILE = 'data/participant_assignments.json';

export const handler = async (event) => {
    // handle DELETE requests for removing participant IDs
    if (event.httpMethod === 'DELETE') {
        const prolificID = event.queryStringParameters.prolific_id;
        
        if (!prolificID) {
            return {
                statusCode: 400,
                body: JSON.stringify({ error: 'No Prolific ID provided' }),
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            };
        }

        try {
            // read current assignments
            const data = await s3Client.send(new GetObjectCommand({
                Bucket: BUCKET_NAME,
                Key: ASSIGNMENTS_FILE
            }));
            const assignments = JSON.parse(await data.Body.transformToString());

            // remove the participant from both party assignments
            if (assignments.democrat?.assignments[prolificID]) {
                delete assignments.democrat.assignments[prolificID];
            }
            if (assignments.republican?.assignments[prolificID]) {
                delete assignments.republican.assignments[prolificID];
            }

            // write updated assignments back to S3
            await s3Client.send(new PutObjectCommand({
                Bucket: BUCKET_NAME,
                Key: ASSIGNMENTS_FILE,
                Body: JSON.stringify(assignments),
                ContentType: 'application/json'
            }));

            return {
                statusCode: 200,
                body: JSON.stringify({ message: 'Participant ID removed successfully' }),
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            };
        } catch (error) {
            console.error('Error:', error);
            return {
                statusCode: 500,
                body: JSON.stringify({ error: 'Internal server error' }),
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            };
        }
    }

    // handle GET requests for assigning participant IDs
    const prolificID = event.queryStringParameters.prolific_id;
    const party = event.queryStringParameters.party;

    if (!prolificID || !party) {
        return {
            statusCode: 400,
            body: JSON.stringify({ error: 'Missing required parameters' }),
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        };
    }

    try {
        // read current assignments from S3
        let assignments;
        try {
            const data = await s3Client.send(new GetObjectCommand({
                Bucket: BUCKET_NAME,
                Key: ASSIGNMENTS_FILE
            }));
            assignments = JSON.parse(await data.Body.transformToString());
            console.log('Current assignments:', JSON.stringify(assignments, null, 2)); // Debug log
        } catch (error) {
            if (error.name === 'NoSuchKey') {
                assignments = {
                    democrat: { count: 0, assignments: {} },
                    republican: { count: 0, assignments: {} }
                };
                console.log('Created new assignments object:', JSON.stringify(assignments, null, 2)); // Debug log
            } else {
                console.error('Error reading assignments from S3:', error);
                throw error;
            }
        }

        // Initialize party counters if they don't exist
        if (!assignments.democrat) {
            assignments.democrat = { count: 0, assignments: {} };
        }
        if (!assignments.republican) {
            assignments.republican = { count: 0, assignments: {} };
        }

        // Determine which party counter to use
        const partyType = (party === 'democrat' || party === 'lean_democrat') ? 'democrat' : 'republican';
        console.log('Party type:', partyType); // Debug log
        console.log('Current party count:', assignments[partyType].count); // Debug log
        console.log('Current party assignments:', assignments[partyType].assignments); // Debug log

        // Check if participant already has an assignment
        if (assignments[partyType].assignments[prolificID]) {
            console.log('Found existing assignment for prolificID:', prolificID); // Debug log
            return {
                statusCode: 200,
                body: JSON.stringify({ 
                    participantID: assignments[partyType].assignments[prolificID],
                    partyCount: assignments[partyType].count 
                }),
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            };
        }

        // Assign new ID based on party-specific counter
        assignments[partyType].count++;
        assignments[partyType].assignments[prolificID] = assignments[partyType].count;
        console.log('New assignment created:', { // Debug log
            prolificID,
            partyType,
            newCount: assignments[partyType].count,
            allAssignments: assignments
        });

        // Save updated assignments
        await s3Client.send(new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: ASSIGNMENTS_FILE,
            Body: JSON.stringify(assignments),
            ContentType: 'application/json'
        }));       

        return {
            statusCode: 200,
            body: JSON.stringify({ 
                participantID: assignments[partyType].count,  // Changed from tempID
                partyCount: assignments[partyType].count 
            }),
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        };
    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Internal server error' }),
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        };
    }
};