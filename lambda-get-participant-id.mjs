// gets participant IDs extracted from frontend

// No S3 writes here; participant IDs are generated locally

export const handler = async (event) => {
    // handle DELETE requests for removing participant IDs
    if (event.httpMethod === 'DELETE') {
        const prolificID = event.queryStringParameters?.prolific_id;
        const isTest = event.queryStringParameters?.is_test === 'true';
        
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
            const inferredTest = isTest
                || (typeof prolificID === 'string' && (prolificID.startsWith('UNKNOWN_') || prolificID.startsWith('TEST_')));
            const assignmentKey = inferredTest ? ASSIGNMENTS_FILE_TEST : ASSIGNMENTS_FILE_PROLIFIC;

            const data = await s3Client.send(new GetObjectCommand({
                Bucket: BUCKET_NAME,
                Key: assignmentKey
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
                Key: assignmentKey,
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
    const prolificID = event.queryStringParameters?.prolific_id;
    const party = event.queryStringParameters?.party;
    const isTest = event.queryStringParameters?.is_test === 'true';

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

    const participantID = `P_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    const partyType = (party === 'democrat' || party === 'lean_democrat') ? 'democrat' : 'republican';

    return {
        statusCode: 200,
        body: JSON.stringify({ participantID, partyCount: null, partyType }),
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    };
};
