// saves experiment data to S3 bucket

import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });

const BUCKET_NAME = 'jspsych-rate-tweets';
const DATA_PREFIX = 'data/';

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

    const filename = `data_${Date.now()}.csv`;

    try {
        // write csv data to S3
        await s3Client.send(new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: DATA_PREFIX + filename,
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