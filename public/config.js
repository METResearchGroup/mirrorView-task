// Production endpoint + study identity configuration.
// Source of truth: jobs/config/mirrorview_scaled_2026_06_18.yaml
const config = {
    POST_ASSIGNMENTS_URL: 'https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments',
    SAVE_DATA_URL: 'https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data',
    PROLIFIC_COMPLETION_URL: null,
    STUDY_ID: 'mirrorview',
    STUDY_ITERATION_ID: 'mirrorview_scaled_2026_06_18',
    PROLIFIC_COMPLETION_CODE: 'CE5XLP3L',
    PROLIFIC_COMPLETION_LINK: 'https://app.prolific.com/submissions/complete?cc=CE5XLP3L',

    getUrls() {
        return {
            POST_ASSIGNMENTS_URL: this.POST_ASSIGNMENTS_URL,
            SAVE_DATA_URL: this.SAVE_DATA_URL,
            PROLIFIC_COMPLETION_URL: this.PROLIFIC_COMPLETION_URL || null,
            STUDY_ID: this.STUDY_ID,
            STUDY_ITERATION_ID: this.STUDY_ITERATION_ID
        };
    }
};

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}

// Make available globally for browser
if (typeof window !== 'undefined') {
    window.config = config;
}
