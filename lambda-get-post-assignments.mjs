/**
 * AWS Lambda function for assigning posts to participants
 * 
 * Delegates to https://github.com/METResearchGroup/study_participant_assignment_interface
 * to get post assignments.
 */

import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const lambdaClient = new LambdaClient({ region: "us-east-2" });

const ASSIGNMENT_LAMBDA_NAME = process.env.ASSIGNMENT_LAMBDA_NAME;

const STUDY_SPEC = Object.freeze({
    conditions: ['control', 'training', 'training_assisted'],
    validPoliticalParties: ['democrat', 'republican'],
});

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
        throw new Error('No prolificId provided');
    }
    if (!partyGroup) {
        throw new Error('No partyGroup provided');
    }
    if (!STUDY_SPEC.validPoliticalParties.includes(partyGroup)) {
        throw new Error(`Invalid partyGroup: ${partyGroup}. Must be one of: ${STUDY_SPEC.validPoliticalParties.join(', ')}`);
    }
    if (!studyId) {
        throw new Error('No STUDY_ID provided');
    }
    if (!studyIterationId) {
        throw new Error('No STUDY_ITERATION_ID provided');
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
    isTest,
    studyId,
    studyIterationId
}) {
    let effectiveStudyIterationId = studyIterationId;
    if (isTest) {
        effectiveStudyIterationId = `dev-${studyIterationId}`;
        console.log(`Using dev study iteration ID: ${effectiveStudyIterationId}`);
    } else {
        console.log(`Using study iteration ID: ${effectiveStudyIterationId}`);
    }

    const payload = {
        study_id: studyId,
        study_iteration_id: effectiveStudyIterationId,
        prolificId: prolificId,
        partyGroup: partyGroup
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
        !Array.isArray(parsed.assignedPostIds) ||
        !STUDY_SPEC.conditions.includes(parsed.condition)
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
