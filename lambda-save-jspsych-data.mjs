import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });
const BUCKET_NAME = "jspsych-mirror-view-3";
const DATA_PREFIX_PROLIFIC = "data/prolific/";
const DATA_PREFIX_TEST = "data/test/";

function corsResponse(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
    body: JSON.stringify(body),
  };
}

function inferIsTest(prolificId, explicitIsTest) {
  return (
    explicitIsTest === true ||
    !prolificId ||
    (typeof prolificId === "string" &&
      (prolificId.startsWith("UNKNOWN_") || prolificId.startsWith("TEST_")))
  );
}

export const handler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return corsResponse(200, {});
  }

  try {
    const body = JSON.parse(event.body || "{}");

    if (!body.csv) {
      return corsResponse(400, { error: "No data provided" });
    }

    const prolificId = body.prolific_id;
    const isTest = inferIsTest(prolificId, body.is_test);
    const prefix = isTest ? DATA_PREFIX_TEST : DATA_PREFIX_PROLIFIC;
    const filename = `data_${Date.now()}.csv`;

    await s3Client.send(
      new PutObjectCommand({
        Bucket: BUCKET_NAME,
        Key: `${prefix}${filename}`,
        Body: body.csv,
        ContentType: "text/csv",
      })
    );

    return corsResponse(200, {
      message: "Data saved successfully",
      key: `${prefix}${filename}`,
    });
  } catch (error) {
    console.error("Error saving data to S3:", error);
    return corsResponse(500, { error: "Failed to save data to S3" });
  }
};
