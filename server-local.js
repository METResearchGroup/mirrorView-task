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
// Structure: { "post_id": { post_number, democrat: count, republican: count }, ... }
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

// Save functions
function savePostAssignments(assignments, isTest) {
    const target = isTest ? POST_ASSIGNMENTS_LOCAL_FILE : POST_ASSIGNMENTS_FILE;
    fs.writeFileSync(target, JSON.stringify(assignments, null, 2));
}

function saveParticipantAssignments(assignments, isTest) {
    const target = isTest ? PARTICIPANT_ASSIGNMENTS_LOCAL_FILE : PARTICIPANT_ASSIGNMENTS_FILE;
    fs.writeFileSync(target, JSON.stringify(assignments, null, 2));
}

function getAssignmentContext({ prolificID, isTest }) {
    const inferredTest = isTest === true
        || (typeof prolificID === 'string' && (prolificID.startsWith('TEST_') || prolificID.startsWith('UNKNOWN_')));
    return {
        isTest: inferredTest,
        postAssignments: inferredTest ? postAssignmentsLocal : postAssignments,
        participantAssignments: inferredTest ? participantAssignmentsLocal : participantAssignments
    };
}

// ============================================================
// CONFIGURATION
// ============================================================

const NUM_POSTS_PER_PARTICIPANT = 10;
const MAX_RATINGS_PER_PARTY = 3; // 3 democrats + 3 republicans = 6 total per post
const CONDITIONS = ['control', 'linked_fate'];

// ============================================================
// MIDDLEWARE
// ============================================================

app.use(bodyParser.json());

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
 *   - all_posts: Array of {post_id, post_number} objects
 * 
 * Returns:
 *   - assigned_post_ids: Array of 5 post IDs to show this participant
 */
app.post('/get-post-assignments', (req, res) => {
    const { prolific_id: prolificID, party_group: partyGroup, condition, all_posts: allPosts, is_test: isTest } = req.body;

    const normalizedConditionRaw = typeof condition === 'string' ? condition.toLowerCase() : '';
    let normalizedCondition = normalizedConditionRaw.replace('-', '_');
    if (normalizedCondition === 'linkedfate') normalizedCondition = 'linked_fate';
    if (!CONDITIONS.includes(normalizedCondition)) {
        normalizedCondition = 'control';
    }

    if (!prolificID) {
        return res.status(400).json({ error: 'No prolific_id provided' });
    }

    if (!partyGroup || !['democrat', 'republican'].includes(partyGroup)) {
        return res.status(400).json({ error: 'Invalid party_group. Must be "democrat" or "republican"' });
    }

    if (!allPosts || allPosts.length === 0) {
        return res.status(400).json({ error: 'No posts provided' });
    }

    const { postAssignments, participantAssignments, isTest: effectiveIsTest } = getAssignmentContext({
        prolificID,
        isTest
    });

    // Check if this participant already has assigned posts
    const existingAssignment = participantAssignments[partyGroup]?.assignments?.[prolificID];
    if (existingAssignment && existingAssignment.posts) {
        const existingPostIds = existingAssignment.posts.map(p => p.post_id || p);
        if (existingPostIds.length >= NUM_POSTS_PER_PARTICIPANT) {
            console.log(`Returning existing assignment for ${prolificID}: ${existingPostIds.length} posts`);
            return res.json({ 
                assigned_post_ids: existingPostIds,
                already_assigned: true,
                condition: existingAssignment.condition || normalizedCondition
            });
        }
    }

    // Find posts that haven't reached the quota for this party
    const existingPostIds = new Set(existingAssignment?.posts?.map(p => p.post_id || p) || []);
    const availablePosts = allPosts.filter(post => {
        if (existingPostIds.has(post.post_id)) return false;
        const assignment = postAssignments[post.post_id];
        if (!assignment) return true; // Not yet assigned to anyone
        return (assignment[partyGroup] || 0) < MAX_RATINGS_PER_PARTY;
    });

    console.log(`Available posts for ${partyGroup}: ${availablePosts.length}/${allPosts.length} (${normalizedCondition})`);

    const getCounts = (post) => {
        const assignment = postAssignments[post.post_id];
        const partyCount = assignment ? (assignment[partyGroup] || 0) : 0;
        const totalCount = assignment ? ((assignment.democrat || 0) + (assignment.republican || 0)) : 0;
        const conditionCount = assignment?.counts?.[partyGroup]?.[normalizedCondition] || 0;
        return { partyCount, totalCount, conditionCount };
    };

    // Randomly select from available posts first
    const neededCount = Math.max(NUM_POSTS_PER_PARTICIPANT - existingPostIds.size, 0);
    const selectedPosts = [...availablePosts]
        .sort((a, b) => {
            const aCounts = getCounts(a);
            const bCounts = getCounts(b);
            if (aCounts.conditionCount !== bCounts.conditionCount) return aCounts.conditionCount - bCounts.conditionCount;
            if (aCounts.partyCount !== bCounts.partyCount) return aCounts.partyCount - bCounts.partyCount;
            if (aCounts.totalCount !== bCounts.totalCount) return aCounts.totalCount - bCounts.totalCount;
            return Math.random() - 0.5;
        })
        .slice(0, neededCount);

    // If we don't have enough available posts, fill from the least-used posts (even if at/over quota)
    let fallbackUsed = false;
    if (selectedPosts.length < neededCount) {
        fallbackUsed = true;
        const selectedIds = new Set(selectedPosts.map(p => p.post_id));
        const remainingPosts = allPosts.filter(p => !selectedIds.has(p.post_id) && !existingPostIds.has(p.post_id));

        const getPartyCount = (post) => {
            const assignment = postAssignments[post.post_id];
            return assignment ? (assignment[partyGroup] || 0) : 0;
        };

        const fallbackCandidates = [...remainingPosts].sort((a, b) => getPartyCount(a) - getPartyCount(b));
        const needed = neededCount - selectedPosts.length;
        selectedPosts.push(...fallbackCandidates.slice(0, needed));
    }

    const combinedPosts = [
        ...(existingAssignment?.posts?.map(p => ({ post_id: p.post_id || p, post_number: p.post_number })) || []),
        ...selectedPosts
    ];

    // Update post assignments (store both post_id and post_number)
    selectedPosts.forEach(post => {
        if (!postAssignments[post.post_id]) {
            postAssignments[post.post_id] = { 
                post_number: post.post_number,
                democrat: 0, 
                republican: 0,
                counts: {
                    democrat: { control: 0, linked_fate: 0 },
                    republican: { control: 0, linked_fate: 0 }
                }
            };
        }
        if (!postAssignments[post.post_id].counts) {
            postAssignments[post.post_id].counts = {
                democrat: { control: 0, linked_fate: 0 },
                republican: { control: 0, linked_fate: 0 }
            };
        }
        postAssignments[post.post_id][partyGroup]++;
        postAssignments[post.post_id].counts[partyGroup][normalizedCondition]++;
    });

    // Save participant assignment (store both post_id and post_number)
    if (!participantAssignments[partyGroup].assignments) {
        participantAssignments[partyGroup].assignments = {};
    }
    participantAssignments[partyGroup].assignments[prolificID] = {
        condition: normalizedCondition,
        posts: combinedPosts.map(p => ({ post_id: p.post_id, post_number: p.post_number })),
        assignedAt: new Date().toISOString()
    };
    participantAssignments[partyGroup].count++;

    // Persist to disk
    savePostAssignments(postAssignments, effectiveIsTest);
    saveParticipantAssignments(participantAssignments, effectiveIsTest);

    const fallbackNote = fallbackUsed ? ' (used fallback posts over quota)' : '';
    const testNote = effectiveIsTest ? ' [test]' : '';
    console.log(`Assigned ${combinedPosts.length} posts to ${prolificID} (${partyGroup}, ${normalizedCondition})${fallbackNote}${testNote}: ${combinedPosts.map(p => p.post_number).join(', ')}`);

    res.json({ 
        assigned_post_ids: combinedPosts.map(p => p.post_id),
        already_assigned: existingPostIds.size > 0,
        fallback_used: fallbackUsed,
        condition: normalizedCondition,
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
    const { participantAssignments, isTest: effectiveIsTest } = getAssignmentContext({
        prolificID,
        isTest
    });

    // Check if participant already has an assignment
    const existing = participantAssignments[partyGroup]?.assignments?.[prolificID];
    if (existing) {
        return res.json({ 
            participantID: existing.participantID || participantAssignments[partyGroup].count,
            partyGroup 
        });
    }

    // Assign new ID
    participantAssignments[partyGroup].count++;
    const participantID = participantAssignments[partyGroup].count;

    if (!participantAssignments[partyGroup].assignments) {
        participantAssignments[partyGroup].assignments = {};
    }
    participantAssignments[partyGroup].assignments[prolificID] = {
        participantID,
        assignedAt: new Date().toISOString()
    };

    saveParticipantAssignments(participantAssignments, effectiveIsTest);

    const testNote = effectiveIsTest ? ' [test]' : '';
    console.log(`Assigned participant ID ${participantID} to ${prolificID} (${partyGroup})${testNote}`);
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

    // Count posts by completion status
    let fullyComplete = 0;
    let partialDemocrat = 0;
    let partialRepublican = 0;
    let unassigned = 0;

    Object.values(assignmentsToInspect).forEach(assignment => {
        const demComplete = (assignment.democrat || 0) >= MAX_RATINGS_PER_PARTY;
        const repComplete = (assignment.republican || 0) >= MAX_RATINGS_PER_PARTY;
        
        if (demComplete && repComplete) {
            fullyComplete++;
        } else if (demComplete) {
            partialDemocrat++;
        } else if (repComplete) {
            partialRepublican++;
        }
    });

    res.json({
        summary: {
            totalTracked: Object.keys(assignmentsToInspect).length,
            fullyComplete,
            partialDemocrat,
            partialRepublican
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
        savePostAssignments(postAssignmentsLocal, true);
        saveParticipantAssignments(participantAssignmentsLocal, true);
        console.log('Reset test assignments');
        res.json({ message: 'Test assignments reset', is_test: true });
        return;
    }

    postAssignments = {};
    participantAssignments = createEmptyParticipantAssignments();
    savePostAssignments(postAssignments, false);
    saveParticipantAssignments(participantAssignments, false);
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
    console.log(`   Max ratings per party per post: ${MAX_RATINGS_PER_PARTY}`);
});
