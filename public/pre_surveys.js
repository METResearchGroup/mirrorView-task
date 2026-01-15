/**
 * Political affiliation survey for MirrorView experiment
 * Asks participants to confirm their political party before the main task
 */

// Helper function to determine the effective party group
function determinePartyGroup(party, partyLean) {
    if (party === 'democrat') return 'democrat';
    if (party === 'republican') return 'republican';
    if (party === 'other') {
        return partyLean; // Will be 'democrat' or 'republican'
    }
    return null;
}

const politicalAffiliation = {
    type: jsPsychSurveyHtmlForm,
    preamble: '',
    html: `
        <div style="text-align: center; max-width: 600px; margin: 0 auto;">
            <p style="font-size: 18px; margin-bottom: 24px;">Politically speaking, do you consider yourself:</p>
            
            <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
                <label style="display: flex; align-items: center; width: 280px; padding: 14px 20px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; background: white;"
                       onmouseover="this.style.borderColor='#3b82f6'; this.style.background='#f8fafc';"
                       onmouseout="if(!this.querySelector('input').checked){this.style.borderColor='#e5e7eb'; this.style.background='white';}">
                    <input type="radio" name="party" value="democrat" required 
                           style="width: 18px; height: 18px; margin-right: 12px; accent-color: #3b82f6;"
                           onchange="document.getElementById('party-lean-container').style.display='none'; document.getElementById('party_lean').required=false; document.querySelectorAll('label[data-party]').forEach(l => {l.style.borderColor='#e5e7eb'; l.style.background='white';}); this.parentElement.style.borderColor='#3b82f6'; this.parentElement.style.background='#eff6ff';">
                    <span style="font-size: 16px;">A Democrat</span>
                </label>
                
                <label style="display: flex; align-items: center; width: 280px; padding: 14px 20px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; background: white;"
                       onmouseover="this.style.borderColor='#3b82f6'; this.style.background='#f8fafc';"
                       onmouseout="if(!this.querySelector('input').checked){this.style.borderColor='#e5e7eb'; this.style.background='white';}">
                    <input type="radio" name="party" value="republican" required 
                           style="width: 18px; height: 18px; margin-right: 12px; accent-color: #3b82f6;"
                           onchange="document.getElementById('party-lean-container').style.display='none'; document.getElementById('party_lean').required=false; document.querySelectorAll('label[data-party]').forEach(l => {l.style.borderColor='#e5e7eb'; l.style.background='white';}); this.parentElement.style.borderColor='#3b82f6'; this.parentElement.style.background='#eff6ff';">
                    <span style="font-size: 16px;">A Republican</span>
                </label>
                
                <label data-party="other" style="display: flex; align-items: center; width: 280px; padding: 14px 20px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; background: white;"
                       onmouseover="this.style.borderColor='#3b82f6'; this.style.background='#f8fafc';"
                       onmouseout="if(!this.querySelector('input').checked){this.style.borderColor='#e5e7eb'; this.style.background='white';}">
                    <input type="radio" name="party" value="other" required 
                           style="width: 18px; height: 18px; margin-right: 12px; accent-color: #3b82f6;"
                           onchange="document.getElementById('party-lean-container').style.display='flex'; document.getElementById('party_lean').required=true; document.querySelectorAll('label[data-party]').forEach(l => {l.style.borderColor='#e5e7eb'; l.style.background='white';}); this.parentElement.style.borderColor='#3b82f6'; this.parentElement.style.background='#eff6ff';">
                    <span style="font-size: 16px;">Other</span>
                </label>
            </div>
            
            <div id="party-lean-container" style="display: none; flex-direction: column; align-items: center; margin-top: 24px; padding-top: 24px; border-top: 1px solid #e5e7eb;">
                <p style="font-size: 16px; margin-bottom: 16px; color: #4b5563;">If you had to choose, which party do you lean toward?</p>
                <div style="display: flex; gap: 16px;">
                    <label style="display: flex; align-items: center; padding: 12px 24px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; background: white;"
                           onmouseover="this.style.borderColor='#3b82f6'; this.style.background='#f8fafc';"
                           onmouseout="if(!this.querySelector('input').checked){this.style.borderColor='#e5e7eb'; this.style.background='white';}">
                        <input type="radio" name="party_lean" id="party_lean" value="democrat" 
                               style="width: 16px; height: 16px; margin-right: 8px; accent-color: #3b82f6;"
                               onchange="this.parentElement.style.borderColor='#3b82f6'; this.parentElement.style.background='#eff6ff'; document.querySelector('input[name=party_lean][value=republican]').parentElement.style.borderColor='#e5e7eb'; document.querySelector('input[name=party_lean][value=republican]').parentElement.style.background='white';">
                        <span>Democrat</span>
                    </label>
                    <label style="display: flex; align-items: center; padding: 12px 24px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; background: white;"
                           onmouseover="this.style.borderColor='#3b82f6'; this.style.background='#f8fafc';"
                           onmouseout="if(!this.querySelector('input').checked){this.style.borderColor='#e5e7eb'; this.style.background='white';}">
                        <input type="radio" name="party_lean" value="republican" 
                               style="width: 16px; height: 16px; margin-right: 8px; accent-color: #3b82f6;"
                               onchange="this.parentElement.style.borderColor='#3b82f6'; this.parentElement.style.background='#eff6ff'; document.querySelector('input[name=party_lean][value=democrat]').parentElement.style.borderColor='#e5e7eb'; document.querySelector('input[name=party_lean][value=democrat]').parentElement.style.background='white';">
                        <span>Republican</span>
                    </label>
                </div>
            </div>
        </div>
    `,
    button_label: "Continue →",
    data: { trial_type: 'political-affiliation' },
    on_finish: function(data) {
        // Determine party group: use party_lean if party is 'other', otherwise use party
        const party = data.response.party;
        const partyLean = data.response.party_lean;
        const partyGroup = determinePartyGroup(party, partyLean);
        
        jsPsych.data.addProperties({
            political_affiliation: party,
            party_lean: partyLean || null,
            party_group: partyGroup
        });
        console.log('Political affiliation:', party, '| Party group:', partyGroup);
    }
};

// Export for Node.js (if needed)
if (typeof module !== 'undefined') {
    module.exports = { politicalAffiliation, determinePartyGroup };
}
