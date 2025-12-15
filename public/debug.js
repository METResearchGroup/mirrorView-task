const debug = false;

window.debug = debug;

// make require_movement optional for image slider trials when debug is true
function makeRequireMovementOptional(trial) {
    if (window.debug && trial.type === jsPsychHtmlSliderResponse) {
        trial.require_movement = false;
    }
    return trial;
}

// remove 'required' attributes from pre_surveys.js and post_surveys.js when debug is true
function removeRequiredAttributes() {
    if (window.debug) {
        document.querySelectorAll('[required]').forEach(el => {
            el.removeAttribute('required');
        });
    }
}

// make function globally available
window.makeRequireMovementOptional = makeRequireMovementOptional;
window.removeRequiredAttributes = removeRequiredAttributes;