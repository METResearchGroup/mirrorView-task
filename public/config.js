// Production-only endpoint configuration.
const config = {
    POST_ASSIGNMENTS_URL: 'https://ngxqzz3qhd.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments',
    SAVE_DATA_URL: 'https://ngxqzz3qhd.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data',
    PROLIFIC_COMPLETION_URL: null,

    getUrls() {
        return {
            POST_ASSIGNMENTS_URL: this.POST_ASSIGNMENTS_URL,
            SAVE_DATA_URL: this.SAVE_DATA_URL,
            PROLIFIC_COMPLETION_URL: this.PROLIFIC_COMPLETION_URL || null
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
