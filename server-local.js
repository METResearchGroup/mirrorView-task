const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3000;

// ============================================================
// DATA PERSISTENCE
// ============================================================

const DATA_DIR = path.join(__dirname, 'local_data');
const PROLIFIC_DIR = path.join(DATA_DIR, 'prolific');
const TEST_DIR = path.join(DATA_DIR, 'test');
const POST_ASSIGNMENTS_FILE = path.join(PROLIFIC_DIR, 'post_assignments.json');
const POST_ASSIGNMENTS_LOCAL_FILE = path.join(TEST_DIR, 'post_assignments.json');
const PARTICIPANT_ASSIGNMENTS_FILE = path.join(PROLIFIC_DIR, 'participant_assignments.json');
const PARTICIPANT_ASSIGNMENTS_LOCAL_FILE = path.join(TEST_DIR, 'participant_assignments.json');
const PENDING_ASSIGNMENTS_FILE = path.join(PROLIFIC_DIR, 'pending_assignments.json');
const PENDING_ASSIGNMENTS_LOCAL_FILE = path.join(TEST_DIR, 'pending_assignments.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}
if (!fs.existsSync(PROLIFIC_DIR)) {
    fs.mkdirSync(PROLIFIC_DIR, { recursive: true });
}
if (!fs.existsSync(TEST_DIR)) {
    fs.mkdirSync(TEST_DIR, { recursive: true });
}

function loadJsonFile(filePath, fallback) {
    if (!fs.existsSync(filePath)) return fallback;
    try {
        return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (e) {
        console.error(`Error loading ${path.basename(filePath)}:`, e);
        return fallback;
    }
}

function createEmptyParticipantAssignments() {
    return {
        democrat: { count: 0, assignments: {} },
        republican: { count: 0, assignments: {} }
    };
}

// Load or initialize post assignments
// Structure: { "post_id": { post_number, counts: { control, training, training_assisted } }, ... }
let postAssignments = loadJsonFile(POST_ASSIGNMENTS_FILE, {});
let postAssignmentsLocal = loadJsonFile(POST_ASSIGNMENTS_LOCAL_FILE, {});
console.log(`Loaded ${Object.keys(postAssignments).length} post assignments from file`);
console.log(`Loaded ${Object.keys(postAssignmentsLocal).length} local post assignments from file`);

// Load or initialize participant assignments
let participantAssignments = loadJsonFile(
    PARTICIPANT_ASSIGNMENTS_FILE,
    createEmptyParticipantAssignments()
);
let participantAssignmentsLocal = loadJsonFile(
    PARTICIPANT_ASSIGNMENTS_LOCAL_FILE,
    createEmptyParticipantAssignments()
);
console.log('Loaded participant assignments from file');
console.log('Loaded local participant assignments from file');

// Load or initialize pending assignments
let pendingAssignments = loadJsonFile(PENDING_ASSIGNMENTS_FILE, {});
let pendingAssignmentsLocal = loadJsonFile(PENDING_ASSIGNMENTS_LOCAL_FILE, {});
console.log('Loaded pending assignments from file');

// Save functions
function savePostAssignments(assignments, isTest) {
    const target = isTest ? POST_ASSIGNMENTS_LOCAL_FILE : POST_ASSIGNMENTS_FILE;
    fs.writeFileSync(target, JSON.stringify(assignments, null, 2));
}

function saveParticipantAssignments(assignments, isTest) {
    const target = isTest ? PARTICIPANT_ASSIGNMENTS_LOCAL_FILE : PARTICIPANT_ASSIGNMENTS_FILE;
    fs.writeFileSync(target, JSON.stringify(assignments, null, 2));
}

function savePendingAssignments(assignments, isTest) {
    const target = isTest ? PENDING_ASSIGNMENTS_LOCAL_FILE : PENDING_ASSIGNMENTS_FILE;
    fs.writeFileSync(target, JSON.stringify(assignments, null, 2));
}

function getAssignmentContext({ prolificID, isTest }) {
    const inferredTest = isTest === true
        || (typeof prolificID === 'string' && (prolificID.startsWith('TEST_') || prolificID.startsWith('UNKNOWN_')));
    return {
        isTest: inferredTest,
        postAssignments: inferredTest ? postAssignmentsLocal : postAssignments,
        participantAssignments: inferredTest ? participantAssignmentsLocal : participantAssignments,
        pendingAssignments: inferredTest ? pendingAssignmentsLocal : pendingAssignments
    };
}

// ============================================================
// CONFIGURATION
// ============================================================

const NUM_POSTS_PER_PARTICIPANT = 20;
const CONDITIONS = ['control', 'training', 'training_assisted'];
// Pilot support: for the final 20 participants of the 90-person pilot, we only
// allow control/training to land so that `training_assisted` stops drifting.
const PILOT_TOTAL_TARGET = 90;
const PILOT_NEXT_BATCH_SIZE = 20;
const PILOT_NEXT_BATCH_ONLY_CONTROL_TRAINING_START =
    PILOT_TOTAL_TARGET - PILOT_NEXT_BATCH_SIZE; // e.g. 70 (start restricting)
const POST_CATALOG_FILE = path.join(__dirname, 'public', 'img', 'all_mirrors_claude.csv');
const CATEGORY_ORDER = [
    'left__sample_low_toxicity',
    'left__sample_high_toxicity',
    'left__sample_middle_toxicity',
    'right__sample_low_toxicity',
    'right__sample_high_toxicity',
    'right__sample_middle_toxicity'
];

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

function loadPostCatalog() {
    try {
        const csvText = fs.readFileSync(POST_CATALOG_FILE, 'utf8');
        const parsed = parseCSV(csvText);
        const catalog = parsed
            .filter(row => row.post_primary_key && row.post_number)
            .map(row => ({
                post_id: row.post_primary_key,
                post_number: row.post_number,
                sampled_stance: row.sampled_stance,
                sample_toxicity_type: row.sample_toxicity_type
            }));
        console.log(`Loaded ${catalog.length} posts from catalog`);
        return catalog;
    } catch (error) {
        console.error('Failed to load post catalog:', error);
        return [];
    }
}

let postCatalog = loadPostCatalog();

function makeConditionCounts(existing = {}) {
    return {
        control: Number(existing?.control || 0),
        training: Number(existing?.training || existing?.linked_fate || 0),
        training_assisted: Number(existing?.training_assisted || 0)
    };
}

// ============================================================
// MIDDLEWARE
// ============================================================

app.use(bodyParser.json({ limit: '10mb' }));

// Serve HTML file (local development version) - MUST be before express.static
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index-local.html'));
});

// Static files (after the root route to prevent index.html from being served)
app.use(express.static(path.join(__dirname, 'public')));

// ============================================================
// POST ASSIGNMENT ENDPOINT
// ============================================================

/**
 * Get post assignments for a participant based on their party
 * 
 * Body params:
 *   - prolific_id: The participant's Prolific ID
 *   - party_group: 'democrat' or 'republican'
 *   - all_posts: Optional array fallback (post catalog is loaded server-side)
 * 
 * Returns:
 *   - assigned_post_ids: Array of 5 post IDs to show this participant
 */
app.post('/get-post-assignments', (req, res) => {
    const { prolific_id: prolificID, party_group: partyGroup, condition, all_posts: allPosts, is_test: isTest } = req.body;

    if (!prolificID) {
        return res.status(400).json({ error: 'No prolific_id provided' });
    }

    if (!partyGroup || !['democrat', 'republican'].includes(partyGroup)) {
        return res.status(400).json({ error: 'Invalid party_group. Must be "democrat" or "republican"' });
    }

    const postPool = Array.isArray(allPosts) && allPosts.length > 0 ? allPosts : postCatalog;
    if (!postPool || postPool.length === 0) {
        return res.status(400).json({ error: 'No posts provided' });
    }

    const { postAssignments, participantAssignments, pendingAssignments, isTest: effectiveIsTest } = getAssignmentContext({
        prolificID,
        isTest
    });

    // Check if this participant already completed
    const existingAssignment = participantAssignments[partyGroup]?.assignments?.[prolificID];
    if (existingAssignment && existingAssignment.posts) {
        const existingPostIds = existingAssignment.posts.map(p => p.post_id || p);
        if (existingPostIds.length >= NUM_POSTS_PER_PARTICIPANT) {
            console.log(`Returning existing assignment for ${prolificID}: ${existingPostIds.length} posts`);
            return res.json({
                assigned_post_ids: existingPostIds,
                already_assigned: true,
                condition: existingAssignment.condition || CONDITIONS[0]
            });
        }
    }

    // Check if participant has pending assignment
    const pending = pendingAssignments[prolificID];
    if (pending && pending.posts) {
        return res.json({
            assigned_post_ids: pending.posts.map(p => p.post_id || p),
            already_assigned: true,
            condition: pending.condition || CONDITIONS[0]
        });
    }

    const requestedCondition = CONDITIONS.includes(String(condition || '').trim()) ? String(condition).trim() : null;
    let assignedCondition;
    if (effectiveIsTest && requestedCondition) {
        assignedCondition = requestedCondition;
    } else {
        // Assign condition globally with pending-aware balancing to prevent drift
        // during concurrent sign-ups.
        const totalCompleted = ['democrat', 'republican'].reduce((sum, party) => {
            const assignmentsByParty = participantAssignments[party]?.assignments || {};
            return sum + Object.keys(assignmentsByParty).length;
        }, 0);

        const totalPending = Object.keys(pendingAssignments || {}).length;
        const totalCommitted = totalCompleted + totalPending;

        // Use committed (completed+pending) so we don't keep restricting
        // indefinitely while earlier sign-ups are still in-flight.
        const inPilotTail = totalCommitted >= PILOT_NEXT_BATCH_ONLY_CONTROL_TRAINING_START && totalCommitted < PILOT_TOTAL_TARGET;
        const allowedConditions = inPilotTail ? ['control', 'training'] : CONDITIONS;

        // Count both completed and pending:
        // - party-aware counts (primary): balance control/training within this party_group
        // - global counts (tie-break): avoid systematic drift overall
        const partyConditionCounts = {};
        const globalConditionCounts = {};
        allowedConditions.forEach(c => {
            partyConditionCounts[c] = 0;
            globalConditionCounts[c] = 0;
        });

        // Completed history (party-aware + global)
        for (const party of ['democrat', 'republican']) {
            const assignmentsByParty = participantAssignments[party]?.assignments || {};
            Object.values(assignmentsByParty || {}).forEach(a => {
                if (!a) return;
                if (!allowedConditions.includes(a.condition)) return;

                globalConditionCounts[a.condition] += 1;
                if (party !== partyGroup) return;
                partyConditionCounts[a.condition] += 1;
            });
        }

        // Pending in-flight reservations (party-aware + global)
        Object.values(pendingAssignments || {}).forEach(pending => {
            if (!pending) return;
            if (!allowedConditions.includes(pending.condition)) return;

            globalConditionCounts[pending.condition] += 1;
            const pendingParty = pending?.party_group || pending?.party;
            if (pendingParty !== partyGroup) return;
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

    // Find posts not already assigned to this participant
    const existingPostIds = new Set();
    const availablePosts = postPool.filter(post => !existingPostIds.has(post.post_id));

    console.log(`Available posts for ${partyGroup}: ${availablePosts.length}/${postPool.length} (${assignedCondition})`);

    const neededCount = Math.max(NUM_POSTS_PER_PARTICIPANT - existingPostIds.size, 0);
    const sortedPosts = [...availablePosts].sort((a, b) => Number(a.post_number) - Number(b.post_number));
    const completedInCondition = ['democrat', 'republican'].reduce((sum, party) => {
        const assignmentsByParty = participantAssignments[party]?.assignments || {};
        const partyCount = Object.values(assignmentsByParty).filter(a => a?.condition === assignedCondition).length;
        return sum + partyCount;
    }, 0);
    const startOffset = completedInCondition % CATEGORY_ORDER.length;

    const getCategoryKey = (post) => {
        const stance = String(post.sampled_stance || '').trim().toLowerCase();
        const tox = String(post.sample_toxicity_type || '').trim().toLowerCase();
        const key = `${stance}__${tox}`;
        return CATEGORY_ORDER.includes(key) ? key : null;
    };

    // Count condition exposure per *party* for this participant request.
    // We compute this from `participantAssignments` so we can enforce a strict
    // "at most once per (party, condition, post)" rule without relying on
    // the non-party-specific `post_assignments.json` counters.
    const conditionCountByPostId = new Map();
    const partyAssignments = participantAssignments[partyGroup]?.assignments || {};
    Object.values(partyAssignments).forEach(a => {
        const cond = a?.condition;
        if (cond !== assignedCondition) return;
        const postsArr = a?.posts || [];
        postsArr.forEach(p => {
            const postId = p?.post_id || p;
            if (!postId) return;
            conditionCountByPostId.set(postId, (conditionCountByPostId.get(postId) || 0) + 1);
        });
    });

    // Also include *pending* assignments so we don't hand out the same
    // (party, condition, post) cell to multiple participants while earlier
    // ones are still in-flight.
    Object.values(pendingAssignments || {}).forEach(pending => {
        if (!pending) return;
        const pendingParty = pending?.party_group || pending?.party;
        const pendingCond = pending?.condition;
        if (pendingParty !== partyGroup) return;
        if (pendingCond !== assignedCondition) return;
        const postsArr = pending?.posts || [];
        postsArr.forEach(p => {
            const postId = p?.post_id || p;
            if (!postId) return;
            conditionCountByPostId.set(postId, (conditionCountByPostId.get(postId) || 0) + 1);
        });
    });
    const getConditionCount = (post) => conditionCountByPostId.get(post.post_id) || 0;

    /**
     * Reorder selected posts so that the first half and second half have:
     * - balanced stance counts (left/right as even as possible)
     * - balanced toxicity counts (low/high/middle as even as possible)
     * - less stance clustering (avoid long left-left... runs)
     *
     * Only affects ordering (client slices indices into phases). It does not
     * change which posts are selected.
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

            // Sanity: toxicity counts should fully account for the half.
            const toxSum = c.sample_low_toxicity + c.sample_high_toxicity + c.sample_middle_toxicity;
            if (toxSum !== phaseSize) return false;

            const stanceSeq = half.map(p => normalizeStance(p));
            const run = maxRun(stanceSeq);
            const trans = transitions(stanceSeq);

            // Avoid heavy clustering; tuned for 5/5 halves.
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
            if (isValid(p1) && isValid(p2)) return candidate;
        }

        // Fallback: at least shuffle to remove deterministic clustering.
        return shuffleInPlace(posts.slice());
    };

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

    // Weighted target per participant follows actual catalog prevalence.
    // First allocate by toxicity, then split each toxicity across left/right.
    const toxicityTieLookup = new Map(rotatedToxicityOrder.map((k, i) => [k, i]));
    const targetByToxicity = allocateByWeights(neededCount, TOXICITY_ORDER, catalogCountsByToxicity, toxicityTieLookup);

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
        while (selectedPosts.length < neededCount && selectedCountByCell[key] < target) {
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

    const fallbackUsed = selectedPosts.length < neededCount;

    const combinedPosts = selectedPosts.map(p => ({ post_id: p.post_id, post_number: p.post_number }));

    pendingAssignments[prolificID] = {
        party_group: partyGroup,
        condition: assignedCondition,
        posts: combinedPosts,
        assignedAt: new Date().toISOString()
    };

    savePendingAssignments(pendingAssignments, effectiveIsTest);

    const fallbackNote = fallbackUsed ? ' (short assignment)' : '';
    const testNote = effectiveIsTest ? ' [test]' : '';
    console.log(`Assigned ${combinedPosts.length} posts to ${prolificID} (${partyGroup}, ${assignedCondition})${fallbackNote}${testNote}: ${combinedPosts.map(p => p.post_number).join(', ')}`);

    res.json({ 
        assigned_post_ids: combinedPosts.map(p => p.post_id),
        already_assigned: false,
        fallback_used: fallbackUsed,
        condition: assignedCondition,
        is_test: effectiveIsTest
    });
});

// ============================================================
// PARTICIPANT ID ENDPOINT (legacy, kept for compatibility)
// ============================================================

app.get('/get-participant-id', (req, res) => {
    const prolificID = req.query.prolific_id;
    const party = req.query.party;
    const isTest = req.query.is_test === 'true';

    if (!prolificID) {
        return res.status(400).json({ error: 'No Prolific ID provided' });
    }

    if (!party) {
        return res.status(400).json({ error: 'No political party provided' });
    }

    const partyGroup = (party === 'democrat' || party === 'lean_democrat') ? 'democrat' : 'republican';
    const participantID = `P_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

    res.json({ participantID, partyGroup });
});

// ============================================================
// DATA SAVE ENDPOINT
// ============================================================

app.post('/save-jspsych-data', (req, res) => {
    const data = req.body;
    const isTest = data?.is_test === true
        || !data?.prolific_id
        || (typeof data?.prolific_id === 'string' && (data.prolific_id.startsWith('UNKNOWN_') || data.prolific_id.startsWith('TEST_')));
    const filename = `data_${Date.now()}.csv`;
    const targetDir = isTest ? TEST_DIR : PROLIFIC_DIR;
    
    fs.writeFile(path.join(targetDir, filename), data.csv, (err) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error saving data');
        } else {
            const prefix = isTest ? 'test' : 'prolific';
            console.log(`Data saved to ${prefix}/${filename}`);
            // Commit pending assignment now that data is saved
            const prolificID = data?.prolific_id;
            if (prolificID) {
                const { postAssignments, participantAssignments, pendingAssignments, isTest: effectiveIsTest } = getAssignmentContext({
                    prolificID,
                    isTest
                });

                const pending = pendingAssignments[prolificID];
                if (pending && pending.posts && pending.posts.length > 0) {
                    pending.posts.forEach(post => {
                        if (!postAssignments[post.post_id]) {
                            postAssignments[post.post_id] = {
                                post_number: post.post_number,
                                counts: makeConditionCounts()
                            };
                        }
                        postAssignments[post.post_id].counts = makeConditionCounts(postAssignments[post.post_id].counts);
                        const pendingCondition = CONDITIONS.includes(pending.condition) ? pending.condition : CONDITIONS[0];
                        postAssignments[post.post_id].counts[pendingCondition] =
                            (postAssignments[post.post_id].counts[pendingCondition] || 0) + 1;
                    });

                    if (!participantAssignments[pending.party_group]?.assignments) {
                        participantAssignments[pending.party_group].assignments = {};
                    }

                    participantAssignments[pending.party_group].assignments[prolificID] = {
                        condition: pending.condition,
                        posts: pending.posts,
                        assignedAt: pending.assignedAt
                    };
                    participantAssignments[pending.party_group].count =
                        (participantAssignments[pending.party_group].count || 0) + 1;

                    delete pendingAssignments[prolificID];

                    savePostAssignments(postAssignments, effectiveIsTest);
                    saveParticipantAssignments(participantAssignments, effectiveIsTest);
                    savePendingAssignments(pendingAssignments, effectiveIsTest);
                }
            }

            res.json({ message: 'Data saved successfully', filename, is_test: isTest });
        }
    });
});

// ============================================================
// DEBUG ENDPOINTS
// ============================================================

app.get('/debug/assignments', (req, res) => {
    res.json({
        participantAssignments,
        participantAssignmentsLocal,
        postAssignmentCount: Object.keys(postAssignments).length,
        postAssignmentCountLocal: Object.keys(postAssignmentsLocal).length
    });
});

app.get('/debug/post-assignments', (req, res) => {
    const useTest = req.query.is_test === 'true';
    const assignmentsToInspect = useTest ? postAssignmentsLocal : postAssignments;

    // Count posts by completion status (per condition)
    let controlComplete = 0;
    let trainingComplete = 0;
    let assistedComplete = 0;
    let unassigned = 0;

    Object.values(assignmentsToInspect).forEach(assignment => {
        const counts = makeConditionCounts(assignment?.counts);
        const controlCount = counts.control || 0;
        const trainingCount = counts.training || 0;
        const assistedCount = counts.training_assisted || 0;
        const hasControl = controlCount > 0;
        const hasTraining = trainingCount > 0;
        const hasAssisted = assistedCount > 0;

        if (hasControl) {
            controlComplete++;
        }
        if (hasTraining) {
            trainingComplete++;
        }
        if (hasAssisted) {
            assistedComplete++;
        }
        if (!hasControl && !hasTraining && !hasAssisted) {
            unassigned++;
        }
    });

    res.json({
        summary: {
            totalTracked: Object.keys(assignmentsToInspect).length,
            controlComplete,
            trainingComplete,
            assistedComplete,
            unassigned
        },
        details: assignmentsToInspect,
        is_test: useTest
    });
});

// Reset endpoint for testing
app.post('/debug/reset', (req, res) => {
    const useTest = req.query.is_test === 'true';

    if (useTest) {
        postAssignmentsLocal = {};
        participantAssignmentsLocal = createEmptyParticipantAssignments();
        pendingAssignmentsLocal = {};
        savePostAssignments(postAssignmentsLocal, true);
        saveParticipantAssignments(participantAssignmentsLocal, true);
        savePendingAssignments(pendingAssignmentsLocal, true);
        console.log('Reset test assignments');
        res.json({ message: 'Test assignments reset', is_test: true });
        return;
    }

    postAssignments = {};
    participantAssignments = createEmptyParticipantAssignments();
    pendingAssignments = {};
    savePostAssignments(postAssignments, false);
    saveParticipantAssignments(participantAssignments, false);
    savePendingAssignments(pendingAssignments, false);
    console.log('Reset main assignments');
    res.json({ message: 'Main assignments reset', is_test: false });
});

// ============================================================
// START SERVER
// ============================================================

app.listen(port, () => {
    console.log(`\n Local development server running at http://localhost:${port}`);
    console.log(`\n Debug endpoints:`);
    console.log(`   http://localhost:${port}/debug/assignments`);
    console.log(`   http://localhost:${port}/debug/post-assignments`);
    console.log(`\n Data will be saved to: ${DATA_DIR}`);
    console.log(`\n  Configuration:`);
    console.log(`   Posts per participant: ${NUM_POSTS_PER_PARTICIPANT}`);
    console.log(`   Conditions: ${CONDITIONS.join(', ')}`);
});
