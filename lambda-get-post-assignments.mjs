/**
 * AWS Lambda function for assigning posts to participants
 * 
 * Delegates to https://github.com/METResearchGroup/study_participant_assignment_interface
 * to get post assignments.
 */

import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const lambdaClient = new LambdaClient({ region: "us-east-2" });
const validPoliticalParties = ['democrat', 'republican'];

// TODO: this should be provided via environment variable
const STUDY_ITERATION_ID = process.env.STUDY_ITERATION_ID;
const STUDY_ID = process.env.STUDY_ID;
const ASSIGNMENT_LAMBDA_NAME = process.env.ASSIGNMENT_LAMBDA_NAME;

/**
 * Validate the inputs
 * @param {Object} inputs - The inputs to validate
 * @returns {void}
 */
function validateInputs(
    prolificId,
    partyGroup
) {
    if (!prolificId) {
        throw new Error('No prolific_id provided');
    }
    if (!partyGroup) {
        throw new Error('No party_group provided');
    }
    if (!validPoliticalParties.includes(partyGroup)) {
        throw new Error(`Invalid party_group: ${partyGroup}. Must be one of: ${validPoliticalParties.join(', ')}`);
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
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        body: typeof body === 'string' ? body : JSON.stringify(body)
    }
}

/**
 * Parse the body of the event
 * @param {Object} event - The event object
 * @returns {Object} - The parsed body
 */
function parseBody(event) {
    if (!event.body) {
        throw new Error('No body provided');
    }
    const body = JSON.parse(event.body);
    return body;
}

async function callStudyAssignmentLambda({
    prolificId,
    partyGroup,
    isTest
}) {
    const studyIterationId = STUDY_ITERATION_ID;
    if (isTest) {
        studyIterationId = `dev-${STUDY_ITERATION_ID}`;
        console.log(`Using dev study iteration ID: ${studyIterationId}`);
    } else {
        console.log(`Using study iteration ID: ${studyIterationId}`);
    }

    const payload = {
        study_id: STUDY_ID,
        study_iteration_id: studyIterationId,
        prolific_id: prolificId,
        party_group: partyGroup
    }

    const result = await lambdaClient.send(
        new InvokeCommand({
            FunctionName: ASSIGNMENT_LAMBDA_NAME,
            Payload: JSON.stringify(payload)
        })
    );

    // InvokeCommand does not give you a JavaScript string in result.Payload.
    // It gives you raw bytes. We need to decode first.
    if (result.FunctionError) {
        const errorPayload = result.Payload ? JSON.parse(result.Payload) : null;
        const errorMessage = errorPayload?.error || 'Unknown error';
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
        !["control", "training_assisted"].includes(parsed.condition)
    ) {
        throw new Error(`Unexpected assignment response: ${decoded}`);
    }

    return parsed;
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
        const partyGroup = body.party_group;
        const isTest = body.is_test;

        validateInputs(prolificId, partyGroup);

        const assignment = await callStudyAssignmentLambda({
            prolificId,
            partyGroup,
            isTest: isTest
        });

        return corsResponse(200, {
            assigned_post_ids: assignment.assigned_post_ids,
            already_assigned: assignment.already_assigned,
            condition: assignment.condition,
            is_test: isTest,
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
