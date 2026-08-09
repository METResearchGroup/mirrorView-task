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

/**
 * Frozen attention-check catalog (political-expression comprehension).
 * Correct set = all isPolitical:true ids exactly (Q3–Q6).
 */
const ATTENTION_CHECK_OPTIONS = Object.freeze([
    Object.freeze({
        id: 'Q1',
        label: 'I thought the new ice cream place was pretty good but not great.',
        isPolitical: false,
    }),
    Object.freeze({
        id: 'Q2',
        label: "Hot take: Winter is simply the best season. I can't wait for the cold weather.",
        isPolitical: false,
    }),
    Object.freeze({
        id: 'Q3',
        label: "I support Democrats' positions to protect basic human rights.",
        isPolitical: true,
    }),
    Object.freeze({
        id: 'Q4',
        label: "It's so awful how Texas is taking away Women's rights. I won't stand for it any longer!",
        isPolitical: true,
    }),
    Object.freeze({
        id: 'Q5',
        label: 'It completely breaks my heart to see how immigrants are treated these days.',
        isPolitical: true,
    }),
    Object.freeze({
        id: 'Q6',
        label: 'I stand with Republicans who support our second amendment rights.',
        isPolitical: true,
    }),
]);

const ATTENTION_CHECK_CORRECT_IDS = Object.freeze(
    ATTENTION_CHECK_OPTIONS.filter((o) => o.isPolitical).map((o) => o.id)
);

/**
 * Score political-expression attention check by exact id-set equality.
 * @param {iterable|*} selectedIds
 * @returns {{ passed: 0|1, selected: string }}
 */
function scorePoliticalExpressionAttentionCheck(selectedIds) {
    let ids;
    if (selectedIds == null) {
        ids = [];
    } else if (Array.isArray(selectedIds)) {
        ids = selectedIds;
    } else if (typeof selectedIds[Symbol.iterator] === 'function' && typeof selectedIds !== 'string') {
        ids = Array.from(selectedIds);
    } else {
        ids = [];
    }

    const uniqueSorted = [...new Set(ids.map((id) => String(id)))].sort();
    const selected = uniqueSorted.join('|');
    const correct = ATTENTION_CHECK_CORRECT_IDS;
    const passed =
        uniqueSorted.length === correct.length &&
        uniqueSorted.every((id, i) => id === correct[i])
            ? 1
            : 0;
    return { passed, selected };
}

// Browser provides jsPsychSurveyHtmlForm; Node tests use a string stand-in.
const SURVEY_HTML_FORM =
    typeof jsPsychSurveyHtmlForm !== 'undefined'
        ? jsPsychSurveyHtmlForm
        : 'survey-html-form';

function buildAttentionCheckOptionsHtml() {
    return ATTENTION_CHECK_OPTIONS.map((opt, index) => {
        const requiredAttr = index === 0 ? ' required' : '';
        return `
            <label class="att-check-option" data-att-option="${opt.id}"
                   style="display: flex; align-items: flex-start; gap: 12px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; background: white; cursor: pointer; text-align: left;"
                   onmouseover="if(!this.querySelector('input').checked){this.style.borderColor='#5b2d8e'; this.style.background='#faf7fc';}"
                   onmouseout="if(!this.querySelector('input').checked){this.style.borderColor='#e5e7eb'; this.style.background='white';}">
                <input type="checkbox" name="${opt.id}" value="${opt.id}" data-att-check="1"${requiredAttr}
                       style="width: 16px; height: 16px; margin-top: 3px; accent-color: #5b2d8e; flex-shrink: 0;"
                       onchange="(function(el){
                         var boxes = document.querySelectorAll('input[data-att-check]');
                         var any = Array.prototype.some.call(boxes, function(b){ return b.checked; });
                         boxes.forEach(function(b, i){ b.required = !any && i === 0; });
                         var label = el.parentElement;
                         if (el.checked) {
                           label.style.borderColor = '#5b2d8e';
                           label.style.background = '#f7f2fc';
                         } else {
                           label.style.borderColor = '#e5e7eb';
                           label.style.background = 'white';
                         }
                       })(this)">
                <span style="font-size: 15px; line-height: 1.4;">${opt.label}</span>
            </label>`;
    }).join('');
}

/**
 * Extract selected attention-check option ids from a survey-html-form response object.
 * Each checkbox uses a unique name (Q1…Q6) because objectifyForm keeps only one value per name.
 */
function selectedIdsFromAttentionCheckResponse(response) {
    if (!response || typeof response !== 'object') return [];
    return ATTENTION_CHECK_OPTIONS.map((o) => o.id).filter((id) => {
        const v = response[id];
        return v !== undefined && v !== null && v !== '';
    });
}

const politicalExpressionAttentionCheck = {
    type: SURVEY_HTML_FORM,
    preamble: '',
    html: `
        <div class="att-check-container" style="max-width: 720px; margin: 0 auto; text-align: left;">
            <h1 style="margin: 0 0 16px; font-size: 28px; color: #3d1c63; font-weight: 700;">Political Expression</h1>
            <div style="background: #f3f4f6; border-left: 5px solid #5b2d8e; padding: 14px 16px; margin-bottom: 22px; color: #4b5563; line-height: 1.5; font-size: 15px;">
                The next section is about expressing political views on social media.
                By political expression, we mean any sort of public display of your political opinions —
                this includes posts, reposts, and comments.
            </div>
            <p style="font-size: 16px; line-height: 1.55; margin: 0 0 18px; color: #1f2937;">
                To make sure we are on the same page, select the messages expressing a political view.
                Do not judge the message based on whether you agree with it, only whether it expresses a political view.
                <strong>Select all that apply.</strong>
            </p>
            <div class="multi-select-options" style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 8px;">
                ${buildAttentionCheckOptionsHtml()}
            </div>
        </div>
    `,
    button_label: 'Continue',
    data: { trial_type: 'political-expression-attention-check' },
    on_finish: function (data) {
        const selectedIds = selectedIdsFromAttentionCheckResponse(data.response);
        const scored = scorePoliticalExpressionAttentionCheck(selectedIds);
        data.attention_check_passed = scored.passed;
        data.attention_check_selected = scored.selected;
        jsPsych.data.addProperties({
            attention_check_passed: scored.passed,
            attention_check_selected: scored.selected,
        });
        console.log(
            'Attention check passed:',
            scored.passed,
            '| selected:',
            scored.selected
        );
    },
};

const politicalAffiliation = {
    type: SURVEY_HTML_FORM,
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
    button_label: "Continue >",
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
    module.exports = {
        politicalAffiliation,
        determinePartyGroup,
        ATTENTION_CHECK_OPTIONS,
        ATTENTION_CHECK_CORRECT_IDS,
        scorePoliticalExpressionAttentionCheck,
        selectedIdsFromAttentionCheckResponse,
        politicalExpressionAttentionCheck,
    };
}
