/**
 * AWS Lambda function for assigning posts to participants
 * 
 * Delegates to https://github.com/METResearchGroup/study_participant_assignment_interface
 * to get post assignments.
 */

import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const AWS_REGION = process.env.AWS_REGION || "us-east-2";
const lambdaClient = new LambdaClient({ region: AWS_REGION });

const ASSIGNMENT_LAMBDA_NAME = process.env.ASSIGNMENT_LAMBDA_NAME;
const TEST_ITERATION_PREFIX = process.env.TEST_ITERATION_PREFIX || "dev-";

// Source of truth: jobs/config/mirrorview_scaled_2026_06_18.yaml (assignment.batch_uri)
const SCALED_ITERATION_PREFIX = "mirrorview_scaled_2026_06_18";
const SCALED_BATCH_URI =
    "s3://jspsych-mirror-view-4/precomputed_assignments/2026_06_18-15:48:34";
const PILOT_BATCH_URI =
    "s3://jspsych-mirror-view-3/precomputed_assignments/2026_04_07-06:17:02";

const STUDY_SPEC = Object.freeze({
    conditions: ['training_assisted'],
    validPoliticalParties: ['democrat', 'republican'],
});

function resolveAssignmentBatchUri(studyIterationId) {
    const base = studyIterationId.replace(/^dev-/, "");
    if (base === SCALED_ITERATION_PREFIX || base.startsWith(SCALED_ITERATION_PREFIX)) {
        return SCALED_BATCH_URI;
    }
    return PILOT_BATCH_URI;
}

/**
 * Validate the inputs
 * @param {Object} inputs - The inputs to validate
 * @returns {void}
 */
function validateInputs(
    prolificId,
    partyGroup,
    studyId,
    studyIterationId
) {
    if (!prolificId) {
        throw new Error('Invalid prolificId: value is required');
    }
    if (!partyGroup) {
        throw new Error('Invalid partyGroup: value is required');
    }
    if (!STUDY_SPEC.validPoliticalParties.includes(partyGroup)) {
        throw new Error(`Invalid partyGroup: ${partyGroup}. Must be one of: ${STUDY_SPEC.validPoliticalParties.join(', ')}`);
    }
    if (!studyId) {
        throw new Error('Invalid STUDY_ID: value is required');
    }
    if (!studyIterationId) {
        throw new Error('Invalid STUDY_ITERATION_ID: value is required');
    }
}
/**
 * Create response with CORS headers
 * @param {number} statusCode - The status code of the response
 * @param {Object} body - The body of the response
 * @returns {Object} - The response object
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

/**
 * Parse the body of the event
 * @param {Object} event - The event object
 * @returns {Object} - The parsed body
 */
function parseBody(event) {
    if (!event.body) {
        throw new Error('Invalid request body: body is required');
    }
    try {
        const body = JSON.parse(event.body);
        return body;
    } catch {
        throw new Error('Invalid request body: must be valid JSON');
    }
}

async function callStudyAssignmentLambda({
    prolificId,
    partyGroup,
    isTest,
    studyId,
    studyIterationId
}) {
    if (isTest) {
        console.log(`Test participant; using study iteration ID: ${studyIterationId}`);
    }

    const assignmentBatchUri = resolveAssignmentBatchUri(studyIterationId);
    console.log(`Using assignment batch URI: ${assignmentBatchUri}`);

    const payload = {
        study_id: studyId,
        study_iteration_id: studyIterationId,
        prolific_id: prolificId,
        political_party: partyGroup,
        assignment_batch_uri: assignmentBatchUri,
    };

    const result = await lambdaClient.send(
        new InvokeCommand({
            FunctionName: ASSIGNMENT_LAMBDA_NAME,
            Payload: JSON.stringify(payload)
        })
    );

    // InvokeCommand does not give you a JavaScript string in result.Payload.
    // It gives you raw bytes. We need to decode first.
    if (result.FunctionError) {
        const decodedError = (
            result.Payload ? new TextDecoder().decode(result.Payload) : "{}"
        );
        let parsedError = null;
        try {
            parsedError = JSON.parse(decodedError);
        } catch {
            parsedError = null;
        }
        const errorMessage = (
            parsedError?.errorMessage ||
            parsedError?.error ||
            decodedError ||
            'Unknown error'
        );
        throw new Error(
            `Assignment lambda failed: ${result.FunctionError} ${errorMessage}`
        );
    }

    const decoded = (
        result.Payload ? new TextDecoder().decode(result.Payload) : "{}"
    );

    const parsed = JSON.parse(decoded);

    /* Validate the response values */
    if (
        !parsed ||
        !Array.isArray(parsed.assigned_post_ids) ||
        !STUDY_SPEC.conditions.includes(parsed.condition)
    ) {
        throw new Error(`Unexpected assignment response: ${decoded}`);
    }

    return {
        ...parsed,
        assignedPostIds: parsed.assigned_post_ids,
    };
}


/*** MAIN HANDLER ***/

export const handler = async (event) => {
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return corsResponse(200, '');
    }

    try {

        const body = parseBody(event);
        
        const prolificId = body.prolificId;
        const partyGroup = body.partyGroup;
        const isTest = body.isTest;
        const studyId = body.STUDY_ID;
        const studyIterationId = body.STUDY_ITERATION_ID;

        validateInputs(prolificId, partyGroup, studyId, studyIterationId);

        const assignment = await callStudyAssignmentLambda({
            prolificId,
            partyGroup,
            isTest,
            studyId,
            studyIterationId
        });

        return corsResponse(200, {
            assignedPostIds: assignment.assignedPostIds,
            alreadyAssigned: assignment.alreadyAssigned,
            condition: assignment.condition,
            isTest: isTest,
          });
      

    } catch (error) {
        console.error("Error getting post assignments:", error);
        const message = (
            error instanceof Error ? error.message : "Internal server error"
        );
        const statusCode = (
            message.startsWith("Missing") || message.startsWith("Invalid") ? 400 : 500
        );
        return corsResponse(statusCode, { error: message });
    }
};
