// saves experiment data to S3 bucket

import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });

const BUCKET_NAME = 'jspsych-mirror-view';
const DATA_PREFIX_PROLIFIC = 'data/prolific/';
const DATA_PREFIX_TEST = 'data/test/';

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
