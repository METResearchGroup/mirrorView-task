/**
 * @file Lambda test harness for testing the Lambda function.
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

/* Parses the Lambda's JSON response. 

Takes a Lambda-style HTTP response (with a body that is a JSON string) and
returns a new object with all original response fields plus a new json field
containing the parsed body.
*/

function parseLambdaResponse(response) {
    return {
        ...response,
        json: typeof response.body === 'string' ? JSON.parse(response.body) : response.body,
    };
}

/*Invokes the lambda handler as a JSON API.

This function wraps a the lambda handler so it can be called in tests as
if it were triggered by an HTTP JSON request. It:
- stringifies the body
- applies any overrides
- parses the Lambda's JSON response

It ensures tests invoke handlers just like real HTTP events, preventing
subtle bugs from test/request mismatch.
*/
async function invokeJsonHandler(handler, body, eventOverrides = {}) {
    const response = await handler({
        body: JSON.stringify(body),
        ...eventOverrides,
    });

    return parseLambdaResponse(response);
}

/* Loads the lambda function and mocks the S3 client. This allows us to test
the prod lambda code in a test environment, without actually hitting S3.
*/
async function loadLambdaWithMockedS3({ modulePath, initialStore = {} }) {
    const store = new Map(
        Object.entries(initialStore).map(([key, value]) => [
            key,
            typeof value === 'string' ? value : JSON.stringify(value),
        ])
    );

    /* Temp files setup */
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mirrorview-lambda-test-'));
    const stubModulePath = path.join(tempDir, 'client-s3-stub.mjs');
    const lambdaCopyPath = path.join(tempDir, `${path.basename(modulePath, '.mjs')}.test-copy.mjs`);

    /*
    - stub module: fake S3 client that reads/writes to in-memory store.
    */
    const stubSource = `
const __store = new Map(${JSON.stringify(Array.from(store.entries()))});
globalThis.__mirrorViewTestStore = __store;
globalThis.__mirrorViewTestPutCalls = [];

export class GetObjectCommand {
    constructor(input) {
        this.input = input;
    }
}

export class PutObjectCommand {
    constructor(input) {
        this.input = input;
    }
}

export class S3Client {
    async send(command) {
        if (command instanceof GetObjectCommand) {
            const key = command.input.Key;
            if (!__store.has(key)) {
                const error = new Error(\`Missing key: \${key}\`);
                error.name = 'NoSuchKey';
                throw error;
            }

            const body = __store.get(key);
            return {
                Body: {
                    async transformToString() {
                        return body;
                    }
                }
            };
        }

        if (command instanceof PutObjectCommand) {
            globalThis.__mirrorViewTestPutCalls.push(command.input);
            __store.set(command.input.Key, String(command.input.Body));
            return {};
        }

        throw new Error(\`Unsupported command: \${command?.constructor?.name || 'unknown'}\`);
    }
}
`;

    /*
    - read actual lambda source code from disk.
    - string-replace the specific S3 import line. from: @aws-sdk/client-s3, to: temp stub module file URL.
    */
    const originalSource = fs.readFileSync(modulePath, 'utf8');
    const rewrittenSource = originalSource.replace(
        'import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";',
        `import { S3Client, GetObjectCommand, PutObjectCommand } from ${JSON.stringify(pathToFileURL(stubModulePath).href)};`
    );

    /*
    - write stub module to disk.
    - write rewritten lambda copy to disk.
    - convert lambda copy path to file URL.
    */
    fs.writeFileSync(stubModulePath, stubSource);
    fs.writeFileSync(lambdaCopyPath, rewrittenSource);

    const moduleUrl = pathToFileURL(lambdaCopyPath);
    const imported = await import(`${moduleUrl.href}?test=${Date.now()}-${Math.random()}`);

    /*
    - handler: real lambda handler function from rewritten copy.
    - store: in-memory fake S3 state (inspect reads/writes).
    - putCalls: raw write call payloads.
    */
    return {
        handler: imported.handler,
        store: globalThis.__mirrorViewTestStore,
        putCalls: globalThis.__mirrorViewTestPutCalls,
    };
}

module.exports = {
    invokeJsonHandler,
    loadLambdaWithMockedS3,
    parseLambdaResponse,
};
