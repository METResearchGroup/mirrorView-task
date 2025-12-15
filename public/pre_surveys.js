function determinePoliticalAffiliation(party, partyLean) {
    if (party === 'democrat') return 'democrat';
    if (party === 'republican') return 'republican';
    if (party === 'other') {
        return partyLean === 'democrat' ? 'lean_democrat' : 'lean_republican';
    }
    return null;
}

const prePolSurvey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2>Political Affiliation</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <label for="party">Politically speaking, do you consider yourself:</label>
                <select id="party" name="party" required>
                    <option value="" selected disabled>Select an option</option>
                    <option value="democrat">A Democrat</option>
                    <option value="republican">A Republican</option>
                    <option value="other">Other</option>
                </select>
            </div>
        </div>
        <div id="party-lean" class="survey-container" style="display:none;">
            <div class="survey-question">
                <label for="party_lean">If you had to choose, which party do you feel like you lean more closely toward?</label>
                <select id="party_lean" name="party_lean">
                    <option value="" selected disabled>Select an option</option>
                    <option value="democrat">A Democrat</option>
                    <option value="republican">A Republican</option>
                </select>
            </div>
        </div>
    `,
    button_label: "Next >",

    on_load: function() {
        const partySelect = document.getElementById('party');
        const partyLeanSelect = document.getElementById('party_lean');
        
        // ensure the first select is required
        partySelect.required = true;
        
        // add validation for the first select
        partySelect.addEventListener('change', function() {
            // validate party selection
            if (!this.value || this.value === '' || this.value === 'null') {
                this.required = true;
                return false;
            }
            
            var partyLeanDiv = document.getElementById('party-lean');
            if (this.value === 'other') {
                partyLeanDiv.style.display = 'block';
                partyLeanSelect.required = true;
            } else {
                partyLeanDiv.style.display = 'none';
                partyLeanSelect.required = false;
            }
        });

        // window.removeRequiredAttributes();
    },
    on_finish: function(data) {
        // store political affiliation for later use
        const politicalAffiliation = determinePoliticalAffiliation(
            data.response.party,
            data.response.party_lean
        );
        jsPsych.data.addProperties({
            political_affiliation: politicalAffiliation
        });
    }
};



// export surveys so they can be imported in the main file
if (typeof module !== 'undefined') {
    module.exports = {
        prePolSurvey
    };
}