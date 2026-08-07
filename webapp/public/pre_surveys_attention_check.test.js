/**
 * Tests for political-expression attention-check scoring (pre_surveys.js).
 *
 * Pseudocode (Phase 3):
 * given selectedIds = ['Q6','Q3','Q5','Q4']
 * when scorePoliticalExpressionAttentionCheck(selectedIds)
 * then passed === 1 and selected === 'Q3|Q4|Q5|Q6'
 *
 * given selectedIds missing one political id (e.g. no Q5)
 * when score...
 * then passed === 0
 *
 * given selectedIds includes a non-political id (Q1) plus all political
 * when score...
 * then passed === 0
 *
 * given selectedIds = []
 * when score...
 * then passed === 0 and selected === ''
 *
 * given selectedIds = null / not an array
 * when score...
 * then passed === 0 and selected === '' (no throw)
 *
 * given unknown id 'QX' mixed with correct set
 * when score...
 * then passed === 0 and selected includes QX
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

// Browser globals used by trial object literals at module load time.
globalThis.jsPsychSurveyHtmlForm =
    globalThis.jsPsychSurveyHtmlForm || 'survey-html-form';
globalThis.jsPsych = globalThis.jsPsych || {
    data: { addProperties() {} },
};

const {
    ATTENTION_CHECK_OPTIONS,
    ATTENTION_CHECK_CORRECT_IDS,
    scorePoliticalExpressionAttentionCheck,
    politicalExpressionAttentionCheck,
    determinePartyGroup,
} = require('./pre_surveys.js');

describe('ATTENTION_CHECK_OPTIONS catalog', () => {
    it('has six options with exact labels and political flags', () => {
        assert.equal(ATTENTION_CHECK_OPTIONS.length, 6);
        const byId = Object.fromEntries(ATTENTION_CHECK_OPTIONS.map((o) => [o.id, o]));
        assert.equal(
            byId.Q1.label,
            'I thought the new ice cream place was pretty good but not great.'
        );
        assert.equal(byId.Q1.isPolitical, false);
        assert.equal(
            byId.Q2.label,
            "Hot take: Winter is simply the best season. I can't wait for the cold weather."
        );
        assert.equal(byId.Q2.isPolitical, false);
        assert.equal(
            byId.Q3.label,
            "I support Democrats' positions to protect basic human rights."
        );
        assert.equal(byId.Q3.isPolitical, true);
        assert.equal(
            byId.Q4.label,
            "It's so awful how Texas is taking away Women's rights. I won't stand for it any longer!"
        );
        assert.equal(byId.Q4.isPolitical, true);
        assert.equal(
            byId.Q5.label,
            'It completely breaks my heart to see how immigrants are treated these days.'
        );
        assert.equal(byId.Q5.isPolitical, true);
        assert.equal(
            byId.Q6.label,
            'I stand with Republicans who support our second amendment rights.'
        );
        assert.equal(byId.Q6.isPolitical, true);
    });
});

describe('ATTENTION_CHECK_CORRECT_IDS', () => {
    it('is exactly Q3–Q6', () => {
        const ids = [...ATTENTION_CHECK_CORRECT_IDS].sort();
        assert.deepEqual(ids, ['Q3', 'Q4', 'Q5', 'Q6']);
    });
});

describe('scorePoliticalExpressionAttentionCheck', () => {
    it('passes on exact correct set regardless of order', () => {
        const result = scorePoliticalExpressionAttentionCheck(['Q6', 'Q3', 'Q5', 'Q4']);
        assert.equal(result.passed, 1);
        assert.equal(result.selected, 'Q3|Q4|Q5|Q6');
    });

    it('fails when a political option is missing', () => {
        const result = scorePoliticalExpressionAttentionCheck(['Q3', 'Q4', 'Q6']);
        assert.equal(result.passed, 0);
        assert.equal(result.selected, 'Q3|Q4|Q6');
    });

    it('fails when a non-political option is included with the correct set', () => {
        const result = scorePoliticalExpressionAttentionCheck([
            'Q1',
            'Q3',
            'Q4',
            'Q5',
            'Q6',
        ]);
        assert.equal(result.passed, 0);
        assert.equal(result.selected, 'Q1|Q3|Q4|Q5|Q6');
    });

    it('fails on empty selection', () => {
        const result = scorePoliticalExpressionAttentionCheck([]);
        assert.equal(result.passed, 0);
        assert.equal(result.selected, '');
    });

    it('coerces non-array input to empty without throwing', () => {
        assert.deepEqual(scorePoliticalExpressionAttentionCheck(null), {
            passed: 0,
            selected: '',
        });
        assert.deepEqual(scorePoliticalExpressionAttentionCheck(undefined), {
            passed: 0,
            selected: '',
        });
        assert.deepEqual(scorePoliticalExpressionAttentionCheck('Q3'), {
            passed: 0,
            selected: '',
        });
    });

    it('fails on unknown ids but still records them in selected', () => {
        const result = scorePoliticalExpressionAttentionCheck([
            'Q3',
            'Q4',
            'Q5',
            'Q6',
            'QX',
        ]);
        assert.equal(result.passed, 0);
        assert.equal(result.selected, 'Q3|Q4|Q5|Q6|QX');
    });

    it('dedupes duplicate ids', () => {
        const result = scorePoliticalExpressionAttentionCheck([
            'Q3',
            'Q3',
            'Q4',
            'Q5',
            'Q6',
        ]);
        assert.equal(result.passed, 1);
        assert.equal(result.selected, 'Q3|Q4|Q5|Q6');
    });
});

describe('politicalExpressionAttentionCheck trial export', () => {
    it('exports trial with expected trial_type', () => {
        assert.ok(politicalExpressionAttentionCheck);
        assert.equal(
            politicalExpressionAttentionCheck.data.trial_type,
            'political-expression-attention-check'
        );
    });

    it('does not abort the experiment on finish (only addProperties)', () => {
        const calls = [];
        const original = jsPsych.data.addProperties;
        jsPsych.data.addProperties = (props) => {
            calls.push(props);
        };
        jsPsych.endExperiment = () => {
            throw new Error('must not end experiment');
        };
        try {
            politicalExpressionAttentionCheck.on_finish({
                response: { Q3: 'Q3', Q4: 'Q4', Q5: 'Q5', Q6: 'Q6' },
            });
        } finally {
            jsPsych.data.addProperties = original;
        }
        assert.equal(calls.length, 1);
        assert.equal(calls[0].attention_check_passed, 1);
        assert.equal(calls[0].attention_check_selected, 'Q3|Q4|Q5|Q6');
    });

    it('records fail without ending experiment', () => {
        const calls = [];
        const original = jsPsych.data.addProperties;
        jsPsych.data.addProperties = (props) => {
            calls.push(props);
        };
        try {
            politicalExpressionAttentionCheck.on_finish({
                response: { Q1: 'Q1', Q3: 'Q3' },
            });
        } finally {
            jsPsych.data.addProperties = original;
        }
        assert.equal(calls[0].attention_check_passed, 0);
        assert.equal(calls[0].attention_check_selected, 'Q1|Q3');
    });
});

describe('selectedIdsFromAttentionCheckResponse', () => {
    it('reads unique checkbox names from form response', () => {
        const {
            selectedIdsFromAttentionCheckResponse,
        } = require('./pre_surveys.js');
        assert.deepEqual(
            selectedIdsFromAttentionCheckResponse({
                Q3: 'Q3',
                Q6: 'Q6',
                Q4: 'Q4',
            }),
            ['Q3', 'Q4', 'Q6']
        );
    });
});

describe('determinePartyGroup unchanged', () => {
    it('still maps party values', () => {
        assert.equal(determinePartyGroup('democrat', null), 'democrat');
        assert.equal(determinePartyGroup('other', 'republican'), 'republican');
    });
});
