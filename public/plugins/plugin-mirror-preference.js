/**
 * Mirror Preference Plugin for jsPsych
 * 
 * Displays 5 mirror versions of a post (1 human + 4 LLMs) and lets 
 * participants select which one they prefer.
 * 
 * @author Meriel Doyle
 */

var jsPsychMirrorPreference = (function (jspsych) {
    "use strict";

    var _package = {
        name: "jspsych-plugin-mirror-preference",
        version: "1.0.0",
        description: "jsPsych plugin for displaying mirror text options and getting a preference selection",
        author: "Meriel Doyle",
        // license: "MIT"
    };

    const info = {
        name: "mirror-preference",
        version: _package.version,
        parameters: {
            /** The original post text (for context, may or may not be shown) */
            original_text: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** The unique identifier for this post */
            post_id: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** The numeric post number (easier reference than post_id) */
            post_number: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** The unique identifier for this specific human mirror */
            human_mirror_id: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** Human mirror text */
            human_mirror: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** LLM mirrors object with keys: llama, qwen, claude, gpt4o */
            llm_mirrors: {
                type: jspsych.ParameterType.OBJECT,
                default: {}
            },
            /** Whether to show the original post */
            show_original: {
                type: jspsych.ParameterType.BOOL,
                default: false
            },
            /** Prompt text to display */
            prompt: {
                type: jspsych.ParameterType.STRING,
                default: "Which version do you prefer?"
            },
            /** Button text for the next button */
            button_label: {
                type: jspsych.ParameterType.STRING,
                default: "Next"
            },
            /** Trial number (for display) */
            trial_number: {
                type: jspsych.ParameterType.INT,
                default: null
            },
            /** Total number of trials (for display) */
            total_trials: {
                type: jspsych.ParameterType.INT,
                default: null
            }
        },
        data: {
            /** The unique identifier for the post */
            post_id: {
                type: jspsych.ParameterType.STRING
            },
            /** The numeric post number (easier reference than post_id) */
            post_number: {
                type: jspsych.ParameterType.STRING
            },
            /** The unique identifier for this specific human mirror */
            human_mirror_id: {
                type: jspsych.ParameterType.STRING
            },
            /** The original post text */
            original_text: {
                type: jspsych.ParameterType.STRING
            },
            /** The mirror source that was selected (human, llama, qwen, claude, gpt4o) */
            selected_mirror: {
                type: jspsych.ParameterType.STRING
            },
            /** The position (1-5) of the selected mirror in the displayed order */
            selected_position: {
                type: jspsych.ParameterType.INT
            },
            /** The order in which mirrors were presented */
            presentation_order: {
                type: jspsych.ParameterType.OBJECT
            },
            /** Total time on the trial in milliseconds */
            response_time_ms: {
                type: jspsych.ParameterType.FLOAT
            },
            /** Time until selection was made in milliseconds */
            selection_time_ms: {
                type: jspsych.ParameterType.FLOAT
            },
            /** JSON string of hover data with timestamps */
            hover_data: {
                type: jspsych.ParameterType.STRING
            },
            /** The human mirror text */
            human_mirror: {
                type: jspsych.ParameterType.STRING
            },
            /** The Llama mirror text */
            llama_mirror: {
                type: jspsych.ParameterType.STRING
            },
            /** The Qwen mirror text */
            qwen_mirror: {
                type: jspsych.ParameterType.STRING
            },
            /** The Claude mirror text */
            claude_mirror: {
                type: jspsych.ParameterType.STRING
            },
            /** The GPT-4o mirror text */
            gpt4o_mirror: {
                type: jspsych.ParameterType.STRING
            }
        }
    };

    class MirrorPreferencePlugin {
        static info = info;

        constructor(jsPsych) {
            this.jsPsych = jsPsych;
        }

        trial(display_element, trial) {
            // Build the mirror options array
            const mirrorOptions = [
                { id: 'human', label: 'Human', text: trial.human_mirror },
                { id: 'gpt4o', label: 'GPT-4o Mini', text: trial.llm_mirrors.gpt4o },
                { id: 'claude', label: 'Claude 4.5 Haiku', text: trial.llm_mirrors.claude },
                { id: 'qwen', label: 'Qwen 3', text: trial.llm_mirrors.qwen },
                { id: 'llama', label: 'Llama 3.3', text: trial.llm_mirrors.llama }
            ];

            // Filter out any null/undefined mirrors
            const validMirrors = mirrorOptions.filter(m => m.text && m.text.trim() !== '');

            // Shuffle the order for this participant
            const shuffledMirrors = this.shuffleArray([...validMirrors]);

            // Store the presentation order
            const presentationOrder = shuffledMirrors.map(m => m.id);

            // Build progress indicator
            let progressHtml = '';
            if (trial.trial_number !== null && trial.total_trials !== null) {
                progressHtml = `<div class="mirror-progress">Trial ${trial.trial_number} of ${trial.total_trials}</div>`;
            }

            // Build the HTML
            let html = `
                <div class="mirror-preference-container">
                    ${progressHtml}
            `;

            // Always show the original text at the top
            if (trial.original_text) {
                html += `
                    <div class="original-post-label">Original Text</div>
                    <div class="original-post-container">
                        <div class="original-post-text">${trial.original_text}</div>
                    </div>
                `;
            }

            // Add the prompt for mirrors
            html += `<div class="mirror-prompt">${trial.prompt}</div>`;

            // Add mirror cards
            html += `<div class="mirror-cards-container">`;
            
            shuffledMirrors.forEach((mirror, index) => {
                html += `
                    <div class="mirror-card" data-mirror-id="${mirror.id}" data-position="${index + 1}">
                        <div class="mirror-card-number">${index + 1}</div>
                        <div class="mirror-card-text">${mirror.text}</div>
                    </div>
                `;
            });

            html += `</div>`;

            // Add next button (initially disabled)
            html += `
                <div class="mirror-button-container">
                    <button class="jspsych-btn mirror-next-btn" disabled>${trial.button_label}</button>
                </div>
            </div>
            `;

            display_element.innerHTML = html;

            // Track state
            let selectedMirror = null;
            let selectionTime = null;
            const startTime = performance.now();
            const hoverData = [];

            // Get elements
            const cards = display_element.querySelectorAll('.mirror-card');
            const nextBtn = display_element.querySelector('.mirror-next-btn');

            // Add hover tracking
            cards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    const mirrorId = card.dataset.mirrorId;
                    hoverData.push({
                        mirror_id: mirrorId,
                        event: 'enter',
                        time: performance.now() - startTime
                    });
                });

                card.addEventListener('mouseleave', () => {
                    const mirrorId = card.dataset.mirrorId;
                    hoverData.push({
                        mirror_id: mirrorId,
                        event: 'leave',
                        time: performance.now() - startTime
                    });
                });

                // Click to select
                card.addEventListener('click', () => {
                    // Remove selection from all cards
                    cards.forEach(c => c.classList.remove('selected'));
                    
                    // Select this card
                    card.classList.add('selected');
                    selectedMirror = card.dataset.mirrorId;
                    selectionTime = performance.now() - startTime;
                    
                    // Enable next button
                    nextBtn.disabled = false;
                });
            });

            // Handle next button click
            nextBtn.addEventListener('click', () => {
                if (selectedMirror === null) return;

                const endTime = performance.now();
                const responseTime = endTime - startTime;

                // Find the selected card's position
                const selectedCard = display_element.querySelector('.mirror-card.selected');
                const selectedPosition = selectedCard ? parseInt(selectedCard.dataset.position) : null;

                // Compile trial data
                const trialData = {
                    post_id: trial.post_id,
                    post_number: trial.post_number,
                    human_mirror_id: trial.human_mirror_id,  // Unique ID for this specific human mirror
                    original_text: trial.original_text,
                    selected_mirror: selectedMirror,
                    selected_position: selectedPosition,
                    presentation_order: presentationOrder,
                    response_time_ms: responseTime,
                    selection_time_ms: selectionTime,
                    hover_data: JSON.stringify(hoverData),
                    human_mirror: trial.human_mirror,
                    llama_mirror: trial.llm_mirrors.llama,
                    qwen_mirror: trial.llm_mirrors.qwen,
                    claude_mirror: trial.llm_mirrors.claude,
                    gpt4o_mirror: trial.llm_mirrors.gpt4o
                };

                // End trial
                display_element.innerHTML = '';
                this.jsPsych.finishTrial(trialData);
            });
        }

        // Fisher-Yates shuffle
        shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }
    }

    MirrorPreferencePlugin.info = info;

    return MirrorPreferencePlugin;
})(jsPsychModule);
