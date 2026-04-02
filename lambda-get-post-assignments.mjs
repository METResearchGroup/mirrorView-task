/**
 * AWS Lambda function for assigning posts to participants
 * 
 * This function manages post assignments to ensure each post gets rated by
 * exactly 3 democrats and 3 republicans (6 total).
 * 
 * Uses S3 to store assignment data (same pattern as other Lambda functions).
 */

import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-2" });

// Configuration - matches existing setup
// const BUCKET_NAME = 'jspsych-mirror-view';
const BUCKET_NAME = 'jspsych-mirror-view-2';
const POST_ASSIGNMENTS_FILE = 'data/prolific/post_assignments.json';
const POST_ASSIGNMENTS_TEST_FILE = 'data/test/post_assignments.json';
const PENDING_ASSIGNMENTS_FILE = 'data/prolific/pending_assignments.json';
const PENDING_ASSIGNMENTS_TEST_FILE = 'data/test/pending_assignments.json';
const POST_CATALOG_KEY = 'img/all_mirrors_claude.csv';

const NUM_POSTS_PER_PARTICIPANT = 20;
const CONDITIONS = ['control', 'training', 'training_assisted'];
const CATEGORY_ORDER = [
    'left__sample_low_toxicity',
    'left__sample_high_toxicity',
    'left__sample_middle_toxicity',
    'right__sample_low_toxicity',
    'right__sample_high_toxicity',
    'right__sample_middle_toxicity'
];

let cachedPostCatalog = null;

function parseCSV(csvText) {
    const rows = [];
    const headers = [];
    let currentRow = [];
    let currentField = '';
    let inQuotes = false;
    let isFirstRow = true;

    for (let i = 0; i < csvText.length; i++) {
        const char = csvText[i];
        const nextChar = csvText[i + 1];

        if (inQuotes) {
            if (char === '"') {
                if (nextChar === '"') {
                    currentField += '"';
                    i++;
                } else {
                    inQuotes = false;
                }
            } else {
                currentField += char;
            }
        } else {
            if (char === '"') {
                inQuotes = true;
            } else if (char === ',') {
                currentRow.push(currentField);
                currentField = '';
            } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
                if (char === '\r') i++;
                currentRow.push(currentField);
                currentField = '';

                if (isFirstRow) {
                    headers.push(...currentRow);
                    isFirstRow = false;
                } else if (currentRow.length > 0 && currentRow.some(f => f.trim() !== '')) {
                    const rowObj = {};
                    headers.forEach((header, idx) => {
                        rowObj[header] = currentRow[idx] || '';
                    });
                    rows.push(rowObj);
                }
                currentRow = [];
            } else if (char !== '\r') {
                currentField += char;
            }
        }
    }

    if (currentField !== '' || currentRow.length > 0) {
        currentRow.push(currentField);
        if (currentRow.length > 0 && currentRow.some(f => f.trim() !== '')) {
            const rowObj = {};
            headers.forEach((header, idx) => {
                rowObj[header] = currentRow[idx] || '';
            });
            rows.push(rowObj);
        }
    }

    return rows;
}

async function getPostCatalog() {
    if (cachedPostCatalog && cachedPostCatalog.length > 0) {
        return cachedPostCatalog;
    }

    const data = await s3Client.send(new GetObjectCommand({
        Bucket: BUCKET_NAME,
        Key: POST_CATALOG_KEY
    }));
    const csvText = await data.Body.transformToString();
    const parsed = parseCSV(csvText);
    cachedPostCatalog = parsed
        .filter(row => row.post_primary_key && row.post_number)
        .map(row => ({
            post_id: row.post_primary_key,
            post_number: row.post_number,
            sampled_stance: row.sampled_stance,
            sample_toxicity_type: row.sample_toxicity_type
        }));

    return cachedPostCatalog;
}


function parseInputs(event) {
    let body;
    if (typeof event.body === 'string') {
        body = JSON.parse(event.body);
    } else {
        body = event.body || {};
    }

    const { prolific_id, party_group, condition, all_posts, is_test } = body;

    if (!prolific_id) {
        return corsResponse(400, { error: 'Missing prolific_id' });
    }

    if (!party_group || !['democrat', 'republican'].includes(party_group)) {
        return corsResponse(400, { error: 'Invalid party_group. Must be "democrat" or "republican"' });
    }

    const inferredTest = getIsTestFlag(prolific_id);

    if (is_test == null) {
        is_test = inferredTest;
    } else {
        // if is_test is False, we want to use the inferredTest flag.
        is_test = is_test ?? inferredTest;
    }

    return { prolific_id, party_group, condition, all_posts, is_test };
}

/*
 * Get the post pool for the assignment.
 * @param {Array} all_posts - The list of all posts to choose from.
 * @returns {Array} - The post pool.
 */
async function getPostPool(all_posts) {
    let postPool = Array.isArray(all_posts) && all_posts.length > 0 ? all_posts : null;
    if (!postPool) {
        postPool = await getPostCatalog();
    }
    if (!postPool || postPool.length === 0) {
        return corsResponse(400, { error: 'No posts available for assignment' });
    }
}


/*
 * Load assignments from S3.
 * @param {string} assignmentKey - The key to load the assignments from.
 * @returns {Object} - The loaded assignments.
 */
async function loadAssignmentsFromS3(assignmentKey) {
    let loadedAssignments;
    try {
        const data = await s3Client.send(new GetObjectCommand({
            Bucket: BUCKET_NAME,
            Key: assignmentKey
        }));
        loadedAssignments = JSON.parse(await data.Body.transformToString());
        console.log(`Loaded ${Object.keys(loadedAssignments.posts || {}).length} post assignments`);
    } catch (error) {
        if (error.name === 'NoSuchKey') {
            loadedAssignments = {}
            console.log(`Created new post assignments file: ${assignmentKey}`);
        } else {
            console.error('Error reading post assignments from S3:', error);
            throw error;
        }
    }
    return loadedAssignments
}


/* Set default assignments if the file doesn't exist. 
 * @returns {Object} - The default assignments.
 */
function setDefaultAssignments() {
    return {
        posts: {},
        participants: {}
    }
}

/*
 * Load committed assignments from S3.
 * @param {string} assignmentKey - The key to load the assignments from.
 * @returns {Object} - The loaded assignments.
 */
function loadCommitedAssignmentsFromS3(assignmentKey) {
    let loadedAssignments = loadAssignmentsFromS3(assignmentKey);
    if (loadedAssignments && Object.keys(loadedAssignments).length === 0) {
        loadedAssignments = setDefaultAssignments();
    }
    return loadedAssignments;
}

/*
 * Load pending assignments from S3.
 * @param {string} pendingKey - The key to load the assignments from.
 * @returns {Object} - The loaded assignments.
 */
function loadPendingAssignmentsFromS3(pendingKey) {
    let loadedPendingAssignments = loadAssignmentsFromS3(pendingKey);
    if (loadedPendingAssignments && Object.keys(loadedPendingAssignments).length === 0) {
        loadedPendingAssignments = {};
    }
    return loadedPendingAssignments;
}


function getIsTestFlag(prolific_id) {
    return (typeof prolific_id === 'string' && (prolific_id.startsWith('UNKNOWN_') || prolific_id.startsWith('TEST_')));
}

/* 
 * Get the correct S3 keys for the assignments, based on if we're in test mode or not.
 * @param {boolean} is_test - Whether we're running in test mode.
 * @returns {Object} - An object with the assignment and pending keys.
 */
function getAssignmentKeys(is_test) {
    return {
        assignmentKey: is_test ? POST_ASSIGNMENTS_TEST_FILE : POST_ASSIGNMENTS_FILE,
        pendingKey: is_test ? PENDING_ASSIGNMENTS_TEST_FILE : PENDING_ASSIGNMENTS_FILE
    };
}


export const handler = async (event) => {
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return corsResponse(200, '');
    }

    try {
        const { prolific_id, party_group, condition, all_posts, is_test } = parseInputs(event);
        let postPool = await getPostPool(all_posts);

        // get the correct S3 keys for the assignments, based on if we're in test mode or not.
        const { assignmentKey, pendingKey } = getAssignmentKeys(is_test);

        // Read current assignments from S3
        let assignments = loadCommitedAssignmentsFromS3(assignmentKey);

        // Read pending assignments
        let pendingAssignments = loadPendingAssignmentsFromS3(pendingKey);

        // Check if participant already has completed assignments
        if (assignments.participants[prolific_id] && assignments.participants[prolific_id].posts) {
            const existingPosts = assignments.participants[prolific_id].posts;
            const postIds = existingPosts.map(p => p.post_id || p);
            if (postIds.length >= NUM_POSTS_PER_PARTICIPANT) {
                console.log(`Returning existing assignment for ${prolific_id}`);
                return corsResponse(200, {
                    assigned_post_ids: postIds,
                    already_assigned: true,
                    condition: assignments.participants[prolific_id].condition || CONDITIONS[0],
                    is_test: is_test
                });
            }
        }

        // Check pending assignments
        const pending = pendingAssignments[prolific_id];
        if (pending && pending.posts) {
            return corsResponse(200, {
                assigned_post_ids: pending.posts.map(p => p.post_id || p),
                already_assigned: true,
                condition: pending.condition || CONDITIONS[0],
                is_test: is_test
            });
        }

        const requestedCondition = CONDITIONS.includes(String(condition || '').trim()) ? String(condition).trim() : null;
        let assignedCondition;
        if (is_test && requestedCondition) {
            assignedCondition = requestedCondition;
        } else {
            // Assign condition globally with pending-aware balancing to prevent drift
            // during concurrent sign-ups.
            const totalCompleted = Object.keys(assignments.participants || {}).length;
            const totalPending = Object.keys(pendingAssignments || {}).length;
            const totalCommitted = totalCompleted + totalPending;

            const allowedConditions = CONDITIONS;

            // Count both completed and pending:
            // - party-aware counts (primary): balance control/training within this party_group
            // - global counts (tie-break): avoid systematic drift overall
            const partyConditionCounts = {};
            const globalConditionCounts = {};
            allowedConditions.forEach(c => {
                partyConditionCounts[c] = 0;
                globalConditionCounts[c] = 0;
            });

            // Completed history
            Object.values(assignments.participants || {}).forEach(p => {
                if (!p) return;
                if (!allowedConditions.includes(p.condition)) return;
                globalConditionCounts[p.condition] += 1;
                if (p.party !== party_group) return;
                partyConditionCounts[p.condition] += 1;
            });

            // Pending in-flight reservations
            Object.values(pendingAssignments || {}).forEach(pending => {
                if (!pending) return;
                if (!allowedConditions.includes(pending.condition)) return;
                globalConditionCounts[pending.condition] += 1;
                if (pending.party !== party_group) return;
                partyConditionCounts[pending.condition] += 1;
            });

            // Primary: balance within this party_group
            const minPartyCount = Math.min(...allowedConditions.map(c => partyConditionCounts[c] ?? 0));
            const partyCandidates = allowedConditions.filter(c => (partyConditionCounts[c] ?? 0) === minPartyCount);

            if (partyCandidates.length === 1) {
                assignedCondition = partyCandidates[0];
            } else {
                // Tie-break: balance globally
                const minGlobalCount = Math.min(...partyCandidates.map(c => globalConditionCounts[c] ?? 0));
                const globalCandidates = partyCandidates.filter(c => (globalConditionCounts[c] ?? 0) === minGlobalCount);
                assignedCondition = globalCandidates[totalCommitted % globalCandidates.length];
            }
        }

        // Find available posts
        const availablePosts = postPool;

        const testNote = is_test ? ' [test]' : '';
        console.log(`Available posts for ${party_group}: ${availablePosts.length}/${postPool.length}${testNote}`);

        const sortedPosts = [...availablePosts].sort((a, b) => Number(a.post_number) - Number(b.post_number));
        const completedInCondition = Object.values(assignments.participants || {})
            .filter(participant => participant?.condition === assignedCondition)
            .length;
        const startOffset = completedInCondition % CATEGORY_ORDER.length;

        const getCategoryKey = (post) => {
            const stance = String(post.sampled_stance || '').trim().toLowerCase();
            const tox = String(post.sample_toxicity_type || '').trim().toLowerCase();
            const key = `${stance}__${tox}`;
            return CATEGORY_ORDER.includes(key) ? key : null;
        };

        /**
         * Reorder selected posts so that the first half and second half have:
         * - balanced stance counts (left/right as even as possible)
         * - balanced toxicity counts (low/high/middle as even as possible)
         * - less stance clustering (avoid long left-left... runs)
         *
         * This only changes the order of `assigned_post_ids` (which the client slices
         * into phase 1 vs phase 2). It does not change which posts are assigned.
         */
        const reorderPostsForPhaseBalance = (posts, phaseSize) => {
            if (!Array.isArray(posts) || posts.length !== phaseSize * 2) return posts;

            const normalizeStance = (p) => String(p.sampled_stance || '').trim().toLowerCase();
            const normalizeTox = (p) => String(p.sample_toxicity_type || '').trim().toLowerCase();

            const countTotals = (arr) => {
                const totals = {
                    left: 0,
                    right: 0,
                    sample_low_toxicity: 0,
                    sample_high_toxicity: 0,
                    sample_middle_toxicity: 0
                };
                for (const p of arr) {
                    const stance = normalizeStance(p);
                    if (stance === 'left') totals.left += 1;
                    else if (stance === 'right') totals.right += 1;

                    const tox = normalizeTox(p);
                    if (tox in totals) totals[tox] += 1;
                }
                return totals;
            };

            const totals = countTotals(posts);

            // Allowed per-half counts are floor/ceil splits of the totals.
            const allowedCounts = (total) => {
                const a = Math.floor(total / 2);
                const b = Math.ceil(total / 2);
                return Array.from(new Set([a, b]));
            };

            const allowedLeft = allowedCounts(totals.left);
            const allowedToxMid = allowedCounts(totals.sample_middle_toxicity);
            const allowedToxLow = allowedCounts(totals.sample_low_toxicity);
            const allowedToxHigh = allowedCounts(totals.sample_high_toxicity);

            const shuffleInPlace = (arr) => {
                for (let i = arr.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [arr[i], arr[j]] = [arr[j], arr[i]];
                }
                return arr;
            };

            const maxRun = (seq) => {
                let best = 1;
                let cur = 1;
                for (let i = 1; i < seq.length; i++) {
                    if (seq[i] === seq[i - 1]) {
                        cur += 1;
                        best = Math.max(best, cur);
                    } else {
                        cur = 1;
                    }
                }
                return best;
            };

            const transitions = (seq) => {
                let t = 0;
                for (let i = 1; i < seq.length; i++) {
                    if (seq[i] !== seq[i - 1]) t += 1;
                }
                return t;
            };

            const isValid = (half) => {
                if (half.length !== phaseSize) return false;
                const c = countTotals(half);

                // Balance stance and toxicity as evenly as possible.
                if (!allowedLeft.includes(c.left)) return false;
                if (c.left + c.right !== phaseSize) return false;
                if (!allowedToxMid.includes(c.sample_middle_toxicity)) return false;
                if (!allowedToxLow.includes(c.sample_low_toxicity)) return false;
                if (!allowedToxHigh.includes(c.sample_high_toxicity)) return false;

                // Sanity: toxicity + stance should fully account for the half.
                const toxSum = c.sample_low_toxicity + c.sample_high_toxicity + c.sample_middle_toxicity;
                if (toxSum !== phaseSize) return false;

                // Avoid heavy clustering of the same stance.
                const stanceSeq = half.map(p => normalizeStance(p));
                const run = maxRun(stanceSeq);
                const trans = transitions(stanceSeq);

                // Two-tier constraints: prefer interleaving, but relax if needed.
                // (With 5/5, max run <= 3 eliminates the obvious "all left then all right" pattern.)
                // Avoid the specific failure mode you saw: long left-left-left-left streaks.
                if (run > 3) return false;
                if (trans < 3) return false;

                return true;
            };

            const tryBudget = 800;
            for (let attempt = 0; attempt < tryBudget; attempt++) {
                const candidate = shuffleInPlace(posts.slice());
                const p1 = candidate.slice(0, phaseSize);
                const p2 = candidate.slice(phaseSize);

                if (isValid(p1) && isValid(p2)) {
                    return candidate;
                }
            }

            // Fallback: at least shuffle to remove the deterministic stance clustering.
            return shuffleInPlace(posts.slice());
        };

        // Count condition exposure per *party* for this participant request.
        // We compute this from `assignments.participants` (which is party-aware),
        // so we can enforce "at most once per (party, condition, post)" without
        // relying on non-party-specific counters in `assignments.posts`.
        const conditionCountByPostId = new Map();
        const participantsObj = assignments.participants || {};
        Object.values(participantsObj).forEach(participant => {
            if (!participant) return;
            if (participant.party !== party_group) return;
            if (participant.condition !== assignedCondition) return;
            const postsArr = participant.posts || [];
            postsArr.forEach(p => {
                const postId = p?.post_id || p;
                if (!postId) return;
                conditionCountByPostId.set(postId, (conditionCountByPostId.get(postId) || 0) + 1);
            });
        });

        // Also count *pending* assignments so we don't hand out the same
        // (party, condition, post) cell to multiple participants while earlier
        // ones are still in-flight.
        Object.values(pendingAssignments || {}).forEach(pending => {
            if (!pending) return;
            if (pending.party !== party_group) return;
            if (pending.condition !== assignedCondition) return;
            const postsArr = pending.posts || [];
            postsArr.forEach(p => {
                const postId = p?.post_id || p;
                if (!postId) return;
                conditionCountByPostId.set(postId, (conditionCountByPostId.get(postId) || 0) + 1);
            });
        });
        const getConditionCount = (post) => conditionCountByPostId.get(post.post_id) || 0;

        const selectedPosts = [];
        const selectedIds = new Set();
        const rotatedOrder = CATEGORY_ORDER.map((_, i) => CATEGORY_ORDER[(startOffset + i) % CATEGORY_ORDER.length]);
        const orderRank = new Map(rotatedOrder.map((k, i) => [k, i]));
        const TOXICITY_ORDER = ['sample_low_toxicity', 'sample_high_toxicity', 'sample_middle_toxicity'];
        const rotatedToxicityOrder = TOXICITY_ORDER.map((_, i) => TOXICITY_ORDER[(completedInCondition + i) % TOXICITY_ORDER.length]);

        const allocateByWeights = (total, keys, weightLookup, tieLookup) => {
            const safeKeys = keys.filter(k => (weightLookup[k] || 0) > 0);
            if (total <= 0 || safeKeys.length === 0) {
                const empty = {};
                keys.forEach(k => { empty[k] = 0; });
                return empty;
            }

            const totalWeight = safeKeys.reduce((sum, k) => sum + (weightLookup[k] || 0), 0);
            const allocation = {};
            const remainders = [];
            let assigned = 0;

            keys.forEach(k => {
                if (!safeKeys.includes(k)) {
                    allocation[k] = 0;
                    return;
                }
                const raw = (total * (weightLookup[k] || 0)) / totalWeight;
                const base = Math.floor(raw);
                allocation[k] = base;
                assigned += base;
                remainders.push({ key: k, remainder: raw - base, tie: tieLookup.get(k) ?? 0 });
            });

            let remaining = total - assigned;
            remainders.sort((a, b) => {
                if (b.remainder !== a.remainder) return b.remainder - a.remainder;
                return a.tie - b.tie;
            });
            for (let i = 0; i < remaining; i++) {
                const target = remainders[i % remainders.length];
                allocation[target.key] = (allocation[target.key] || 0) + 1;
            }
            return allocation;
        };

        const catalogCountsByCell = {};
        CATEGORY_ORDER.forEach(k => { catalogCountsByCell[k] = 0; });
        const catalogCountsByToxicity = {};
        TOXICITY_ORDER.forEach(k => { catalogCountsByToxicity[k] = 0; });
        sortedPosts.forEach(post => {
            const key = getCategoryKey(post);
            if (key) {
                catalogCountsByCell[key] += 1;
                const tox = String(post.sample_toxicity_type || '').trim().toLowerCase();
                if (TOXICITY_ORDER.includes(tox)) {
                    catalogCountsByToxicity[tox] += 1;
                }
            }
        });

        const toxicityTieLookup = new Map(rotatedToxicityOrder.map((k, i) => [k, i]));
        const targetByToxicity = allocateByWeights(
            NUM_POSTS_PER_PARTICIPANT,
            TOXICITY_ORDER,
            catalogCountsByToxicity,
            toxicityTieLookup
        );

        const targetByCell = {};
        CATEGORY_ORDER.forEach(k => { targetByCell[k] = 0; });
        TOXICITY_ORDER.forEach((tox, toxIndex) => {
            const leftKey = `left__${tox}`;
            const rightKey = `right__${tox}`;
            const splitKeys = [leftKey, rightKey].filter(k => CATEGORY_ORDER.includes(k));
            const splitTieOrder = (toxIndex + startOffset) % 2 === 0 ? [leftKey, rightKey] : [rightKey, leftKey];
            const splitTieLookup = new Map(splitTieOrder.map((k, i) => [k, i]));
            const splitCounts = allocateByWeights(
                targetByToxicity[tox] || 0,
                splitKeys,
                catalogCountsByCell,
                splitTieLookup
            );
            splitKeys.forEach(k => {
                targetByCell[k] = splitCounts[k] || 0;
            });
        });

        const unseenBuckets = {};
        const seenBuckets = {};
        const selectedCountByCell = {};
        CATEGORY_ORDER.forEach(k => {
            unseenBuckets[k] = [];
            seenBuckets[k] = [];
            selectedCountByCell[k] = 0;
        });
        sortedPosts.forEach(post => {
            const key = getCategoryKey(post);
            if (!key) return;
            if (getConditionCount(post) === 0) {
                unseenBuckets[key].push(post);
            }
        });

        rotatedOrder.forEach(key => {
            const target = targetByCell[key] || 0;
            while (selectedPosts.length < NUM_POSTS_PER_PARTICIPANT && selectedCountByCell[key] < target) {
                const unseen = unseenBuckets[key];
                if (!unseen || unseen.length === 0) break;
                const post = unseen.shift();
                if (!selectedIds.has(post.post_id)) {
                    selectedIds.add(post.post_id);
                    selectedPosts.push(post);
                    selectedCountByCell[key] += 1;
                }
            }
        });

        // Fix deterministic stance clustering across phase boundaries by reordering.
        // Client assigns phase 1 to indices 0..TRIALS_PER_PHASE-1 and phase 2 to the rest.
        const phaseSize = Math.floor(NUM_POSTS_PER_PARTICIPANT / 2);
        if (selectedPosts.length === phaseSize * 2) {
            const ordered = reorderPostsForPhaseBalance(selectedPosts, phaseSize);
            if (Array.isArray(ordered) && ordered.length === selectedPosts.length) {
                selectedPosts.splice(0, selectedPosts.length, ...ordered);
            }
        }

        const shortAssignment = selectedPosts.length < NUM_POSTS_PER_PARTICIPANT;

        pendingAssignments[prolific_id] = {
            party: party_group,
            condition: assignedCondition,
            posts: selectedPosts.map(p => ({ post_id: p.post_id, post_number: p.post_number })),
            assigned_at: new Date().toISOString()
        };

        await s3Client.send(new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: pendingKey,
            Body: JSON.stringify(pendingAssignments, null, 2),
            ContentType: 'application/json'
        }));

        const shortNote = shortAssignment ? ' (short assignment)' : '';
        console.log(`Assigned ${selectedPosts.length} posts to ${prolific_id} (${party_group}, ${assignedCondition})${shortNote}${testNote}: ${selectedPosts.map(p => p.post_number).join(', ')}`);

        return corsResponse(200, {
            assigned_post_ids: selectedPosts.map(p => p.post_id),
            already_assigned: false,
            short_assignment: shortAssignment,
            condition: assignedCondition,
            is_test: is_test
        });

    } catch (error) {
        console.error('Error processing request:', error);
        return corsResponse(500, { error: 'Internal server error', message: error.message });
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
