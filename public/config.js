// Configuration file for switching between local development and AWS production
const config = {
    // Set to 'local' for development, 'aws' for production
    mode: 'local',
    
    // Local development settings
    local: {
        GET_PARTICIPANT_ID_URL: 'http://localhost:3000/get-participant-id',
        SAVE_DATA_URL: 'http://localhost:3000/save-jspsych-data',
        port: 3000
    },
    
    // AWS production settings
    aws: {
        GET_PARTICIPANT_ID_URL: 'https://n2w6sd413g.execute-api.us-east-2.amazonaws.com/get-participant-id',
        SAVE_DATA_URL: 'https://n2w6sd413g.execute-api.us-east-2.amazonaws.com/save-jspsych-data',
        PROLIFIC_COMPLETION_URL: null // Set this to your Prolific completion URL when ready
    },
    
    // Get current configuration based on mode
    getCurrentConfig() {
        return this[this.mode];
    },
    
    // Switch between modes
    setMode(newMode) {
        if (['local', 'aws'].includes(newMode)) {
            this.mode = newMode;
            console.log(`Switched to ${newMode} mode`);
            return true;
        } else {
            console.error('Invalid mode. Use "local" or "aws"');
            return false;
        }
    },
    
    // Get current URLs
    getUrls() {
        const currentConfig = this.getCurrentConfig();
        return {
            GET_PARTICIPANT_ID_URL: currentConfig.GET_PARTICIPANT_ID_URL,
            SAVE_DATA_URL: currentConfig.SAVE_DATA_URL,
            PROLIFIC_COMPLETION_URL: currentConfig.PROLIFIC_COMPLETION_URL || null
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
