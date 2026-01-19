// demographics survey
const demographicsSurvey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2>Demographics</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
            <label for="gender" style="font-weight: normal;">To which gender do you mostly identify?</label>
            <select id="gender" name="gender" required>
                <option value="" selected disabled>Select an option</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
                </select>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
            <label for="age" style="font-weight: normal;">How old are you?</label>
                <input type="number" id="age" name="age" required min="18" max="120">
            </div>
        </div>          
        <div class="survey-container">
            <div class="survey-question">
                <label for="language" style="font-weight: normal;">Is English your first language?</label>
            <select id="language" name="language" required>
                <option value="" selected disabled>Select an option</option>
                <option value="yes">Yes</option>
                <option value="no_fluent">No, but fluent</option>
                <option value="no_mostly_fluent">No, mostly fluent</option>
                <option value="no_minimal">No, minimal fluency</option>
                </select>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="education" style="font-weight: normal;">Please indicate your education level</label>
            <select id="education" name="education" required>
                <option value="" selected disabled>Select an option</option>
                <option value="no_school">No school</option>
                <option value="eighth_or_less">Eighth grade or less</option>
                <option value="some_high_school">More than eighth grade, but less than high school</option>
                <option value="high_school">High school or equivalent</option>
                <option value="some_college">Some college</option>
                <option value="college_degree">4-year college degree</option>
                <option value="graduate">Graduate or professional training</option>
                </select>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="employment" style="font-weight: normal;">Are you currently...?</label>
            <select id="employment" name="employment" required>
                <option value="" selected disabled>Select an option</option>
                <option value="employed">Employed</option>
                <option value="self_employed">Self-employed</option>
                <option value="student">A student</option>
                <option value="unemployed">Unemployed</option>
                <option value="other">Other</option>
                </select>
            </div>
        </div>
    `,
    button_label: "Submit",
    autofocus: "gender",

    // on_load: function() {
    //     window.removeRequiredAttributes();
    // }
};

function createLikertOptions(name, count) {
    let options = '';
    for (let i = 1; i <= count; i++) {
        options += `
            <div class="likert-option">
                <input type="radio" name="${name}" value="${i}" id="${name}-${i}" required>
                <label for="${name}-${i}"></label>
            </div>
        `;
    }
    return options;
}

function setupLikertScales() {
    const likertContainers = document.querySelectorAll('.likert-container');
    likertContainers.forEach(container => {
        const radioButtons = container.querySelectorAll('input[type="radio"]');
        const labels = container.querySelector('.likert-labels').children;

        radioButtons.forEach(radio => {
            radio.addEventListener('change', function() {
                // reset all labels to normal font weight
                for (let i = 0; i < labels.length; i++) {
                    labels[i].style.fontWeight = 'normal';
                }
                // bold the selected label
                labels[this.value - 1].style.fontWeight = 'bold';
            });
        });
    });
}

const politicalSurvey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2>Political Attitudes</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <label for="political_ideology" style="font-weight: normal;">How would you describe your political ideology?</label>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('political_ideology', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Extremely liberal</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Neither</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Extremely conservative</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="political_follow" style="font-weight: normal;">Generally speaking, how closely do you follow politics?</label>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('political_follow', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Not closely at all</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Moderately closely</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very closely</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="rep_id" style="font-weight: normal;">To what extent do you agree with the following statement: "<b>I identify with the Republican Party</b>"</label>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('rep_id', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Fully Disagree</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Neither agree nor disagree</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Fully agree</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="dem_id" style="font-weight: normal;">To what extent do you agree with the following statement: "<b>I identify with the Democratic Party</b>"</label>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('dem_id', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Fully Disagree</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Neither agree nor disagree</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Fully agree</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    button_label: "Submit >",

    on_load: function() {

        setupLikertScales();

        // window.removeRequiredAttributes();
    }
};

const socialMediaSurvey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2>Social Media Usage</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <label for="sm_use" style="font-weight: normal;">How often do you use social media?</label>
                <select id="sm_use" name="sm_use" required>
                <option value="" selected disabled>Select an option</option>
                <option value="daily_or_more">Daily or more</option>
                <option value="4-6_times_a_week">4-6 times a week</option>
                <option value="2-3_times_a_week">2-3 times a week</option>
                <option value="once_per_week">Once per week</option>
                <option value="between_once_per_week_and_once_per_month">Between once per week and once per month</option>
                <option value="between_once_per_month_and_once_per_year">Between once per month and once per year</option>
                <option value="never">Never</option>
                </select>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="sm_use_slider" style="font-weight: normal;">If you use social media <b>daily or more</b>, use the slider to indicate <b>how many times per day</b> you tend to use social media. If you don't use social media daily or more, then leave the slider at 0.</label>
                <div class="slider-container">
                    <input type="range" id="sm_use_slider" name="sm_use_slider" min="0" max="100" value="0" step="1">
                    <output for="sm_use_slider" id="sm_use_slider_value">0</output>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="sm_use_poli" style="font-weight: normal;">How often do you use social media specifically to <b>view or learn about political content</b>?</label>
                <select id="sm_use_poli" name="sm_use_poli" required>
                <option value="" selected disabled>Select an option</option>
                <option value="daily_or_more">Daily or more</option>
                <option value="4-6_times_a_week">4-6 times a week</option>
                <option value="2-3_times_a_week">2-3 times a week</option>
                <option value="once_per_week">Once per week</option>
                <option value="between_once_per_week_and_once_per_month">Between once per week and once per month</option>
                <option value="between_once_per_month_and_once_per_year">Between once per month and once per year</option>
                <option value="never">Never</option>
                </select>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="sm_use_poli_slider" style="font-weight: normal;">If you use social media to <b>view or learn about political content daily or more</b>, use the slider to indicate <b>how many times per day</b> you tend to use social media to view or learn about political content. <b>If you don't</b> use social media to view or learn about political content daily or more, then <b>leave the slider at 0.</b></label>
                <div class="slider-container">
                    <input type="range" id="sm_use_poli_slider" name="sm_use_poli_slider" min="0" max="100" value="0" step="1">
                    <output for="sm_use_poli_slider" id="sm_use_poli_slider_value">0</output>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="sm_post_poli" style="font-weight: normal;">How often do you use social media specifically to <b>post or share political content</b>?</label>
                <select id="sm_post_poli" name="sm_post_poli" required>
                <option value="" selected disabled>Select an option</option>
                <option value="daily_or_more">Daily or more</option>
                <option value="4-6_times_a_week">4-6 times a week</option>
                <option value="2-3_times_a_week">2-3 times a week</option>
                <option value="once_per_week">Once per week</option>
                <option value="between_once_per_week_and_once_per_month">Between once per week and once per month</option>
                <option value="between_once_per_month_and_once_per_year">Between once per month and once per year</option>
                <option value="never">Never</option>
                </select>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="sm_post_poli_slider" style="font-weight: normal;">If you use social media to <b>post or share political content daily or more</b>, use the slider to indicate <b>how many times per day</b> you tend to use social media to post or share political content. <b>If you don't</b> use social media to post or share political content daily or more, then <b>leave the slider at 0.</b></label>
                <div class="slider-container">
                    <input type="range" id="sm_post_poli_slider" name="sm_post_poli_slider" min="0" max="100" value="0" step="1">
                    <output for="sm_post_poli_slider" id="sm_post_poli_slider_value">0</output>
                </div>
            </div>
        </div>  
        <div class="survey-container">
            <div class="survey-question">
                <label for="share_why" style="font-weight: normal;">If you share (e.g. retweet, share, repost) content on social media, <b>why do you typically share it</b> (check all that apply)?</label>
                <div class="multi-select-options">
                    <label><input type="checkbox" name="share_why_1" value="see_content"> I want people to see the content</label>
                    <label><input type="checkbox" name="share_why_2" value="make_laugh"> I want to make people laugh</label>
                    <label><input type="checkbox" name="share_why_3" value="change_opinions"> I want to change people's opinions</label>
                    <label><input type="checkbox" name="share_why_4" value="troll_people"> I want to troll people</label>
                    <label><input type="checkbox" name="share_why_5" value="represents_beliefs"> The content represents my beliefs or attitudes</label>
                    <label><input type="checkbox" name="share_why_6" value="show_common_beliefs"> I want to show people that we share common beliefs or attitudes</label>
                    <label><input type="checkbox" name="share_why_7" value="other"> Other</label>
                </div>
            </div>
        </div>   
    `,
    button_label: "Next >",

    on_load: function() {
        const sliders = ['sm_use_slider', 'sm_use_poli_slider', 'sm_post_poli_slider'];
        sliders.forEach(sliderId => {
            const slider = document.getElementById(sliderId);
            const output = document.getElementById(`${sliderId}_value`);
            slider.oninput = function() {
                output.value = this.value;
            }
        });

        // window.removeRequiredAttributes();
    }
}

const prescriptiveSurvey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2 style='font-weight: normal;'>Perceptions of the <b>second</b> social media network (feed) you viewed</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <div>In the <b>second</b> social media network you viewed, how socially appropriate do you think it is to <b>post a message that blames others</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('blame_prescriptive', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>In the <b>second</b> social media network you viewed, how socially appropriate do you think it is to <b>post a message that praises others</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('praise_prescriptive', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>In the <b>second</b> social media network you viewed, how socially appropriate do you think it is to <b>post a message that is emotional</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('emotion_prescriptive', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>In the <b>second</b> social media network you viewed, how socially appropriate do you think it is to <b>post a message that is political</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('poli_prescriptive', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    button_label: "Next >",

    on_load: function() {

        setupLikertScales();

        // window.removeRequiredAttributes();
    }
};

// descriptive survey with slider questions about perceived percentages in the social network
const descriptiveSurvey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2 style='font-weight: normal;'>Perceptions of the <b>second</b> social media network (feed) you viewed</h2>",
    html: `
        <div class="survey-container" style="margin-bottom: 40px;">
            <div class="survey-question">
                <label for="blame_descriptive" style="font-weight: normal;">In the <b>second</b> social media network you viewed, what percentage of people were <b>posting a message that blamed others</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="blame_descriptive" name="blame_descriptive" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="blame_descriptive" id="blame_descriptive_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container" style="margin-bottom: 40px;">
            <div class="survey-question">
                <label for="praise_descriptive" style="font-weight: normal;">In the <b>second</b> social media network you viewed, what percentage of people were <b>posting a message that praised others</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="praise_descriptive" name="praise_descriptive" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="praise_descriptive" id="praise_descriptive_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container" style="margin-bottom: 40px;">
            <div class="survey-question">
                <label for="emotion_descriptive" style="font-weight: normal;">In the <b>second</b> social media network you viewed, what percentage of people were <b>posting a message that was emotional</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="emotion_descriptive" name="emotion_descriptive" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="emotion_descriptive" id="emotion_descriptive_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="political_descriptive" style="font-weight: normal;">In the <b>second</b> social media network you viewed, what percentage of people were <b>posting a message that was political</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="political_descriptive" name="political_descriptive" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="political_descriptive" id="political_descriptive_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div id="validation-message" style="color: red; font-weight: bold; margin-top: 20px; display: none;">
            Please interact with all sliders before proceeding.
        </div>
    `,
    button_label: "Next >",
    on_load: function() {
        const sliders = ['blame_descriptive', 'praise_descriptive', 'emotion_descriptive', 'political_descriptive'];
        
        sliders.forEach(sliderId => {
            const slider = document.getElementById(sliderId);
            const output = document.getElementById(`${sliderId}_value`);
            
            // Set initial custom validity to require interaction
            slider.setCustomValidity('Please interact with this slider.');
            
            // Function to mark slider as interacted
            function markAsInteracted() {
                slider.setAttribute('data-interacted', 'true');
                slider.setCustomValidity('');
                
                // Hide validation message if all sliders have been interacted with
                const allInteracted = sliders.every(id => 
                    document.getElementById(id).getAttribute('data-interacted') === 'true'
                );
                if (allInteracted) {
                    document.getElementById('validation-message').style.display = 'none';
                }
            }
            
            // Track when slider is interacted with (multiple event types)
            slider.addEventListener('input', function() {
                output.value = this.value + '%';
                markAsInteracted();
            });
            
            // Also listen for mouse and keyboard interactions
            slider.addEventListener('mousedown', markAsInteracted);
            slider.addEventListener('touchstart', markAsInteracted);
            slider.addEventListener('keydown', markAsInteracted);
        });
    }
};

const extreme_polarization_survey = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2 style='font-weight: normal;'>Perceptions of the <b>second</b> social media network (feed) you viewed</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <div>How <b>politically extreme</b> do you think members of the <b>second</b> social media network you viewed are?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('poli_extreme', 5)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Not at all extreme</span>
                        <span>2 - Slightly extreme</span>
                        <span>3 - Somewhat extreme</span>
                        <span>4 - Fairly extreme</span>
                        <span>5 - Completely extreme</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>How much do you think members of the <b>second</b> social media network you viewed <b>dislike their political outgroup</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('affect_polarization', 5)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Not at all</span>
                        <span>2 - Slightly</span>
                        <span>3 - Somewhat</span>
                        <span>4 - Fairly</span>
                        <span>5 - Completely</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    button_label: "Next >",

    on_load: function() {

        setupLikertScales();

        // window.removeRequiredAttributes();
    }
};








const prescriptiveSurvey_ownNetwork = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2 style='font-weight: normal;'>Perceptions of <b>your personal</b> social media networks</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <div>In your social media networks, how socially appropriate do you think it is to <b>post a message that blames others</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('blame_prescriptive_ownNetwork', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>In your social media networks, how socially appropriate do you think it is to <b>post a message that praises others</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('praise_prescriptive_ownNetwork', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>In your social media networks, how socially appropriate do you think it is to <b>post a message that is emotional</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('emotion_prescriptive_ownNetwork', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>In your social media networks, how socially appropriate do you think it is to <b>post a message that is political</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('poli_prescriptive_ownNetwork', 7)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Very socially inappropriate</span>
                        <span>2</span>
                        <span>3</span>
                        <span>4 - Completely neutral</span>
                        <span>5</span>
                        <span>6</span>
                        <span>7 - Very socially appropriate</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    button_label: "Next >",

    on_load: function() {

        setupLikertScales();

        // window.removeRequiredAttributes();
    }
};

// descriptive survey with slider questions about perceived percentages in the social network
const descriptiveSurvey_ownNetwork = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2 style='font-weight: normal;'>Perceptions of <b>your personal</b> social media networks</h2>",
    html: `
        <div class="survey-container" style="margin-bottom: 40px;">
            <div class="survey-question">
                <label for="blame_descriptive_ownNetwork" style="font-weight: normal;">In your social media networks, what percentage of people typically <b>post messages that blame others</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="blame_descriptive_ownNetwork" name="blame_descriptive_ownNetwork" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="blame_descriptive_ownNetwork" id="blame_descriptive_ownNetwork_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container" style="margin-bottom: 40px;">
            <div class="survey-question">
                <label for="praise_descriptive_ownNetwork" style="font-weight: normal;">In your social media networks, what percentage of people typically <b>post messages that praise others</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="praise_descriptive_ownNetwork" name="praise_descriptive_ownNetwork" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="praise_descriptive_ownNetwork" id="praise_descriptive_ownNetwork_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container" style="margin-bottom: 40px;">
            <div class="survey-question">
                <label for="emotion_descriptive_ownNetwork" style="font-weight: normal;">In your social media networks, what percentage of people typically <b>post messages that are emotional</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="emotion_descriptive_ownNetwork" name="emotion_descriptive_ownNetwork" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="emotion_descriptive_ownNetwork" id="emotion_descriptive_ownNetwork_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <label for="political_descriptive_ownNetwork" style="font-weight: normal;">In your social media networks, what percentage of people typically <b>post messages that are political</b>?</label>
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>100%</span>
                    </div>
                    <input type="range" id="political_descriptive_ownNetwork" name="political_descriptive_ownNetwork" min="0" max="100" value="50" step="1" required data-interacted="false">
                    <div class="slider-value">
                        <output for="political_descriptive_ownNetwork" id="political_descriptive_ownNetwork_value">50%</output>
                    </div>
                </div>
            </div>
        </div>
        <div id="validation-message-ownNetwork" style="color: red; font-weight: bold; margin-top: 20px; display: none;">
            Please interact with all sliders before proceeding.
        </div>
    `,
    button_label: "Next >",
    on_load: function() {
        const sliders = ['blame_descriptive_ownNetwork', 'praise_descriptive_ownNetwork', 'emotion_descriptive_ownNetwork', 'political_descriptive_ownNetwork'];
        
        sliders.forEach(sliderId => {
            const slider = document.getElementById(sliderId);
            const output = document.getElementById(`${sliderId}_value`);
            
            // Set initial custom validity to require interaction
            slider.setCustomValidity('Please interact with this slider.');
            
            // Function to mark slider as interacted
            function markAsInteracted() {
                slider.setAttribute('data-interacted', 'true');
                slider.setCustomValidity('');
                
                // Hide validation message if all sliders have been interacted with
                const allInteracted = sliders.every(id => 
                    document.getElementById(id).getAttribute('data-interacted') === 'true'
                );
                if (allInteracted) {
                    document.getElementById('validation-message-ownNetwork').style.display = 'none';
                }
            }
            
            // Track when slider is interacted with (multiple event types)
            slider.addEventListener('input', function() {
                output.value = this.value + '%';
                markAsInteracted();
            });
            
            // Also listen for mouse and keyboard interactions
            slider.addEventListener('mousedown', markAsInteracted);
            slider.addEventListener('touchstart', markAsInteracted);
            slider.addEventListener('keydown', markAsInteracted);
        });
    }
};

const extreme_polarization_survey_ownNetwork = {
    type: jsPsychSurveyHtmlForm,
    preamble: "<h2 style='font-weight: normal;'>Perceptions of <b>your personal</b> social media networks</h2>",
    html: `
        <div class="survey-container">
            <div class="survey-question">
                <div>How <b>politically extreme</b> do you think members of your own social media networks are?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('poli_extreme_ownNetwork', 5)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Not at all extreme</span>
                        <span>2 - Slightly extreme</span>
                        <span>3 - Somewhat extreme</span>
                        <span>4 - Fairly extreme</span>
                        <span>5 - Completely extreme</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="survey-container">
            <div class="survey-question">
                <div>How much do you think members of your own social media networks <b>dislike their political outgroup</b>?</div>
                <div class="likert-container">
                    <div class="likert-scale">
                        ${createLikertOptions('affect_polarization_ownNetwork', 5)}
                    </div>
                    <div class="likert-labels">
                        <span>1 - Not at all</span>
                        <span>2 - Slightly</span>
                        <span>3 - Somewhat</span>
                        <span>4 - Fairly</span>
                        <span>5 - Completely</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    button_label: "Next >",

    on_load: function() {

        setupLikertScales();

        // window.removeRequiredAttributes();
    }
};





// export surveys so they can be imported in the main file
if (typeof module !== 'undefined') {
    module.exports = {
        demographicsSurvey,
        politicalSurvey,
        socialMediaSurvey,
        prescriptiveSurvey,
        descriptiveSurvey,
        extreme_polarization_survey,
        prescriptiveSurvey_ownNetwork,
        descriptiveSurvey_ownNetwork,
        extreme_polarization_survey_ownNetwork
    };
}