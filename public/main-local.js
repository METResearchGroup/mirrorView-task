/**
 * MirrorView Experiment - Local Development Version
 * 
 * Participants view 5 "mirror" versions of political posts (1 human + 4 LLMs)
 * and select which mirror they prefer.
 * 
 * Each participant sees 10 randomly selected posts.
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

const NUM_TRIALS = 10; // Number of posts each participant rates


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
                    <p>We're developing an AI tool that will help people think about political messages from different points of view.</p>
                    <p>It works by generating "mirrors" of political text from social media. For example, when prompted with a left-leaning social media post, the AI should generate the same message, as if the post was written from a right-leaning perspective.</p>
                    <br>
                    <p>For example:</p>
                    <p><b>Original Text:</b> "I'm a bleeding-heart liberal, and I think abortion is obviously about protecting women's rights!"</p>
                    <p><b>Mirror Text:</b> "I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!"</p>
                    <p>Notice that the mirror text tries to recreate the original message, but from the opposite political stance (original text is clearly liberal, and the mirror text is clearly conservative).
                    Also notice that it changed the core message to one consistent with a conservative stance when the original was liberal. In other words, the mirror text is not a response to the original text, 
                    it is just trying to replicate the original message as if written from an opposite political stance.</p>
                    <p>In this study, your job is to choose the “mirrored” message that you believe accomplishes this job the best for a given social media post.</p>
                    <br>
                    <p>Click <b>Next</b> to continue to a practice trial.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(welcome);

        // ========== PRACTICE TRIAL ==========
        const practiceTrial = {
            type: jsPsychMirrorPractice,
            original_text: "Climate change is a pressing issue that requires immediate attention and action, and it's essential to address the root causes of this problem.",
            options: [
                {
                    id: 'wrong1',
                    text: "Climate change is not as serious as the left claims, and we shouldn't rush into policies that hurt American jobs."
                },
                {
                    id: 'correct',
                    text: "Government overreach is a pressing issue that requires immediate attention and action, and it's essential to address the root causes of burdensome environmental regulations."
                },
                {
                    id: 'wrong2',
                    text: "The Second Amendment is a fundamental right that requires immediate protection, and it's essential to defend our constitutional freedoms."
                }
            ],
            correct_answer: 'correct',
            prompt: "Which of these 3 versions is the best mirror for the original text?",
            incorrect_feedback: "Try again!",
            correct_feedback: "Correct! This mirror maintains the same <b>structure</b> and <b>tone</b> as the original, while <b>flipping the political stance</b>.",
            button_label: "Continue to Consent Form →",
            shuffle_options: true,
            practice_label: "Practice Trial"
        };
        timeline.push(practiceTrial);

        // ========== CONSENT ==========
        timeline.push(consent);
        
        // ========== READY TO BEGIN ==========
        const readyToBegin = {
            type: jsPsychInstructions,
            pages: [`
                <div class='instructions'>
                    <h2>Great! You're ready to begin.</h2>
                    <p>The real study will be similar to the practice trial, except each post has been rewritten in <b>5 different ways</b>, and you will have to select the best mirror out of each of the 5 posts.</p>
                    <p>There will be <b>${NUM_TRIALS} trials</b> in total. It should take you approximately 10-15 minutes to finish the task.</p>
                    <br>
                    <p>Click <b>Next</b> to begin.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(readyToBegin);
        
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
