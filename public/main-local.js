/**
 * MirrorView Experiment - Local Development Version
 * 
 * Participants view 5 "mirror" versions of political posts (1 human + 4 LLMs)
 * and select which mirror they prefer.
 * 
 * Each participant sees 20 randomly selected posts.
 * Mirror order is randomized for each trial.
 */

const jsPsych = initJsPsych({
    use_webaudio: false,
    on_finish: function() {
        let allData = jsPsych.data.get();
        
        // Filter to just the mirror preference trials for the main data
        const mirrorTrials = allData.filter({trial_type: 'mirror-preference'}).values();
        
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
            // Mirror preference specific
            'post_id',
            'human_mirror_id',  // Unique ID for this specific human mirror
            'original_text',
            'selected_mirror',
            'selected_position',
            'presentation_order',
            'response_time_ms',
            'selection_time_ms',
            'hover_data',
            // Participant info
            'participant_id',
            'prolific_id',
            'consented',
            // Demographics (if collected)
            'age',
            'gender',
            'education'
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
        const urls = window.config?.getUrls?.() || {};
        const endpoint = urls.SAVE_DATA_URL || '/save-jspsych-data';
        
        console.log('Saving data to:', endpoint);
        
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ csv: csv })
        })
        .then(response => response.json())
        .then(result => {
            console.log('Data saved:', result);
            // Show completion message
            document.body.innerHTML = `
                <div style="text-align: center; margin-top: 100px; font-family: system-ui, sans-serif;">
                    <h1 style="color: #16a34a;">Thank you!</h1>
                    <p style="font-size: 18px; color: #4b5563;">Your responses have been recorded.</p>
                    <p style="color: #9ca3af;">You may now close this window.</p>
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
        const response = await fetch('img/all_mirrors.csv');
        const csvText = await response.text();
        
        // Parse CSV properly handling quoted fields with newlines
        const data = parseCSV(csvText);
        
        // Filter to only rows with valid data
        // Each row represents one post with its human mirror and 4 LLM mirrors
        const validData = data.filter(row => 
            row.original_text && 
            row.original_text.trim() !== '' &&
            row.human_mirror_id &&  // ID of the selected human mirror for this post
            row.human_mirror &&
            row.human_mirror.trim() !== ''
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

/**
 * Randomly sample n items from an array
 */
function sampleArray(array, n) {
    const shuffled = [...array].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, Math.min(n, array.length));
}


// ============================================================
// EXPERIMENT CONFIGURATION
// ============================================================

const NUM_TRIALS = 20; // Number of posts each participant rates


// ============================================================
// MAIN EXPERIMENT SETUP
// ============================================================

async function setupExperiment() {
    try {
        // Get URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const prolificID = urlParams.get('PROLIFIC_PID') || 'TEST_' + Date.now();
        console.log('Prolific ID:', prolificID);
        
        // Load mirror data
        const mirrorData = await loadMirrorData();
        
        // Sample posts for this participant
        const selectedPosts = sampleArray(mirrorData, NUM_TRIALS);
        console.log(`Selected ${selectedPosts.length} posts for this participant`);
        
        // Build timeline
        const timeline = [];
        
        // ========== WELCOME ==========
        const welcome = {
            type: jsPsychInstructions,
            pages: [`
                <div class='instructions'>
                    <h2>Welcome!</h2>
                    <p>In this study, you will read different versions of social media posts and tell us which version you prefer.</p>
                    <p>Each post has been rewritten in 5 different ways. Your task is to <b>read all 5 versions</b> and <b>click on the one you like best</b>.</p>
                    <p>You will complete <b>${NUM_TRIALS} trials</b> in total. This should take approximately 10-15 minutes.</p>
                    <br>
                    <p>Click <b>Next</b> to continue to the consent form.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(welcome);
        
        // ========== CONSENT ==========
        timeline.push(consent);
        
        // ========== INSTRUCTIONS ==========
        const instructions = {
            type: jsPsychInstructions,
            pages: [
                `<div class='instructions'>
                    <h2>Task Instructions</h2>
                    <p>On each trial, you will see <b>5 different versions</b> of a rewritten social media post.</p>
                    <p>These versions were written by different people (some human, some AI) who were asked to "flip" the perspective of an original post.</p>
                    <p><b>Your job:</b></p>
                    <ul style="text-align: left; max-width: 600px; margin: 0 auto;">
                        <li>Read through all 5 versions</li>
                        <li>Click on the version you prefer most</li>
                        <li>Then click "Next" to continue</li>
                    </ul>
                    <p>There are no right or wrong answers — we're interested in your personal preference!</p>
                </div>`,
                `<div class='instructions'>
                    <h2>Ready to Begin</h2>
                    <p>You will now start the main task.</p>
                    <p>Remember: <b>click on the version you prefer</b>, then click <b>Next</b> to continue.</p>
                    <p>Click <b>Next</b> when you're ready to start!</p>
                </div>`
            ],
            show_clickable_nav: true
        };
        timeline.push(instructions);
        
        // ========== ASSIGN PARTICIPANT ID ==========
        let ParticipantID = 'P_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const assignId = {
            type: jsPsychCallFunction,
            func: function() {
                jsPsych.data.addProperties({
                    participant_id: ParticipantID,
                    prolific_id: prolificID,
                    num_trials: NUM_TRIALS,
                    experiment_version: 'mirrorView_v1'
                });
            }
        };
        timeline.push(assignId);
        
        // ========== MIRROR PREFERENCE TRIALS ==========
        // Each post shows 5 mirrors: 1 human + 4 LLMs
        selectedPosts.forEach((post, index) => {
            const trial = {
                type: jsPsychMirrorPreference,
                post_id: post.post_primary_key,
                human_mirror_id: post.human_mirror_id,  // Unique ID for this specific human mirror
                original_text: post.original_text,
                human_mirror: post.human_mirror,
                llm_mirrors: {
                    llama: post.llama_mirror,
                    qwen: post.qwen_mirror,
                    claude: post.claude_mirror,
                    gpt4o: post.gpt4o_mirror
                },
                show_original: true,
                prompt: "Which mirror do you prefer?",
                button_label: "Next →",
                trial_number: index + 1,
                total_trials: NUM_TRIALS
            };
            timeline.push(trial);
        });
        
        // ========== BRIEF DEMOGRAPHICS (optional) ==========
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
            button_label: "Submit →"
        };
        timeline.push(demographics);
        
        // ========== THANK YOU ==========
        const thankYou = {
            type: jsPsychHtmlButtonResponse,
            stimulus: `
                <div class='instructions'>
                    <h2>Thank You!</h2>
                    <p>You have completed the study.</p>
                    <p>Your responses are being saved...</p>
                </div>
            `,
            choices: ['Finish'],
            on_finish: function() {
                // Data saving is handled by on_finish in jsPsych init
            }
        };
        timeline.push(thankYou);
        
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
