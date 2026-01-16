/**
 * Mirror Practice Plugin for jsPsych
 * 
 * A practice version of the mirror preference task with feedback.
 * Shows "Try again!" when wrong, only allows advancing when correct.
 * 
 * @author Meriel Doyle
 */

var jsPsychMirrorPractice = (function (jspsych) {
    "use strict";

    var _package = {
        name: "jspsych-plugin-mirror-practice",
        version: "1.0.0",
        description: "jsPsych plugin for practice mirror selection with feedback",
        author: "Meriel Doyle",
    };

    const info = {
        name: "mirror-practice",
        version: _package.version,
        parameters: {
            /** The original post text */
            original_text: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** Array of mirror options, each with {id, text} */
            options: {
                type: jspsych.ParameterType.COMPLEX,
                array: true,
                default: []
            },
            /** The id of the correct answer */
            correct_answer: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** Prompt text to display */
            prompt: {
                type: jspsych.ParameterType.STRING,
                default: "Which mirror do you prefer?"
            },
            /** Feedback text for incorrect answers */
            incorrect_feedback: {
                type: jspsych.ParameterType.STRING,
                default: "Try again!"
            },
            /** Feedback text for correct answers */
            correct_feedback: {
                type: jspsych.ParameterType.STRING,
                default: "Correct!"
            },
            /** Button text for the next button */
            button_label: {
                type: jspsych.ParameterType.STRING,
                default: "Next →"
            },
            /** Whether to shuffle the options */
            shuffle_options: {
                type: jspsych.ParameterType.BOOL,
                default: true
            },
            /** Label for the practice indicator */
            practice_label: {
                type: jspsych.ParameterType.STRING,
                default: "Practice Trial"
            }
        },
        data: {
            /** The original post text */
            original_text: {
                type: jspsych.ParameterType.STRING
            },
            /** The mirror id that was selected */
            selected_mirror: {
                type: jspsych.ParameterType.STRING
            },
            /** Whether the response was correct */
            correct: {
                type: jspsych.ParameterType.BOOL
            },
            /** Number of attempts before correct */
            attempts: {
                type: jspsych.ParameterType.INT
            },
            /** Total time on the trial in milliseconds */
            response_time_ms: {
                type: jspsych.ParameterType.FLOAT
            }
        }
    };

    class MirrorPracticePlugin {
        static info = info;

        constructor(jsPsych) {
            this.jsPsych = jsPsych;
        }

        trial(display_element, trial) {
            // Prepare options (optionally shuffle)
            let displayOptions = [...trial.options];
            if (trial.shuffle_options) {
                displayOptions = this.shuffleArray(displayOptions);
            }

            // Build the HTML
            let html = `
                <div class="mirror-preference-container">
                    <div class="mirror-progress">${trial.practice_label}</div>
            `;

            // Show original text
            if (trial.original_text) {
                html += `
                    <div class="original-post-label">Original text:</div>
                    <div class="original-post-container">
                        <div class="original-post-text">${trial.original_text}</div>
                    </div>
                `;
            }

            // Add the prompt
            html += `<div class="mirror-prompt">${trial.prompt}</div>`;

            // Add mirror cards
            html += `<div class="mirror-cards-container">`;
            
            displayOptions.forEach((option, index) => {
                html += `
                    <div class="mirror-card" data-mirror-id="${option.id}" data-position="${index + 1}">
                        <div class="mirror-card-number">${index + 1}</div>
                        <div class="mirror-card-text">${option.text}</div>
                    </div>
                `;
            });

            html += `</div>`;

            // Add feedback area (hidden initially)
            html += `<div class="practice-feedback" style="display: none;"></div>`;

            // Add next button (hidden initially)
            html += `
                <div class="mirror-button-container">
                    <button class="jspsych-btn mirror-next-btn" style="display: none;">${trial.button_label}</button>
                </div>
            </div>
            `;

            display_element.innerHTML = html;

            // Track state
            let attempts = 0;
            let isCorrect = false;
            const startTime = performance.now();

            // Get elements
            const cards = display_element.querySelectorAll('.mirror-card');
            const nextBtn = display_element.querySelector('.mirror-next-btn');
            const feedbackEl = display_element.querySelector('.practice-feedback');

            // Click to select
            cards.forEach(card => {
                card.addEventListener('click', () => {
                    if (isCorrect) return; // Already answered correctly

                    const selectedId = card.dataset.mirrorId;
                    attempts++;

                    // Check if correct
                    if (selectedId === trial.correct_answer) {
                        isCorrect = true;
                        
                        // Remove any previous selections and feedback styling
                        cards.forEach(c => {
                            c.classList.remove('selected', 'incorrect');
                        });
                        
                        // Mark as correct
                        card.classList.add('selected', 'correct');
                        
                        // Show correct feedback
                        feedbackEl.innerHTML = `<span class="feedback-correct">${trial.correct_feedback}</span>`;
                        feedbackEl.style.display = 'block';
                        
                        // Show next button
                        nextBtn.style.display = 'inline-block';
                    } else {
                        // Remove previous selections
                        cards.forEach(c => c.classList.remove('selected'));
                        
                        // Mark as incorrect
                        card.classList.add('selected', 'incorrect');
                        
                        // Show incorrect feedback
                        feedbackEl.innerHTML = `<span class="feedback-incorrect">${trial.incorrect_feedback}</span>`;
                        feedbackEl.style.display = 'block';
                        
                        // Shake the card briefly
                        card.classList.add('shake');
                        setTimeout(() => card.classList.remove('shake'), 500);
                    }
                });
            });

            // Handle next button click
            nextBtn.addEventListener('click', () => {
                const endTime = performance.now();
                const responseTime = endTime - startTime;

                // Compile trial data
                const trialData = {
                    original_text: trial.original_text,
                    selected_mirror: trial.correct_answer,
                    correct: true,
                    attempts: attempts,
                    response_time_ms: responseTime
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

    MirrorPracticePlugin.info = info;

    return MirrorPracticePlugin;
})(jsPsychModule);

