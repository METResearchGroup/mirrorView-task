/**
 * MirrorView Experiment - AWS Production Version
 * 
 * Participants view 5 "mirror" versions of political posts (1 human + 4 LLMs)
 * and select which mirror they prefer.
 * 
 * Each participant sees 5 posts assigned based on their political affiliation.
 * Posts are assigned to ensure 3 democrats + 3 republicans rate each post.
 * Mirror order is randomized for each trial.
 */

let currentProlificID = null;
let isTestParticipant = false;

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

        // Add attention check attempts as a dedicated column
        allTrials.forEach(trial => {
            if (trial.trial_type === 'mirror-practice' && trial.attempts !== undefined) {
                trial.attention_check_attempts = trial.attempts;
            }
        });
        
        // Define columns to keep
        const columnsToKeep = [
            'trial_type',
            'trial_index',
            'time_elapsed',
            'rt',
            // Mirror preference specific
            'post_id',
            'post_number',      // Numeric post identifier (easier to reference)
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
            'political_affiliation',
            'party_lean',
            'party_group',
            // Demographics (if collected)
            'age',
            'gender',
            'education',
            // Political attitudes (if collected)
            'political_ideology',
            'political_follow',
            'rep_id',
            'dem_id'
            ,
            // Attention check (practice) attempts
            'attention_check_attempts'
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
                            <a href="https://app.prolific.com/submissions/complete?cc=CV0XRWGP" target="_blank">
                                <b>Click here</b>
                            </a>
                            to be redirected to Prolific (completion code <b>CV0XRWGP</b>).
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


// ============================================================
// EXPERIMENT CONFIGURATION
// ============================================================

const NUM_TRIALS = 5; // Number of posts each participant rates


// ============================================================
// GLOBAL STATE
// ============================================================

// Store all mirror data (loaded at start)
let allMirrorData = [];

// Store assigned posts (populated after political affiliation)
let assignedPosts = [];


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
                    <p>We're developing an AI tool that will help people think about political messages from different points of view.</p>
                    <p>It works by generating "mirrors" of political text from social media.</p>
                    <p>For example, when prompted with a <b>left-leaning social media post</b>, the AI should generate the same message, as if the post was written from a <b>right-leaning perspective</b> (and vice versa).</p>
                    <br>
                    <p>Click <b>Next</b> to continue to an example.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(welcome);

        const welcome2 = {
            type: jsPsychInstructions,
            pages: [`
                <div class='instructions'>
                    <h2>Example</h2>
                    <p>Here is an example of a <b>good mirror</b>:</p>
                    <br>
                    <p><b>Original Text:</b> "I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!"</p>
                    <p><b>Mirror Text:</b> "I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!"</p>
                    <br>
                    <p>Notice that the mirror text <b>recreates</b> the original message, but <b>from the opposite political stance</b> (original text is clearly liberal, and the mirror text is clearly conservative).
                    Also notice that it <b>changed the core message</b> to one consistent with a conservative stance when the original was liberal. In other words, the mirror text is not a response to the original text, 
                    it is just <b>replicating the original message as if written from an opposite political stance</b>.</p>
                    <br>
                    <p>In this study, your job is to choose the "mirrored" message that you believe accomplishes this job the best for a given social media post.</p>
                    <br>
                    <p>Click <b>Next</b> to continue to a practice trial.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(welcome2);

        // ========== PRACTICE TRIAL ==========
        const practiceTrial = {
            type: jsPsychMirrorPractice,
            original_text: "Climate change is a pressing issue that requires immediate attention and action, and it's essential to address the root causes of this problem.",
            options: [
                {
                    id: 'wrong1',
                    text: "Climate change is a pressing issue and the main cause of it is human-based carbon emissions!"
                },
                {
                    id: 'correct',
                    text: "Climate change is not as serious as the left claims, and we shouldn't rush into policies that hurt American jobs."
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
        
        // ========== POLITICAL AFFILIATION CONFIRMATION ==========
        // (defined in pre_surveys.js)
        timeline.push(politicalAffiliation);
        
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
                    
                    // Get all posts with both ID and number
                    const allPosts = allMirrorData.map(p => ({
                        post_id: p.post_primary_key,
                        post_number: p.post_number
                    }));
                    
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
        
        // ========== READY TO BEGIN ==========
        const readyToBegin = {
            type: jsPsychInstructions,
            pages: [`
                <div class='instructions'>
                    <h2>Great! You're ready to begin.</h2>
                    <p>The real study will be just like the practice, except that you will choose 1 out of <b>5</b> mirror texts that you think is best. 
                    There will be <b>${NUM_TRIALS} trials</b> in total. If several of them look like good mirrors to you, just use your gut to pick the best 
                    one based on our definition of a good mirror.</p>
                    <p>It should take you approximately 10 minutes to finish the task.</p>
                    <br>
                    <p>Reminder:</p>
                    <p>A good mirror is a message that <b>recreates the original message</b>, but from the <b>opposite political stance</b>. It should also maintain the same <b>structure</b> and <b>tone</b> as the original message.</p>
                    <p>For example:</p>
                    <p><b>Original Text:</b> "I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!"</p>
                    <p><b>Mirror Text:</b> "I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!"</p>
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
                    experiment_version: 'mirrorView_v2'
                });
            }
        };
        timeline.push(assignId);
        
        // ========== MIRROR PREFERENCE TRIALS ==========
        // Generate trials dynamically from assignedPosts
        // Each trial is added individually since timeline_variables can't be set dynamically
        for (let i = 0; i < NUM_TRIALS; i++) {
            const trialIndex = i;
            const mirrorTrial = {
                type: jsPsychMirrorPreference,
                post_id: () => assignedPosts[trialIndex]?.post_primary_key || '',
                post_number: () => assignedPosts[trialIndex]?.post_number || '',
                human_mirror_id: () => assignedPosts[trialIndex]?.human_mirror_id || '',
                original_text: () => assignedPosts[trialIndex]?.original_text || '',
                human_mirror: () => assignedPosts[trialIndex]?.human_mirror || '',
                llm_mirrors: () => ({
                    llama: assignedPosts[trialIndex]?.llama_mirror || '',
                    qwen: assignedPosts[trialIndex]?.qwen_mirror || '',
                    claude: assignedPosts[trialIndex]?.claude_mirror || '',
                    gpt4o: assignedPosts[trialIndex]?.gpt4o_mirror || ''
                }),
                show_original: true,
                prompt: "Which mirror is the best?",
                button_label: "Next →",
                trial_number: i + 1,
                total_trials: NUM_TRIALS,
                // Skip this trial if no post is assigned
                conditional_function: () => {
                    const hasPost = assignedPosts[trialIndex] && assignedPosts[trialIndex].original_text;
                    if (trialIndex === 0) {
                        console.log('Starting mirror trials with', assignedPosts.length, 'posts');
                    }
                    return hasPost;
                }
            };
            timeline.push(mirrorTrial);
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
            button_label: "Next →"
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
