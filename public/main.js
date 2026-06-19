/**
 * MirrorView Experiment - AWS Production Version
 *
 * Participants act as content moderators. In the control condition, they
 * evaluate single posts. In the linked-fate condition, they evaluate paired
 * original + mirror posts and make one decision that applies to both.
 */

let currentProlificID = null;
let isTestParticipant = false;

/**
 * Central study-design constants. Single place to align trial counts, conditions, post catalog, and IDs.
 *
 * Cross-repo / Lambda alignment (change these here and mirror elsewhere as noted):
 * - lambda-get-post-assignments.mjs — should accept the same condition strings in responses; validate
 *   assignedPostIds.length === postsPerParticipant; forwards party_group / prolific_id plus STUDY_ID /
 *   STUDY_ITERATION_ID to the assignment Lambda.
 * - lambda-save-jspsych-data.mjs — does not read this object; persisted condition comes from jsPsych CSV columns.
 * - study_participant_assignment_interface/lambdas/get_study_assignment/handler.py — DEFAULT_STUDY_CONDITIONS and
 *   precomputed CSV rows (assignedPostIds per row) must match conditions + postsPerParticipant + post ID semantics.
 */
const STUDY_SPEC = Object.freeze({
    /** Written to jsPsych data as experiment_version. Used only in public/main.js (assignParticipantId). */
    experimentVersion: 'mirrorview_scaled_2026_06_18',

    /** Prolific participant ID query key. Used only in public/main.js (setupExperiment URL parsing). */
    prolificUrlQueryParam: 'PROLIFIC_PID',

    /** Optional debug override for assigned condition. Used in public/main.js; sent in assignment POST body (lambda may ignore). */
    conditionUrlQueryParam: 'condition',

    /**
     * Allowed condition slugs.
     * Must match lambda-get-post-assignments validation and handler.py DEFAULT_STUDY_CONDITIONS.
     */
    conditions: Object.freeze(['training_assisted']),

    /** Condition id for linked-fate single phase. Used in public/main.js (instructions, condition_phase_modes key). */
    CONDITION_CONTROL: 'control',
    CONDITION_TRAINING: 'training',
    CONDITION_TRAINING_ASSISTED: 'training_assisted',

    /**
     * Maps each condition to jsPsych moderation trial evaluation_mode per section.
     * Values: "single", "linked_fate", "assisted".
     */
    condition_phase_modes: Object.freeze({
        training_assisted: Object.freeze({
            phase_1: 'linked_fate',
        }),
    }),

    /** Moderation trials in the single section. */
    trialsPerPhase: 20,
    /** Number of sections (phases of the task). */
    numPhases: 1,
    /** Total evaluated posts per participant; must equal trialsPerPhase * numPhases. */
    numTrials: 20,
    /** Same as numTrials; must match precomputed assignment row length. */
    postsPerParticipant: 20,

    /** Path under public/ for the stimulus catalog fetch (deployed to S3). */
    postCatalogPath: 'img/flips_scaled_2026_06_18.csv',
    /** CSV column used as canonical post id. */
    postIdField: 'post_primary_key',
    /** CSV column for display numeric id (optional; flips.csv has no post_number). */
    postNumberField: 'post_number',
    /** CSV column for mirror text. */
    mirrorTextField: 'mirrored_text',
});

if (STUDY_SPEC.numTrials !== STUDY_SPEC.trialsPerPhase * STUDY_SPEC.numPhases) {
    throw new Error('STUDY_SPEC: numTrials must equal trialsPerPhase * numPhases');
}
if (STUDY_SPEC.postsPerParticipant !== STUDY_SPEC.numTrials) {
    throw new Error('STUDY_SPEC: postsPerParticipant must equal numTrials for this study');
}

const ALLOWED_EVALUATION_MODES = new Set(['single', 'linked_fate', 'assisted']);
for (const cond of STUDY_SPEC.conditions) {
    const row = STUDY_SPEC.condition_phase_modes[cond];
    if (!row) {
        throw new Error(`STUDY_SPEC: condition_phase_modes missing entry for condition "${cond}"`);
    }
    for (let phaseNum = 1; phaseNum <= STUDY_SPEC.numPhases; phaseNum++) {
        const key = `phase_${phaseNum}`;
        if (!ALLOWED_EVALUATION_MODES.has(row[key])) {
            throw new Error(`STUDY_SPEC: condition_phase_modes.${cond}.${key} must be one of ${[...ALLOWED_EVALUATION_MODES].join(', ')}`);
        }
    }
}

function getPostNumber(post) {
    if (!post) return '';
    const num = post[STUDY_SPEC.postNumberField];
    if (num !== undefined && num !== null && String(num).trim() !== '') {
        return String(num);
    }
    return post[STUDY_SPEC.postIdField] || '';
}

function getMirrorText(post) {
    if (!post) return '';
    return post[STUDY_SPEC.mirrorTextField] || '';
}

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
            'phase1_pair_reflection_text',
            'phase1_pair_influence_rating',
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
        
        if (!endpoint || endpoint === 'TBD') {
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
                isTest: isTestParticipant
            })
        })
        .then(async response => {
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Save request failed (${response.status}): ${errorText}`);
            }
            return response.json();
        })
        .then(result => {
            console.log('Data saved:', result);
            // Redirect to Prolific completion URL if available
            const prolificCompletionUrl = urls.PROLIFIC_COMPLETION_URL;
            const prolificCompletionLink = window.config?.PROLIFIC_COMPLETION_LINK;
            const prolificCompletionCode = window.config?.PROLIFIC_COMPLETION_CODE || 'CE5XLP3L';
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
                            <a href="${prolificCompletionLink}" target="_blank">
                                <b>Click here</b>
                            </a>
                            to be redirected to Prolific (completion code <b>${prolificCompletionCode}</b>).
                        </p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error saving data:', error);
            renderFatalError(
                'Error',
                'There was an error saving your data. Please contact the researcher.',
                `Error: ${error.message}`
            );
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
        const response = await fetch(STUDY_SPEC.postCatalogPath);
        const csvText = await response.text();
        
        // Parse CSV properly handling quoted fields with newlines
        const data = parseCSV(csvText);
        
        // Filter to only rows with valid data
        // Each row represents one post with its Claude mirror
        const mirrorField = STUDY_SPEC.mirrorTextField;
        const validData = data.filter(row =>
            row.original_text &&
            row.original_text.trim() !== '' &&
            row[mirrorField] &&
            row[mirrorField].trim() !== ''
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

function renderFatalError(title, message, details = '') {
    const detailHtml = details
        ? `<p style="color: #9ca3af; font-size: 14px;">${details}</p>`
        : '';
    document.body.innerHTML = `
        <div style="text-align: center; margin-top: 100px; font-family: system-ui, sans-serif;">
            <h1 style="color: #dc2626;">${title}</h1>
            <p>${message}</p>
            ${detailHtml}
        </div>
    `;
}


// ============================================================
// GLOBAL STATE
// ============================================================

// Store all mirror data (loaded at start)
let allMirrorData = [];

// Store assigned posts (populated after political affiliation)
let assignedPosts = [];

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
        const prolificPID = urlParams.get(STUDY_SPEC.prolificUrlQueryParam);
        currentProlificID = prolificPID || 'UNKNOWN_' + Date.now();
        isTestParticipant = !prolificPID;
        console.log('Prolific ID:', currentProlificID, isTestParticipant ? '(test)' : '');
        const conditionParam = (urlParams.get(STUDY_SPEC.conditionUrlQueryParam) || '').toLowerCase();
        if (STUDY_SPEC.conditions.includes(conditionParam)) {
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
                    num_trials: STUDY_SPEC.numTrials,
                    experiment_version: STUDY_SPEC.experimentVersion
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
                        throw new Error('Could not determine party_group for assignment request');
                    }
                    
                    // Get the post assignments endpoint from config
                    const postAssignmentUrl = urls.POST_ASSIGNMENTS_URL;
                    const studyId = urls.STUDY_ID;
                    const studyIterationId = urls.STUDY_ITERATION_ID;
                    
                    if (!postAssignmentUrl || postAssignmentUrl === 'TBD') {
                        throw new Error('No POST_ASSIGNMENTS_URL configured');
                    }
                    if (!studyId) {
                        throw new Error('No STUDY_ID configured');
                    }
                    if (!studyIterationId) {
                        throw new Error('No STUDY_ITERATION_ID configured');
                    }
                    
                    // Call the server to get assigned posts
                    const response = await fetch(postAssignmentUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            prolificId: currentProlificID,
                            partyGroup: partyGroup,
                            condition: requestedConditionOverride || assignedCondition,
                            isTest: isTestParticipant,
                            STUDY_ID: studyId,
                            STUDY_ITERATION_ID: studyIterationId
                        })
                    });
                    
                    // validate the response from the post assignment lambda
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`Post assignment request failed (${response.status}): ${errorText}`);
                    }

                    const result = await response.json();

                    if (!Array.isArray(result.assignedPostIds)) {
                        throw new Error('Assignment response did not include assignedPostIds array');
                    }

                    const idField = STUDY_SPEC.postIdField;
                    const assignedPostLookup = new Map(
                        allMirrorData.map(post => [post[idField], post])
                    );
                    const missingPostIds = result.assignedPostIds.filter(
                        postId => !assignedPostLookup.has(postId)
                    );
                    if (missingPostIds.length > 0) {
                        throw new Error(
                            `Assignment response contained unknown post IDs: ${missingPostIds.join(', ')}`
                        );
                    }

                    assignedPosts = result.assignedPostIds.map(postId => assignedPostLookup.get(postId));
                    if (assignedPosts.length !== STUDY_SPEC.postsPerParticipant) {
                        throw new Error(
                            `Expected ${STUDY_SPEC.postsPerParticipant} assigned posts, received ${assignedPosts.length}`
                        );
                    }

                    assignedCondition = result.condition || assignedCondition;
                    if (!assignedCondition) {
                        throw new Error('No condition assigned');
                    }
                    jsPsych.data.addProperties({ condition: assignedCondition });

                    done();
                } catch (error) {
                    console.error('Error fetching post assignments:', error);
                    renderFatalError(
                        'Assignment Error',
                        'There was an error loading your assigned posts. Please contact the researcher.',
                        `Error: ${error.message}`
                    );
                    done();
                }
            }
        };
        timeline.push(fetchAssignedPosts);

        /** Thin lookup into STUDY_SPEC.condition_phase_modes[assignedCondition] (no branching on condition name). */
        const getPhaseMode = (phaseNumber) => {
            const modes = STUDY_SPEC.condition_phase_modes[assignedCondition];
            if (!modes) {
                throw new Error(`condition_phase_modes missing for condition: ${assignedCondition}`);
            }
            return phaseNumber === 1 ? modes.phase_1 : modes.phase_2;
        };

        /** "Allow both" / "Remove both" only when the table says linked_fate for that phase. */
        const useBothDecisionLabels = (phaseNumber) => getPhaseMode(phaseNumber) === 'linked_fate';

        const conditionInstructions = {
            type: jsPsychInstructions,
            pages: () => [`
                <div class='instructions'>
                    <h2>Your Task</h2>
                    ${assignedCondition === STUDY_SPEC.CONDITION_CONTROL
                        // control
                        ? `<p>We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated.</p>
                           <p>Your task is to review a series of real political social media posts and decide whether they should be <b>allowed</b> or <b>removed</b> from the platform.</p>
                           <p>When making your decisions, consider generally whether a post contributes to a <b>healthy environment for political discussion</b>, or whether it would be <b>unhealthy for political discussion</b>. Your goal is to evaluate the messages, using your own judgment.</p>
                           <p>There are no right or wrong answers - we are interested in what you personally think.</p>`
                        // training, training_assisted
                        : `<p>We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. 
                            Your task will be to review a series of <b>pairs</b> of real political social media posts, and decide whether <b>both posts in the pair</b> should be <b>allowed</b> or <b>removed</b> from the platform.</p>
                           <br>
                           <p>The pairs are <b>political mirrors</b> of each other. This means that the mirror text <b>recreates the original message</b> from the <b>opposite political stance</b>. For example:</p>
                           <p><b>Original Text:</b><br>
                           <i>I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!</i></p>
                           <p><b>Mirror Text:</b><br>
                           <i>I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!</i></p>
                           <p>Notice that the mirror text changes the core message to match that of the opposite political stance.
                              In other words, the mirror text is <b>not a response to the original text</b> - it replicates the original message as if written from the opposite political stance.</p>
                            <br>
                           <p>Your job is to decide whether <b>both posts in the pair</b> should be <b>allowed</b> or <b>removed</b> from the platform.</p>
                           <p>When making your decisions, consider generally whether a post contributes to a <b>healthy environment for political discussion</b>, or whether it would be <b>unhealthy for political discussion</b>. Your goal is to evaluate the messages, using your own judgment.</p>
                           <p>There are no right or wrong answers - we are interested in what you personally think.</p>`
                    }
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
            prompt: "Allow or Remove?",
            allow_label: () => useBothDecisionLabels(1) ? "Allow Both" : "Allow",
            remove_label: () => useBothDecisionLabels(1) ? "Remove Both" : "Remove",
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
                    ${STUDY_SPEC.numPhases === 1
                        ? `<p>You will evaluate <b>${STUDY_SPEC.numTrials} posts</b> in total.</p>`
                        : `<p>There will be <b>${STUDY_SPEC.numPhases} sections</b> with <b>${STUDY_SPEC.trialsPerPhase} trials each</b>, for a total of <b>${STUDY_SPEC.numTrials} trials (posts to evaluate)</b>.
                    <br>
                    There will be a short break in the middle after ${STUDY_SPEC.trialsPerPhase} trials.</p>`
                    }
                    <br>
                    <p>Click <b>Next</b> to begin.</p>
                </div>
            `],
            show_clickable_nav: true
        };
        timeline.push(readyToBegin);
        
        // ========== PHASE 1 TRIALS ==========
        for (let i = 0; i < STUDY_SPEC.trialsPerPhase; i++) {
            const trialIndex = i;
            const moderationTrial = {
                type: jsPsychModerationTrial,
                post_id: () => assignedPosts[trialIndex]?.[STUDY_SPEC.postIdField] || '',
                post_number: () => getPostNumber(assignedPosts[trialIndex]),
                context_post_id: '',
                context_post_number: '',
                sampled_stance: () => assignedPosts[trialIndex]?.sampled_stance || '',
                sample_toxicity_type: () => assignedPosts[trialIndex]?.sample_toxicity_type || '',
                original_text: () => assignedPosts[trialIndex]?.original_text || '',
                mirror_text: () => getMirrorText(assignedPosts[trialIndex]),
                show_pair: () => getPhaseMode(1) !== 'single',
                evaluation_mode: () => getPhaseMode(1),
                prompt: "Allow or Remove?",
                allow_label: () => useBothDecisionLabels(1) ? "Allow Both" : "Allow",
                remove_label: () => useBothDecisionLabels(1) ? "Remove Both" : "Remove",
                trial_number: i + 1,
                total_trials: STUDY_SPEC.trialsPerPhase,
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

        // ========== PHASE 1 REFLECTION (TRAINING CONDITIONS ONLY) ==========
        timeline.push({
            timeline: [{
                type: jsPsychSurveyHtmlForm,
                preamble: "<h2>Section 1 Reflection</h2>",
                html: `
                    <div class="survey-container">
                        <div class="survey-question">
                            <label for="phase1_pair_reflection_text" style="font-weight: normal;">
                                You just completed a series of content moderation decisions where you saw pairs of posts expressing opposing political viewpoints on the same topic - one from a left-leaning perspective and one from a right-leaning perspective - and made a single joint decision about both. In a few sentences, please describe what was going through your mind as you made these decisions. What, if anything, influenced how you evaluated the posts as a pair?
                            </label>
                            <textarea
                                id="phase1_pair_reflection_text"
                                name="phase1_pair_reflection_text"
                                rows="6"
                                style="width: 100%; margin-top: 8px;"
                                required
                            ></textarea>
                        </div>
                    </div>
                    <div class="survey-container">
                        <div class="survey-question">
                            <div style="font-weight: normal; margin-bottom: 10px;">
                                To what extent did seeing both versions of each post influence your decisions? (1 = Not at all, 7 = Very much)
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="1" required>
                                    <span style="margin-top: 4px;">1</span>
                                    <span style="font-size: 13px; color: #555;">Not at all</span>
                                </label>
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="2">
                                    <span style="margin-top: 4px;">2</span>
                                </label>
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="3">
                                    <span style="margin-top: 4px;">3</span>
                                </label>
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="4">
                                    <span style="margin-top: 4px;">4</span>
                                    <span style="font-size: 13px; color: #555;">Somewhat</span>
                                </label>
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="5">
                                    <span style="margin-top: 4px;">5</span>
                                </label>
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="6">
                                    <span style="margin-top: 4px;">6</span>
                                </label>
                                <label style="display: flex; flex-direction: column; align-items: center; font-weight: normal;">
                                    <input type="radio" name="phase1_pair_influence_rating" value="7">
                                    <span style="margin-top: 4px;">7</span>
                                    <span style="font-size: 13px; color: #555;">Very much</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                button_label: "Next >",
                data: { trial_type: 'phase1-reflection-survey', phase: 1 }
            }],
            conditional_function: () => getPhaseMode(1) === 'linked_fate'
        });

        // ========== PHASE BREAK (multi-phase studies only) ==========
        if (STUDY_SPEC.numPhases > 1) {
        timeline.push({
            type: jsPsychInstructions,
            pages: () => [`
                <div class='instructions'>
                    <h2>Break</h2>
                    <p>You have completed Section 1.</p>
                    ${assignedCondition === STUDY_SPEC.CONDITION_CONTROL
                        ? `<p>Take a short break if you would like, then click <b>Next</b> to continue to Section 2.</p>`
                        : assignedCondition === STUDY_SPEC.CONDITION_TRAINING
                            ? `<p>In Section 2, the task will be essentially the same, except you will only be evaluating <b>one post at a time</b>.</p>
                               <p>Take a short break if you would like, then click <b>Next</b> to continue.</p>`
                            : `<p>In Section 2, the task will be essentially the same, except you will only be evaluating <b>one post at a time</b>.</p>
                               <p>Underneath the post, you will be provided with its <b>political mirror</b>, in case it helps you make your decision.</p>
                               <p>Take a short break if you would like, then click <b>Next</b> to continue.</p>`
                    }
                </div>
            `],
            show_clickable_nav: true
        });

        // ========== PHASE 2 TRIALS ==========
        for (let i = 0; i < STUDY_SPEC.trialsPerPhase; i++) {
            const trialIndex = i + STUDY_SPEC.trialsPerPhase;
            const moderationTrial = {
                type: jsPsychModerationTrial,
                post_id: () => assignedPosts[trialIndex]?.[STUDY_SPEC.postIdField] || '',
                post_number: () => getPostNumber(assignedPosts[trialIndex]),
                context_post_id: '',
                context_post_number: '',
                sampled_stance: () => assignedPosts[trialIndex]?.sampled_stance || '',
                sample_toxicity_type: () => assignedPosts[trialIndex]?.sample_toxicity_type || '',
                original_text: () => assignedPosts[trialIndex]?.original_text || '',
                mirror_text: () => getMirrorText(assignedPosts[trialIndex]),
                show_pair: () => getPhaseMode(2) !== 'single',
                evaluation_mode: () => getPhaseMode(2),
                prompt: "Allow or Remove?",
                allow_label: () => useBothDecisionLabels(2) ? "Allow Both" : "Allow",
                remove_label: () => useBothDecisionLabels(2) ? "Remove Both" : "Remove",
                trial_number: i + 1,
                total_trials: STUDY_SPEC.trialsPerPhase,
                data: { trial_type: 'moderation-trial', phase: 2 },
                conditional_function: () => {
                    return assignedPosts[trialIndex] && assignedPosts[trialIndex].original_text;
                }
            };
            timeline.push(moderationTrial);
        }
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
