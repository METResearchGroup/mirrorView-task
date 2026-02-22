/**
 * MirrorView Experiment - AWS Production Version
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
            'context_post_id',
            'context_post_number',
            'sampled_stance',
            'sample_toxicity_type',
            'phase',
            'evaluation_mode',
            'original_text',
            'mirror_text',
            'show_pair',
            'decision',
            'pair_order',
            'evaluated_post_role',
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
            'dem_id',
            'attitude_reduce_abortion',
            'attitude_citizenship_undocumented',
            'attitude_restrict_guns',
            'attitude_regulate_environment',
            'attitude_raise_wealth_taxes',
            'attitude_expand_medicaid'
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
        
        // Save data using AWS endpoint from config
        const urls = window.config?.getUrls?.() || {};
        const endpoint = urls.SAVE_DATA_URL;
        
        if (!endpoint) {
            console.error('No SAVE_DATA_URL configured');
            document.body.innerHTML = `
                <div style="text-align: center; margin-top: 100px; font-family: system-ui, sans-serif;">
                    <h1 style="color: #dc2626;">Configuration Error</h1>
                    <p>Unable to save data - no endpoint configured.</p>
                </div>
            `;
            return;
        }
        
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
            // Redirect to Prolific completion URL if available
            const prolificCompletionUrl = urls.PROLIFIC_COMPLETION_URL;
            if (prolificCompletionUrl) {
                window.location.href = prolificCompletionUrl;
            } else {
                // Show completion message
                document.body.innerHTML = `
                    <div style="text-align: center; margin-top: 100px; font-family: system-ui, sans-serif;">
                        <h1 style="color: #16a34a;">Thank you!</h1>
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
            }
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

const TRIALS_PER_PHASE = 10;
const NUM_PHASES = 2;
const NUM_TRIALS = TRIALS_PER_PHASE * NUM_PHASES; // 20 evaluated trials


// ============================================================
// GLOBAL STATE
// ============================================================

// Store all mirror data (loaded at start)
let allMirrorData = [];

// Store assigned posts (populated after political affiliation)
let assignedPosts = [];
let assistedContextPosts = [];

// Store assigned condition
let assignedCondition = null;
let requestedConditionOverride = null;


// ============================================================
// MAIN EXPERIMENT SETUP
// ============================================================

async function setupExperiment() {
    try {
        // Get URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const prolificPID = urlParams.get('PROLIFIC_PID');
        currentProlificID = prolificPID || 'UNKNOWN_' + Date.now();
        isTestParticipant = !prolificPID;
        console.log('Prolific ID:', currentProlificID, isTestParticipant ? '(test)' : '');
        const conditionParam = (urlParams.get('condition') || '').toLowerCase();
        if (['control', 'training', 'training_assisted'].includes(conditionParam)) {
            requestedConditionOverride = conditionParam;
            console.log('Condition override requested:', requestedConditionOverride);
        }
        
        // Get config URLs
        const urls = window.config?.getUrls?.() || {};

        
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
                    <p>In this study, you will take on the role of a <b>content moderator</b> for a social media platform.</p>
                    <p>Your task will involve deciding whether a selection of posts should be <b>allowed</b> or <b>removed</b> from the platform.</p>
                    <br>
                    <p>Click <b>Next</b> to continue to the consent form.</p>
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
                    const allData = jsPsych.data.get().values();
                    const latestWithParty = allData.filter(d => d.party_group).pop();
                    const partyGroup = latestWithParty?.party_group;
                    
                    console.log('Party group for assignment:', partyGroup);
                    
                    if (!partyGroup) {
                        console.error('Could not determine party group');
                        // Fallback to random sampling
                        const shuffled = [...allMirrorData].sort(() => Math.random() - 0.5);
                        assignedPosts = shuffled.slice(0, NUM_TRIALS);
                        done();
                        return;
                    }
                    
                    // Get the post assignments endpoint from config
                    const postAssignmentUrl = urls.POST_ASSIGNMENTS_URL;
                    
                    if (!postAssignmentUrl) {
                        console.warn('No POST_ASSIGNMENTS_URL configured, using random sampling');
                        const shuffled = [...allMirrorData].sort(() => Math.random() - 0.5);
                        assignedPosts = shuffled.slice(0, NUM_TRIALS);
                        done();
                        return;
                    }
                    
                    // Call the server to get assigned posts
                    const response = await fetch(postAssignmentUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            prolific_id: currentProlificID,
                            party_group: partyGroup,
                            condition: requestedConditionOverride || assignedCondition,
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

                        if (assignedCondition === 'training_assisted') {
                            const assignedIds = new Set(assignedPosts.map(p => p?.post_primary_key).filter(Boolean));
                            assistedContextPosts = allMirrorData.filter(p => !assignedIds.has(p.post_primary_key)).slice(0, TRIALS_PER_PHASE);
                        } else {
                            assistedContextPosts = [];
                        }
                        
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

        const getPhaseMode = (phaseNumber) => {
            if (phaseNumber === 1) {
                return assignedCondition === 'control' ? 'single' : 'linked_fate';
            }
            if (assignedCondition === 'training_assisted') return 'assisted';
            return 'single';
        };

        const conditionInstructions = {
            type: jsPsychInstructions,
            pages: () => [`
                <div class='instructions'>
                    <h2>Your Task</h2>
                    <p>You will be shown a series of social media posts.</p>
                    <p>Your job is to decide whether each one should be <b>allowed</b> or <b>removed</b> from the platform.</p>
                    <br>
                    <p>Click <b>Next</b> to continue to a practice trial.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(conditionInstructions);

        // ========== PRACTICE TRIAL ==========
        const practiceTrial = {
            type: jsPsychModerationTrial,
            original_text: "Climate change is a pressing issue that requires immediate attention and action.",
            mirror_text: "Climate change is exaggerated, and we should not rush into costly policies.",
            show_pair: () => getPhaseMode(1) !== 'single',
            evaluation_mode: () => getPhaseMode(1),
            prompt: () => getPhaseMode(1) === 'linked_fate' ? "Allow Both or Remove Both?" : "Allow or Remove?",
            keep_label: "Allow",
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
                    <p>There will be <b>2 sections</b> with <b>${TRIALS_PER_PHASE} trials each</b>, for a total of <b>${NUM_TRIALS} trials (posts to evaluate)</b>. 
                    <br>
                    There will be a short break in between.</p>
                    <br>
                    <p>Click <b>Next</b> to begin.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(readyToBegin);
        
        // ========== PHASE 1 TRIALS ==========
        for (let i = 0; i < TRIALS_PER_PHASE; i++) {
            const trialIndex = i;
            const moderationTrial = {
                type: jsPsychModerationTrial,
                post_id: () => assignedPosts[trialIndex]?.post_primary_key || '',
                post_number: () => assignedPosts[trialIndex]?.post_number || '',
                context_post_id: '',
                context_post_number: '',
                sampled_stance: () => assignedPosts[trialIndex]?.sampled_stance || '',
                sample_toxicity_type: () => assignedPosts[trialIndex]?.sample_toxicity_type || '',
                original_text: () => assignedPosts[trialIndex]?.original_text || '',
                mirror_text: () => assignedPosts[trialIndex]?.claude_mirror || '',
                show_pair: () => getPhaseMode(1) !== 'single',
                evaluation_mode: () => getPhaseMode(1),
                prompt: () => getPhaseMode(1) === 'linked_fate' ? "Allow Both or Remove Both?" : "Allow or Remove?",
                keep_label: "Allow",
                remove_label: "Remove",
                trial_number: i + 1,
                total_trials: TRIALS_PER_PHASE,
                data: { trial_type: 'moderation-trial', phase: 1 },
                // Skip this trial if no post is assigned
                conditional_function: () => {
                    const hasPost = assignedPosts[trialIndex] && assignedPosts[trialIndex].original_text;
                    if (trialIndex === 0) {
                        console.log('Starting phase 1 with', assignedPosts.length, 'assigned posts');
                    }
                    return hasPost;
                }
            };
            timeline.push(moderationTrial);
        }

        // ========== PHASE BREAK ==========
        timeline.push({
            type: jsPsychInstructions,
            pages: () => [`
                <div class='instructions'>
                    <h2>Break</h2>
                    <p>You have completed Section 1.</p>
                    ${assignedCondition === 'control'
                        ? `<p>Take a short break if you would like, then click <b>Next</b> to continue to Section 2.</p>`
                        : assignedCondition === 'training'
                            ? `<p>In Section 2, the task will be essentially the same, except you will only be evaluating <b>one post at a time</b>.</p>
                               <p>Take a short break if you would like, then click <b>Next</b> to continue.</p>`
                            : `<p>In Section 2, the task will be essentially the same, except you will make a decision about only <b>one</b> of the two posts shown. The post you should evaluate will be clearly indicated.</p>
                               <p>Take a short break if you would like, then click <b>Next</b> to continue.</p>`
                    }
                </div>
            `],
            show_clickable_nav: true
        });

        // ========== PHASE 2 TRIALS ==========
        for (let i = 0; i < TRIALS_PER_PHASE; i++) {
            const trialIndex = i + TRIALS_PER_PHASE;
            const moderationTrial = {
                type: jsPsychModerationTrial,
                post_id: () => assignedPosts[trialIndex]?.post_primary_key || '',
                post_number: () => assignedPosts[trialIndex]?.post_number || '',
                context_post_id: () => getPhaseMode(2) === 'assisted' ? (assistedContextPosts[i]?.post_primary_key || '') : '',
                context_post_number: () => getPhaseMode(2) === 'assisted' ? (assistedContextPosts[i]?.post_number || '') : '',
                sampled_stance: () => assignedPosts[trialIndex]?.sampled_stance || '',
                sample_toxicity_type: () => assignedPosts[trialIndex]?.sample_toxicity_type || '',
                original_text: () => assignedPosts[trialIndex]?.original_text || '',
                mirror_text: () => {
                    if (getPhaseMode(2) === 'assisted') {
                        return assistedContextPosts[i]?.claude_mirror || '';
                    }
                    return assignedPosts[trialIndex]?.claude_mirror || '';
                },
                show_pair: () => getPhaseMode(2) !== 'single',
                evaluation_mode: () => getPhaseMode(2),
                prompt: "Allow or Remove?",
                keep_label: "Allow",
                remove_label: "Remove",
                trial_number: i + 1,
                total_trials: TRIALS_PER_PHASE,
                data: { trial_type: 'moderation-trial', phase: 2 },
                conditional_function: () => {
                    return assignedPosts[trialIndex] && assignedPosts[trialIndex].original_text;
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
        timeline.push(attitudeExtremitySurvey);

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
