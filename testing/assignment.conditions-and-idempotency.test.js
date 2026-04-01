/* Testing how conditions are assigned and how to validate user idempotency.

- Returns 400 for missing Prolific ID.

*/

const test = require('node:test');
const assert = require('node:assert/strict');
const {
    CONDITIONS,
    PROD_ASSIGNMENTS_KEY,
    PROD_PENDING_KEY,
    TEST_ASSIGNMENTS_KEY,
    TEST_PENDING_KEY,
    buildCatalog,
    makePosts,
    createAssignments,
    createParticipant,
    loadGetAssignmentsHandler,
    invokeGetAssignments,
} = require('./assignment-test-helpers.js');

test('returns 400 for missing prolific_id', async () => {
    const { handler } = await loadGetAssignmentsHandler();
    const response = await invokeGetAssignments(handler, {
        party_group: 'democrat',
        all_posts: buildCatalog(),
    });

    assert.equal(response.statusCode, 400);
    assert.equal(response.json.error, 'Missing prolific_id');
});

test('reuses pending assignment for the same participant', async () => {
    const catalog = buildCatalog();
    const { handler, store } = await loadGetAssignmentsHandler({
        [PROD_ASSIGNMENTS_KEY]: createAssignments(),
        [PROD_PENDING_KEY]: {},
    });

    const firstResponse = await invokeGetAssignments(handler, {
        prolific_id: 'P1',
        party_group: 'democrat',
        all_posts: catalog,
    });

    assert.equal(firstResponse.statusCode, 200);
    assert.equal(firstResponse.json.already_assigned, false);
    assert.equal(firstResponse.json.assigned_post_ids.length, 20);

    const storedPending = JSON.parse(store.get(PROD_PENDING_KEY));
    assert.deepEqual(
        storedPending.P1.posts.map((post) => post.post_id),
        firstResponse.json.assigned_post_ids
    );

    const secondResponse = await invokeGetAssignments(handler, {
        prolific_id: 'P1',
        party_group: 'democrat',
        all_posts: catalog,
    });

    assert.equal(secondResponse.statusCode, 200);
    assert.equal(secondResponse.json.already_assigned, true);
    assert.deepEqual(secondResponse.json.assigned_post_ids, firstResponse.json.assigned_post_ids);
    assert.equal(secondResponse.json.condition, firstResponse.json.condition);
});

test('reuses committed assignment for the same participant', async () => {
    const committedPosts = makePosts('committed');
    const { handler } = await loadGetAssignmentsHandler({
        [PROD_ASSIGNMENTS_KEY]: createAssignments({
            P1: createParticipant({
                party: 'democrat',
                condition: 'control',
                posts: committedPosts,
            }),
        }),
        [PROD_PENDING_KEY]: {},
    });

    const response = await invokeGetAssignments(handler, {
        prolific_id: 'P1',
        party_group: 'democrat',
        all_posts: buildCatalog(),
    });

    assert.equal(response.statusCode, 200);
    assert.equal(response.json.already_assigned, true);
    assert.equal(response.json.condition, 'control');
    assert.deepEqual(
        response.json.assigned_post_ids,
        committedPosts.map((post) => post.post_id)
    );
});

test('balances conditions within party using committed and pending counts', async () => {
    const { handler } = await loadGetAssignmentsHandler({
        [PROD_ASSIGNMENTS_KEY]: createAssignments({
            D_CONTROL_1: createParticipant({ party: 'democrat', condition: 'control' }),
            D_CONTROL_2: createParticipant({ party: 'democrat', condition: 'control' }),
            D_CONTROL_3: createParticipant({ party: 'democrat', condition: 'control' }),
            D_CONTROL_4: createParticipant({ party: 'democrat', condition: 'control' }),
            D_CONTROL_5: createParticipant({ party: 'democrat', condition: 'control' }),
            D_TRAIN_1: createParticipant({ party: 'democrat', condition: 'training' }),
            D_TRAIN_2: createParticipant({ party: 'democrat', condition: 'training' }),
            D_TRAIN_3: createParticipant({ party: 'democrat', condition: 'training' }),
            D_ASSIST_1: createParticipant({ party: 'democrat', condition: 'training_assisted' }),
            D_ASSIST_2: createParticipant({ party: 'democrat', condition: 'training_assisted' }),
            D_ASSIST_3: createParticipant({ party: 'democrat', condition: 'training_assisted' }),
            R_CONTROL_1: createParticipant({ party: 'republican', condition: 'control' }),
            R_TRAIN_1: createParticipant({ party: 'republican', condition: 'training' }),
            R_ASSIST_1: createParticipant({ party: 'republican', condition: 'training_assisted' }),
        }),
        [PROD_PENDING_KEY]: {
            D_PENDING_TRAIN: {
                party: 'democrat',
                condition: 'training',
                posts: [],
                assigned_at: '2026-04-01T00:00:00.000Z',
            },
        },
    });

    const response = await invokeGetAssignments(handler, {
        prolific_id: 'P_BALANCE',
        party_group: 'democrat',
        all_posts: buildCatalog(),
    });

    assert.equal(response.statusCode, 200);
    assert.equal(response.json.already_assigned, false);
    assert.equal(response.json.condition, 'training_assisted');
});

test('honors condition override only for test participants', async () => {
    const catalog = buildCatalog();
    const { handler } = await loadGetAssignmentsHandler({
        [PROD_ASSIGNMENTS_KEY]: createAssignments({
            D_ASSIST_1: createParticipant({ party: 'democrat', condition: 'training_assisted' }),
        }),
        [PROD_PENDING_KEY]: {},
        [TEST_ASSIGNMENTS_KEY]: createAssignments(),
        [TEST_PENDING_KEY]: {},
    });

    const productionResponse = await invokeGetAssignments(handler, {
        prolific_id: 'REAL_PROLIFIC_1',
        party_group: 'democrat',
        condition: 'training_assisted',
        is_test: false,
        all_posts: catalog,
    });

    const testResponse = await invokeGetAssignments(handler, {
        prolific_id: 'TEST_1',
        party_group: 'democrat',
        condition: 'training_assisted',
        is_test: true,
        all_posts: catalog,
    });

    assert.equal(productionResponse.statusCode, 200);
    assert.equal(testResponse.statusCode, 200);
    assert.notEqual(productionResponse.json.condition, 'training_assisted');
    assert.ok(CONDITIONS.includes(productionResponse.json.condition));
    assert.equal(testResponse.json.condition, 'training_assisted');
    assert.equal(testResponse.json.is_test, true);
});
