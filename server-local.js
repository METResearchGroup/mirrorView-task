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
const POST_ASSIGNMENTS_FILE = path.join(DATA_DIR, 'post_assignments.json');
const PARTICIPANT_ASSIGNMENTS_FILE = path.join(DATA_DIR, 'participant_assignments.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Load or initialize post assignments
// Structure: { "post_id": { democrat: count, republican: count }, ... }
let postAssignments = {};
if (fs.existsSync(POST_ASSIGNMENTS_FILE)) {
    try {
        postAssignments = JSON.parse(fs.readFileSync(POST_ASSIGNMENTS_FILE, 'utf8'));
        console.log(`Loaded ${Object.keys(postAssignments).length} post assignments from file`);
    } catch (e) {
        console.error('Error loading post assignments:', e);
        postAssignments = {};
    }
}

// Load or initialize participant assignments
let participantAssignments = {
    democrat: { count: 0, assignments: {} },
    republican: { count: 0, assignments: {} }
};
if (fs.existsSync(PARTICIPANT_ASSIGNMENTS_FILE)) {
    try {
        participantAssignments = JSON.parse(fs.readFileSync(PARTICIPANT_ASSIGNMENTS_FILE, 'utf8'));
        console.log(`Loaded participant assignments from file`);
    } catch (e) {
        console.error('Error loading participant assignments:', e);
    }
}

// Save functions
function savePostAssignments() {
    fs.writeFileSync(POST_ASSIGNMENTS_FILE, JSON.stringify(postAssignments, null, 2));
}

function saveParticipantAssignments() {
    fs.writeFileSync(PARTICIPANT_ASSIGNMENTS_FILE, JSON.stringify(participantAssignments, null, 2));
}

// ============================================================
// CONFIGURATION
// ============================================================

const NUM_POSTS_PER_PARTICIPANT = 5;
const MAX_RATINGS_PER_PARTY = 3; // 3 democrats + 3 republicans = 6 total per post

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
    const { prolific_id: prolificID, party_group: partyGroup, all_posts: allPosts } = req.body;

    if (!prolificID) {
        return res.status(400).json({ error: 'No prolific_id provided' });
    }

    if (!partyGroup || !['democrat', 'republican'].includes(partyGroup)) {
        return res.status(400).json({ error: 'Invalid party_group. Must be "democrat" or "republican"' });
    }

    if (!allPosts || allPosts.length === 0) {
        return res.status(400).json({ error: 'No posts provided' });
    }

    // Create a mapping from post_id to post_number
    const postIdToNumber = {};
    allPosts.forEach(p => {
        postIdToNumber[p.post_id] = p.post_number;
    });

    // Check if this participant already has assigned posts
    const existingAssignment = participantAssignments[partyGroup]?.assignments?.[prolificID];
    if (existingAssignment && existingAssignment.posts) {
        console.log(`Returning existing assignment for ${prolificID}: ${existingAssignment.posts.length} posts`);
        return res.json({ 
            assigned_post_ids: existingAssignment.posts.map(p => p.post_id || p), // Handle both old and new format
            already_assigned: true
        });
    }

    // Find posts that haven't reached the quota for this party
    const availablePosts = allPosts.filter(post => {
        const assignment = postAssignments[post.post_id];
        if (!assignment) return true; // Not yet assigned to anyone
        return (assignment[partyGroup] || 0) < MAX_RATINGS_PER_PARTY;
    });

    console.log(`Available posts for ${partyGroup}: ${availablePosts.length}/${allPosts.length}`);

    if (availablePosts.length < NUM_POSTS_PER_PARTICIPANT) {
        return res.status(429).json({ 
            error: 'Not enough posts available for this party',
            available: availablePosts.length,
            needed: NUM_POSTS_PER_PARTICIPANT
        });
    }

    // Randomly select posts
    const shuffled = [...availablePosts].sort(() => Math.random() - 0.5);
    const selectedPosts = shuffled.slice(0, NUM_POSTS_PER_PARTICIPANT);

    // Update post assignments (store both post_id and post_number)
    selectedPosts.forEach(post => {
        if (!postAssignments[post.post_id]) {
            postAssignments[post.post_id] = { 
                post_number: post.post_number,
                democrat: 0, 
                republican: 0 
            };
        }
        postAssignments[post.post_id][partyGroup]++;
    });

    // Save participant assignment (store both post_id and post_number)
    if (!participantAssignments[partyGroup].assignments) {
        participantAssignments[partyGroup].assignments = {};
    }
    participantAssignments[partyGroup].assignments[prolificID] = {
        posts: selectedPosts.map(p => ({ post_id: p.post_id, post_number: p.post_number })),
        assignedAt: new Date().toISOString()
    };
    participantAssignments[partyGroup].count++;

    // Persist to disk
    savePostAssignments();
    saveParticipantAssignments();

    console.log(`Assigned ${selectedPosts.length} posts to ${prolificID} (${partyGroup}): ${selectedPosts.map(p => p.post_number).join(', ')}`);

    res.json({ 
        assigned_post_ids: selectedPosts.map(p => p.post_id),
        already_assigned: false
    });
});

// ============================================================
// PARTICIPANT ID ENDPOINT (legacy, kept for compatibility)
// ============================================================

app.get('/get-participant-id', (req, res) => {
    const prolificID = req.query.prolific_id;
    const party = req.query.party;

    if (!prolificID) {
        return res.status(400).json({ error: 'No Prolific ID provided' });
    }

    if (!party) {
        return res.status(400).json({ error: 'No political party provided' });
    }

    const partyGroup = (party === 'democrat' || party === 'lean_democrat') ? 'democrat' : 'republican';

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

    saveParticipantAssignments();

    console.log(`Assigned participant ID ${participantID} to ${prolificID} (${partyGroup})`);
    res.json({ participantID, partyGroup });
});

// ============================================================
// DATA SAVE ENDPOINT
// ============================================================

app.post('/save-jspsych-data', (req, res) => {
    const data = req.body;
    const filename = `data_${Date.now()}.csv`;
    
    fs.writeFile(path.join(DATA_DIR, filename), data.csv, (err) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error saving data');
        } else {
            console.log(`Data saved to ${filename}`);
            res.json({ message: 'Data saved successfully', filename });
        }
    });
});

// ============================================================
// DEBUG ENDPOINTS
// ============================================================

app.get('/debug/assignments', (req, res) => {
    res.json({
        participantAssignments,
        postAssignmentCount: Object.keys(postAssignments).length
    });
});

app.get('/debug/post-assignments', (req, res) => {
    // Count posts by completion status
    let fullyComplete = 0;
    let partialDemocrat = 0;
    let partialRepublican = 0;
    let unassigned = 0;

    Object.values(postAssignments).forEach(assignment => {
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
            totalTracked: Object.keys(postAssignments).length,
            fullyComplete,
            partialDemocrat,
            partialRepublican
        },
        details: postAssignments
    });
});

// Reset endpoint for testing
app.post('/debug/reset', (req, res) => {
    postAssignments = {};
    participantAssignments = {
        democrat: { count: 0, assignments: {} },
        republican: { count: 0, assignments: {} }
    };
    savePostAssignments();
    saveParticipantAssignments();
    console.log('Reset all assignments');
    res.json({ message: 'All assignments reset' });
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
