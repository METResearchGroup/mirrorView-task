/**
 * MirrorView Experiment - Local Development Version
 *
 * Participants act as content moderators. In the control condition, they
 * evaluate single posts. In the linked-fate condition, they evaluate paired
 * original + mirror posts and make one decision that applies to both.
 */

let currentProlificID = null;
let isTestParticipant = false;

const jsPsych = initJsPsych({
    use_webaudio: false,
    on_finish: function() {
        let allData = jsPsych.data.get();
        
        // Flatten any nested response objects
        function flattenResponses(data) {
            if (data.response && typeof data.response === 'object') {
                Object.entries(data.response).forEach(([key, value]) => {
                    data[key] = value;
                });
                delete data.response;
            }
            return data;
        }
        
        // Process all trials
        let allTrials = allData.values();
        allTrials.forEach(flattenResponses);

        // Define columns to keep
        const columnsToKeep = [
            'trial_type',
            'trial_index',
            'time_elapsed',
            'rt',
            // Moderation trial data
            'post_id',
            'post_number',      // Numeric post identifier (easier to reference)
            'original_text',
            'mirror_text',
            'show_pair',
            'decision',
            'pair_order',
            'response_time_ms',
            // Participant info
            'participant_id',
            'prolific_id',
            'consented',
            'political_affiliation',
            'party_lean',
            'party_group',
            'condition',
            // Demographics (if collected)
            'age',
            'gender',
            'education',
            // Political attitudes (if collected)
            'political_ideology',
            'political_follow',
            'rep_id',
            'dem_id'
        ];
        
        // Create CSV
        const createCSV = (trials, columns) => {
            if (trials.length === 0) return '';
            const headers = columns.join(',');
            const rows = trials.map(row => 
                columns.map(col => {
                    let value = row[col];
                    if (value === undefined || value === null) return '';
                    if (typeof value === 'object') value = JSON.stringify(value);
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
                        return `"${value.replace(/"/g, '""')}"`;
                    }
                    return value;
                }).join(',')
            );
            return [headers, ...rows].join('\n');
        };
        
        const csv = createCSV(allTrials, columnsToKeep);
        
        // Save data using local endpoint
        const endpoint = '/save-jspsych-data';
        
        console.log('Saving data to:', endpoint);
        
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                csv: csv,
                prolific_id: currentProlificID,
                is_test: isTestParticipant
            })
        })
        .then(response => response.json())
        .then(result => {
            console.log('Data saved:', result);
            // Show Prolific completion link + code
            document.body.innerHTML = `
                <div style="text-align: center; margin-top: 50px; font-family: system-ui, sans-serif;">
                    <p style="font-size: 18px; color: #4b5563; margin-bottom: 10px;">
                        Thank you for participating! Your responses have been recorded.
                    </p>
                    <p style="font-size: 18px; color: #4b5563;">
                        <a href="https://app.prolific.com/submissions/complete?cc=CE5XLP3L" target="_blank">
                            <b>Click here</b>
                        </a>
                        to be redirected to Prolific (completion code <b>CE5XLP3L</b>).
                    </p>
                </div>
            `;
        })
        .catch(error => {
            console.error('Error saving data:', error);
            document.body.innerHTML = `
                <div style="text-align: center; margin-top: 100px; font-family: system-ui, sans-serif;">
                    <h1 style="color: #dc2626;">Error</h1>
                    <p>There was an error saving your data. Please contact the researcher.</p>
                    <p style="color: #9ca3af; font-size: 14px;">Error: ${error.message}</p>
                </div>
            `;
        });
    }
});


// ============================================================
// DATA LOADING
// ============================================================

/**
 * Load and parse the mirror data CSV
 * Uses a proper CSV parser that handles quoted fields with embedded newlines
 */
async function loadMirrorData() {
    try {
        const response = await fetch('img/all_mirrors_claude.csv');
        const csvText = await response.text();
        
        // Parse CSV properly handling quoted fields with newlines
        const data = parseCSV(csvText);
        
        // Filter to only rows with valid data
        // Each row represents one post with its Claude mirror
        const validData = data.filter(row => 
            row.original_text && 
            row.original_text.trim() !== '' &&
            row.claude_mirror &&
            row.claude_mirror.trim() !== ''
        );
        
        console.log(`Loaded ${validData.length} posts with mirrors`);
        return validData;
    } catch (error) {
        console.error('Error loading mirror data:', error);
        throw error;
    }
}

/**
 * Parse CSV text into array of objects
 * Handles RFC 4180 compliant CSV (quoted fields with embedded newlines/commas)
 */
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
                    // Escaped quote
                    currentField += '"';
                    i++;
                } else {
                    // End of quoted field
                    inQuotes = false;
                }
            } else {
                currentField += char;
            }
        } else {
            if (char === '"') {
                // Start of quoted field
                inQuotes = true;
            } else if (char === ',') {
                // Field separator
                currentRow.push(currentField);
                currentField = '';
            } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
                // End of row
                if (char === '\r') i++; // Skip the \n in \r\n
                
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
    
    // Handle last row (if no trailing newline)
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


// ============================================================
// EXPERIMENT CONFIGURATION
// ============================================================

const NUM_TRIALS = 10; // Number of posts each participant rates


// ============================================================
// GLOBAL STATE
// ============================================================

// Store all mirror data (loaded at start)
let allMirrorData = [];

// Store assigned posts (populated after political affiliation)
let assignedPosts = [];

// Store assigned condition
let assignedCondition = null;


// ============================================================
// MAIN EXPERIMENT SETUP
// ============================================================

async function setupExperiment() {
    try {
        // Get URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const prolificPID = urlParams.get('PROLIFIC_PID');
        currentProlificID = prolificPID || 'TEST_' + Date.now();
        isTestParticipant = !prolificPID;
        console.log('Prolific ID:', currentProlificID, isTestParticipant ? '(test)' : '');

        
        // Load mirror data
        allMirrorData = await loadMirrorData();
        
        // Build timeline
        const timeline = [];
        
        // ========== WELCOME ==========
        const welcome = {
            type: jsPsychInstructions,
            pages: [`
                <div class='instructions'>
                    <h2>Welcome!</h2>
                    <p>In this study, you will take on the role of a content moderator for a political discussion forum.</p>
                    <p>Your task is to decide whether each post should be <b>kept</b> or <b>removed</b>.</p>
                    <br>
                    <p>Click <b>Next</b> to continue.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(welcome);

        // ========== CONSENT ==========
        timeline.push(consent);
        
        // ========== POLITICAL AFFILIATION CONFIRMATION ==========
        // (defined in pre_surveys.js)
        timeline.push(politicalAffiliation);
        
        // ========== ASSIGN PARTICIPANT ID ==========
        let ParticipantID = null;
        
        const assignParticipantId = {
            type: jsPsychCallFunction,
            async: true,
            func: async function(done) {
                ParticipantID = 'P_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                jsPsych.data.addProperties({
                    participant_id: ParticipantID,
                    prolific_id: currentProlificID,
                    num_trials: NUM_TRIALS,
                    experiment_version: 'mirrorView_phase2'
                });
                done();
            }
        };
        timeline.push(assignParticipantId);
        
        // ========== FETCH ASSIGNED POSTS ==========
        // This runs after political affiliation and fetches posts based on party
        const fetchAssignedPosts = {
            type: jsPsychCallFunction,
            async: true,
            func: async function(done) {
                try {
                    // Get the party_group from the data we just collected
                    const partyGroup = jsPsych.data.get().last(1).values()[0].party_group 
                        || jsPsych.data.getDataByTimelineNode(jsPsych.getCurrentTimelineNodeID()).trials[0]?.party_group;
                    
                    // If we can't get party_group from the last trial, try getting it from addProperties
                    const allData = jsPsych.data.get().values();
                    const latestWithParty = allData.filter(d => d.party_group).pop();
                    const effectivePartyGroup = partyGroup || latestWithParty?.party_group;
                    
                    console.log('Party group for assignment:', effectivePartyGroup);
                    
                    if (!effectivePartyGroup) {
                        console.error('Could not determine party group');
                        // Fallback to random sampling
                        const shuffled = [...allMirrorData].sort(() => Math.random() - 0.5);
                        assignedPosts = shuffled.slice(0, NUM_TRIALS);
                        done();
                        return;
                    }
                    
                    // Get all posts with both ID and number
                    const allPosts = allMirrorData.map(p => ({
                        post_id: p.post_primary_key,
                        post_number: p.post_number
                    }));
                    
                    // Call the server to get assigned posts (using POST to handle large payload)
                    const response = await fetch('/get-post-assignments', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            prolific_id: currentProlificID,
                            party_group: effectivePartyGroup,
                            condition: assignedCondition,
                            all_posts: allPosts,
                            is_test: isTestParticipant
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        console.error('Error getting post assignments:', error);
                        // Fallback to random sampling
                        const shuffled = [...allMirrorData].sort(() => Math.random() - 0.5);
                        assignedPosts = shuffled.slice(0, NUM_TRIALS);
                    } else {
                        const result = await response.json();
                        console.log('Received post assignments:', result);
                        
                        // Map post IDs back to full post data
                        assignedPosts = result.assigned_post_ids.map(postId => 
                            allMirrorData.find(p => p.post_primary_key === postId)
                        ).filter(p => p); // Remove any undefined

                        assignedCondition = result.condition || assignedCondition || 'control';
                        jsPsych.data.addProperties({ condition: assignedCondition });
                        
                        console.log(`Assigned ${assignedPosts.length} posts to participant`);
                    }
                    
                    done();
                } catch (error) {
                    console.error('Error fetching post assignments:', error);
                    // Fallback to random sampling
                    const shuffled = [...allMirrorData].sort(() => Math.random() - 0.5);
                    assignedPosts = shuffled.slice(0, NUM_TRIALS);
                    done();
                }
            }
        };
        timeline.push(fetchAssignedPosts);

        const conditionInstructions = {
            type: jsPsychInstructions,
            pages: () => [`
                <div class='instructions'>
                    <h2>Your Task</h2>
                    ${assignedCondition === 'linked_fate'
                        ? `<p>In this condition, you will see <b>two posts at a time</b> that are mirrors of each other.</p>
                           <p>You must make <b>one decision</b> that applies to both posts: keep both or remove both.</p>
                           <p>The order of the two posts will be randomized.</p>`
                        : `<p>In this condition, you will see <b>one post at a time</b> and decide whether to keep or remove it.</p>`
                    }
                    <br>
                    <p>Click <b>Next</b> to continue to an example.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(conditionInstructions);

        const example = {
            type: jsPsychInstructions,
            pages: () => [`
                <div class='instructions'>
                    <h2>Example</h2>
                    ${assignedCondition === 'linked_fate'
                        ? `<p><b>Post A:</b> "I support stricter gun regulations to keep communities safe."</p>
                           <p><b>Post B:</b> "I oppose stricter gun regulations because they infringe on constitutional rights."</p>
                           <br>
                           <p>You would make <b>one decision</b> to keep or remove <b>both posts</b> together.</p>`
                        : `<p><b>Post:</b> "I support stricter gun regulations to keep communities safe."</p>
                           <br>
                           <p>You would decide whether to <b>keep</b> or <b>remove</b> this post.</p>`
                    }
                    <br>
                    <p>Click <b>Next</b> to continue to a practice trial.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(example);

        // ========== PRACTICE TRIAL ==========
        const practiceTrial = {
            type: jsPsychModerationTrial,
            original_text: "Climate change is a pressing issue that requires immediate attention and action.",
            mirror_text: "Climate change is exaggerated, and we should not rush into costly policies.",
            show_pair: () => assignedCondition === 'linked_fate',
            prompt: "Keep or remove?",
            keep_label: "Keep",
            remove_label: "Remove",
            progress_label: "Practice Trial",
            data: { trial_type: 'moderation-practice' }
        };
        timeline.push(practiceTrial);
        
        // ========== READY TO BEGIN ==========
        const readyToBegin = {
            type: jsPsychInstructions,
            pages: [`
                <div class='instructions'>
                    <h2>Great! You're ready to begin.</h2>
                    <p>The real study will be just like the practice. There will be <b>${NUM_TRIALS} trials</b> in total.</p>
                    <p>Please make your decisions based on whether each post should be kept or removed.</p>
                    <br>
                    <p>Click <b>Next</b> to begin.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(readyToBegin);
        
        // ========== MODERATION TRIALS ==========
        // Generate trials dynamically from assignedPosts
        // Each trial is added individually since timeline_variables can't be set dynamically
        for (let i = 0; i < NUM_TRIALS; i++) {
            const trialIndex = i;
            const moderationTrial = {
                type: jsPsychModerationTrial,
                post_id: () => assignedPosts[trialIndex]?.post_primary_key || '',
                post_number: () => assignedPosts[trialIndex]?.post_number || '',
                original_text: () => assignedPosts[trialIndex]?.original_text || '',
                mirror_text: () => assignedPosts[trialIndex]?.claude_mirror || '',
                show_pair: assignedCondition === 'linked_fate',
                prompt: "Keep or remove?",
                keep_label: "Keep",
                remove_label: "Remove",
                trial_number: i + 1,
                total_trials: NUM_TRIALS,
                data: { trial_type: 'moderation-trial' },
                // Skip this trial if no post is assigned
                conditional_function: () => {
                    const hasPost = assignedPosts[trialIndex] && assignedPosts[trialIndex].original_text;
                    if (trialIndex === 0) {
                        console.log('Starting moderation trials with', assignedPosts.length, 'posts');
                    }
                    return hasPost;
                }
            };
            timeline.push(moderationTrial);
        }
        
        // ========== BRIEF DEMOGRAPHICS ==========
        const demographics = {
            type: jsPsychSurveyHtmlForm,
            preamble: "<h2>Almost Done!</h2><p>Please answer a few quick questions about yourself.</p>",
            html: `
                <div class="survey-container">
                    <div class="survey-question">
                        <label for="age">What is your age?</label>
                        <input type="number" id="age" name="age" min="18" max="120" required>
                    </div>
                    <div class="survey-question">
                        <label for="gender">What is your gender?</label>
                        <select id="gender" name="gender" required>
                            <option value="" disabled selected>Select an option</option>
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="non-binary">Non-binary</option>
                            <option value="other">Other</option>
                            <option value="prefer_not">Prefer not to say</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label for="education">What is your highest level of education?</label>
                        <select id="education" name="education" required>
                            <option value="" disabled selected>Select an option</option>
                            <option value="high_school">High school or less</option>
                            <option value="some_college">Some college</option>
                            <option value="bachelors">Bachelor's degree</option>
                            <option value="masters">Master's degree</option>
                            <option value="doctorate">Doctorate</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                </div>
            `,
            button_label: "Next >"
        };
        timeline.push(demographics);

        // ========== IDEOLOGY ==========
        // (defined in post_surveys.js)
        timeline.push(politicalSurvey);
        
        // Run the experiment
        jsPsych.run(timeline);
        
    } catch (error) {
        console.error('Error setting up experiment:', error);
        document.body.innerHTML = `
            <div style="text-align: center; margin-top: 100px; font-family: system-ui, sans-serif;">
                <h1 style="color: #dc2626;">Setup Error</h1>
                <p>There was an error loading the experiment.</p>
                <p style="color: #9ca3af; font-size: 14px;">${error.message}</p>
            </div>
        `;
    }
}

// Start the experiment when page loads
setupExperiment();
