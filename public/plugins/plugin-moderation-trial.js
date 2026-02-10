/**
 * Moderation Trial Plugin for jsPsych
 *
 * Displays one post (control) or a paired original + mirror (linked-fate),
 * and records a Keep/Remove decision that applies to the displayed content.
 *
 * @author Meriel Doyle
 */

var jsPsychModerationTrial = (function (jspsych) {
    "use strict";

    var _package = {
        name: "jspsych-plugin-moderation-trial",
        version: "1.0.0",
        description: "jsPsych plugin for moderation decisions (keep/remove)",
        author: "Meriel Doyle"
    };

    const info = {
        name: "moderation-trial",
        version: _package.version,
        parameters: {
            /** The original post text */
            original_text: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** The mirror post text (linked-fate condition) */
            mirror_text: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** Whether to show the paired posts */
            show_pair: {
                type: jspsych.ParameterType.BOOL,
                default: false
            },
            /** The unique identifier for this post */
            post_id: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** The numeric post number */
            post_number: {
                type: jspsych.ParameterType.STRING,
                default: null
            },
            /** Prompt text to display */
            prompt: {
                type: jspsych.ParameterType.STRING,
                default: "Keep or remove?"
            },
            /** Button text for keep */
            keep_label: {
                type: jspsych.ParameterType.STRING,
                default: "Keep"
            },
            /** Button text for remove */
            remove_label: {
                type: jspsych.ParameterType.STRING,
                default: "Remove"
            },
            /** Progress label for practice trials */
            progress_label: {
                type: jspsych.ParameterType.STRING,
                default: null
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
            post_id: {
                type: jspsych.ParameterType.STRING
            },
            post_number: {
                type: jspsych.ParameterType.STRING
            },
            original_text: {
                type: jspsych.ParameterType.STRING
            },
            mirror_text: {
                type: jspsych.ParameterType.STRING
            },
            show_pair: {
                type: jspsych.ParameterType.BOOL
            },
            decision: {
                type: jspsych.ParameterType.STRING
            },
            pair_order: {
                type: jspsych.ParameterType.OBJECT
            },
            response_time_ms: {
                type: jspsych.ParameterType.FLOAT
            }
        }
    };

    class ModerationTrialPlugin {
        static info = info;

        constructor(jsPsych) {
            this.jsPsych = jsPsych;
        }

        trial(display_element, trial) {
            const startTime = performance.now();

            const isPair = Boolean(trial.show_pair && trial.mirror_text);
            let posts = [
                { role: 'original', label: 'Post A', text: trial.original_text }
            ];

            if (isPair) {
                posts.push({ role: 'mirror', label: 'Post B', text: trial.mirror_text });
                posts = this.shuffleArray(posts);
            }

            const pairOrder = posts.map(post => post.role);

            // Build progress indicator
            let progressHtml = '';
            if (trial.progress_label) {
                progressHtml = `<div class="mirror-progress">${trial.progress_label}</div>`;
            } else if (trial.trial_number !== null && trial.total_trials !== null) {
                progressHtml = `<div class="mirror-progress">Trial ${trial.trial_number} of ${trial.total_trials}</div>`;
            }

            let html = `
                <div class="mirror-preference-container">
                    ${progressHtml}
            `;

            posts.forEach((post, index) => {
                const label = isPair ? `Post ${index + 1}` : 'Post';
                html += `
                    <div class="moderation-post-label">${label}</div>
                    <div class="moderation-post-container">
                        <div class="moderation-post-text">${post.text || ''}</div>
                    </div>
                `;
            });

            html += `
                <div class="mirror-prompt">${trial.prompt}</div>
                <div class="moderation-button-container">
                    <button class="jspsych-btn moderation-choice-btn keep" data-decision="keep">${trial.keep_label}</button>
                    <button class="jspsych-btn moderation-choice-btn remove" data-decision="remove">${trial.remove_label}</button>
                </div>
            </div>
            `;

            display_element.innerHTML = html;

            const buttons = display_element.querySelectorAll('.moderation-choice-btn');
            buttons.forEach(button => {
                button.addEventListener('click', () => {
                    const decision = button.dataset.decision;
                    const responseTime = performance.now() - startTime;

                    const trialData = {
                        post_id: trial.post_id,
                        post_number: trial.post_number,
                        original_text: trial.original_text,
                        mirror_text: trial.mirror_text,
                        show_pair: isPair,
                        decision,
                        pair_order: pairOrder,
                        response_time_ms: responseTime
                    };

                    display_element.innerHTML = '';
                    this.jsPsych.finishTrial(trialData);
                });
            });
        }

        shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }
    }

    ModerationTrialPlugin.info = info;

    return ModerationTrialPlugin;
})(jsPsychModule);

