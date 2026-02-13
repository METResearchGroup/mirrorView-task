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
// Structure: { "post_id": { post_number, counts: { control, linked_fate } }, ... }
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

const NUM_POSTS_PER_PARTICIPANT = 10;
const CONDITIONS = ['control', 'linked_fate'];
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
    const { prolific_id: prolificID, party_group: partyGroup, all_posts: allPosts, is_test: isTest } = req.body;

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
                condition: existingAssignment.condition || 'control'
            });
        }
    }

    // Check if participant has pending assignment
    const pending = pendingAssignments[prolificID];
    if (pending && pending.posts) {
        return res.json({
            assigned_post_ids: pending.posts.map(p => p.post_id || p),
            already_assigned: true,
            condition: pending.condition || 'control'
        });
    }

    // Assign condition by alternating within party (based on completed count)
    const completedCount = participantAssignments[partyGroup]?.count || 0;
    const assignedCondition = completedCount % 2 === 0 ? 'control' : 'linked_fate';

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

    const getConditionCount = (post) => {
        const assignment = postAssignments[post.post_id];
        return assignment?.counts?.[assignedCondition] || 0;
    };

    const selectedPosts = [];
    const selectedIds = new Set();

    // Phase 1: unseen posts only (ensures every post is viewed once per condition before repeats)
    const unseenBuckets = {};
    CATEGORY_ORDER.forEach(k => { unseenBuckets[k] = []; });
    sortedPosts.forEach(post => {
        const key = getCategoryKey(post);
        if (!key) return;
        if (getConditionCount(post) === 0) {
            unseenBuckets[key].push(post);
        }
    });

    let pickedInPass = true;
    while (selectedPosts.length < neededCount && pickedInPass) {
        pickedInPass = false;
        for (let i = 0; i < CATEGORY_ORDER.length && selectedPosts.length < neededCount; i++) {
            const key = CATEGORY_ORDER[(startOffset + i) % CATEGORY_ORDER.length];
            const bucket = unseenBuckets[key];
            if (bucket && bucket.length > 0) {
                const post = bucket.shift();
                if (!selectedIds.has(post.post_id)) {
                    selectedIds.add(post.post_id);
                    selectedPosts.push(post);
                    pickedInPass = true;
                }
            }
        }
    }

    // Phase 2: once all unseen eligible posts are exhausted, cycle through least-viewed posts
    if (selectedPosts.length < neededCount) {
        const seenBuckets = {};
        CATEGORY_ORDER.forEach(k => { seenBuckets[k] = []; });
        sortedPosts.forEach(post => {
            if (selectedIds.has(post.post_id)) return;
            const key = getCategoryKey(post);
            if (!key) return;
            seenBuckets[key].push(post);
        });
        CATEGORY_ORDER.forEach(key => {
            seenBuckets[key].sort((a, b) => {
                const aCount = getConditionCount(a);
                const bCount = getConditionCount(b);
                if (aCount !== bCount) return aCount - bCount;
                return Number(a.post_number) - Number(b.post_number);
            });
        });

        pickedInPass = true;
        while (selectedPosts.length < neededCount && pickedInPass) {
            pickedInPass = false;
            for (let i = 0; i < CATEGORY_ORDER.length && selectedPosts.length < neededCount; i++) {
                const key = CATEGORY_ORDER[(startOffset + i) % CATEGORY_ORDER.length];
                const bucket = seenBuckets[key];
                if (bucket && bucket.length > 0) {
                    const post = bucket.shift();
                    if (!selectedIds.has(post.post_id)) {
                        selectedIds.add(post.post_id);
                        selectedPosts.push(post);
                        pickedInPass = true;
                    }
                }
            }
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
                                counts: { control: 0, linked_fate: 0 }
                            };
                        }
                        if (!postAssignments[post.post_id].counts) {
                            postAssignments[post.post_id].counts = { control: 0, linked_fate: 0 };
                        }
                        postAssignments[post.post_id].counts[pending.condition] =
                            (postAssignments[post.post_id].counts[pending.condition] || 0) + 1;
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
    let linkedFateComplete = 0;
    let bothComplete = 0;
    let unassigned = 0;

    Object.values(assignmentsToInspect).forEach(assignment => {
        const controlCount = assignment?.counts?.control || 0;
        const linkedCount = assignment?.counts?.linked_fate || 0;
        const hasControl = controlCount > 0;
        const hasLinked = linkedCount > 0;

        if (hasControl && hasLinked) {
            bothComplete++;
        } else if (hasControl) {
            controlComplete++;
        } else if (hasLinked) {
            linkedFateComplete++;
        } else {
            unassigned++;
        }
    });

    res.json({
        summary: {
            totalTracked: Object.keys(assignmentsToInspect).length,
            controlComplete,
            linkedFateComplete,
            bothComplete,
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
