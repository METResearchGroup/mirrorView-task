const crypto = require("crypto");

const BUCKET = "mirrorview-experimental-artifacts";
const REGION = process.env.AWS_REGION || "us-east-2";
const POINTS_KEY = "experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/map/map-points.json";
const TEXTS_KEY = "experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/map/map-texts.json";
const EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

let textsPromise = null;

function hmac(key, value) {
  return crypto.createHmac("sha256", key).update(value).digest();
}

async function readObject(key) {
  const accessKey = process.env.AWS_ACCESS_KEY_ID;
  const secret = process.env.AWS_SECRET_ACCESS_KEY;
  if (!accessKey || !secret) {
    throw new Error("Missing storage credentials");
  }
  const host = `${BUCKET}.s3.${REGION}.amazonaws.com`;
  const amzDate = new Date().toISOString().replace(/[:-]|\.\d{3}/g, "");
  const dateStamp = amzDate.slice(0, 8);
  const canonicalUri = `/${key.split("/").map(encodeURIComponent).join("/")}`;
  const canonicalHeaders = `host:${host}\nx-amz-content-sha256:${EMPTY_HASH}\nx-amz-date:${amzDate}\n`;
  const signedHeaders = "host;x-amz-content-sha256;x-amz-date";
  const canonicalRequest = ["GET", canonicalUri, "", canonicalHeaders, signedHeaders, EMPTY_HASH].join("\n");
  const scope = `${dateStamp}/${REGION}/s3/aws4_request`;
  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    scope,
    crypto.createHash("sha256").update(canonicalRequest).digest("hex"),
  ].join("\n");
  const signingKey = hmac(hmac(hmac(hmac(`AWS4${secret}`, dateStamp), REGION), "s3"), "aws4_request");
  const signature = crypto.createHmac("sha256", signingKey).update(stringToSign).digest("hex");
  const authorization = `AWS4-HMAC-SHA256 Credential=${accessKey}/${scope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;
  const response = await fetch(`https://${host}${canonicalUri}`, {
    headers: {
      Authorization: authorization,
      "x-amz-content-sha256": EMPTY_HASH,
      "x-amz-date": amzDate,
    },
  });
  if (!response.ok) {
    throw new Error(`Storage read failed (${response.status})`);
  }
  return response.text();
}

function loadTexts() {
  if (!textsPromise) {
    textsPromise = readObject(TEXTS_KEY).then((body) => JSON.parse(body));
    textsPromise.catch(() => {
      textsPromise = null;
    });
  }
  return textsPromise;
}

module.exports = async function handler(req, res) {
  try {
    const kind = req.query.kind;
    if (kind === "points") {
      const body = await readObject(POINTS_KEY);
      res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.setHeader("Cache-Control", "public, max-age=3600");
      res.status(200).send(body);
      return;
    }
    if (kind === "text") {
      const index = Number(req.query.i);
      const texts = await loadTexts();
      if (!Number.isInteger(index) || index < 0 || index >= texts.length) {
        res.status(400).json({ error: "Unknown dot" });
        return;
      }
      res.setHeader("Cache-Control", "public, max-age=86400");
      res.status(200).json({ text: texts[index] });
      return;
    }
    res.status(400).json({ error: "Unknown request" });
  } catch (error) {
    textsPromise = null;
    res.status(500).json({ error: "The map could not be loaded" });
  }
};
