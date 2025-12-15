const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3000;

// set available participantIDs to array from 1-350
let availableIDs = Array.from({length: 350}, (_, i) => i + 1);
let assignments = new Map();

// Track political party assignments
let politicalAssignments = {
    democrat: { count: 0, assignments: new Map() },
    republican: { count: 0, assignments: new Map() }
};

// middleware
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// serve HTML file
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// endpoint to get participantID; assigns and returns a participantID to a prolificID
app.get('/get-participant-id', (req, res) => {
    const prolificID = req.query.prolific_id;
    const party = req.query.party;

    if (!prolificID) {
        return res.status(400).json({ error: 'No Prolific ID provided' });
    }

    if (!party) {
        return res.status(400).json({ error: 'No political party provided' });
    }

    // Check if participant already has an assignment
    if (assignments.has(prolificID)) {
        res.json({ participantID: assignments.get(prolificID) });
        return;
    }

    // Assign based on political party
    let participantID;
    if (party === 'democrat' || party === 'lean_democrat') {
        if (politicalAssignments.democrat.count < 175) {
            participantID = politicalAssignments.democrat.count + 1;
            politicalAssignments.democrat.count++;
        } else {
            // Fallback to general pool if party quota is full
            participantID = availableIDs.shift();
        }
    } else if (party === 'republican' || party === 'lean_republican') {
        if (politicalAssignments.republican.count < 175) {
            participantID = politicalAssignments.republican.count + 176; // Start from 176
            politicalAssignments.republican.count++;
        } else {
            // Fallback to general pool if party quota is full
            participantID = availableIDs.shift();
        }
    } else {
        // For other parties, assign from general pool
        participantID = availableIDs.shift();
    }

    if (participantID) {
        assignments.set(prolificID, participantID);
        console.log(`Assigned participant ID ${participantID} to ${prolificID} (${party})`);
        res.json({ participantID });
    } else {
        res.status(429).json({ error: 'No more participant IDs available' });
    }
});

// endpoint to save data
app.post('/save-jspsych-data', (req, res) => {
    const data = req.body;
    const filename = `data_${Date.now()}.csv`;
    
    // Create local_data directory if it doesn't exist
    const dataDir = path.join(__dirname, 'local_data');
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }
    
    fs.writeFile(path.join(dataDir, filename), data.csv, (err) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error saving data');
        } else {
            console.log(`Data saved to ${filename}`);
            res.json({ message: 'Data saved successfully', filename });
        }
    });
});

// Debug endpoint to see current assignments
app.get('/debug/assignments', (req, res) => {
    res.json({
        totalAssignments: assignments.size,
        politicalAssignments,
        availableIDs: availableIDs.length,
        assignments: Object.fromEntries(assignments)
    });
});

app.listen(port, () => {
    console.log(`Local development server running at http://localhost:${port}`);
    console.log(`Debug endpoint: http://localhost:${port}/debug/assignments`);
    console.log(`Data will be saved to: ${path.join(__dirname, 'local_data')}`);
});
