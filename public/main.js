const jsPsych = initJsPsych({
    use_webaudio: false, // gets rid of AudioContext console warning, but not working

    on_finish: function() {

        let allData = jsPsych.data.get();
        // console.log("Raw data:", allData.values()); // debug log
        
        // function to flatten survey responses
        function flattenSurveyResponses(data) {
            if (data.response) {
                // initialize all fields with default values (in case participant is able to bypass a question)
                const defaultData = {
                    blame_prescriptive: '',
                    praise_prescriptive: '',
                    emotion_prescriptive: '',
                    poli_prescriptive: '',
                    blame_descriptive: '',
                    praise_descriptive: '',
                    emotion_descriptive: '',
                    political_descriptive: '',
                    poli_extreme: '',
                    affect_polarization: '',
                    blame_prescriptive_ownNetwork: '',
                    praise_prescriptive_ownNetwork: '',
                    emotion_prescriptive_ownNetwork: '',
                    poli_prescriptive_ownNetwork: '',
                    blame_descriptive_ownNetwork: '',
                    praise_descriptive_ownNetwork: '',
                    emotion_descriptive_ownNetwork: '',
                    political_descriptive_ownNetwork: '',
                    poli_extreme_ownNetwork: '',
                    affect_polarization_ownNetwork: '',
                    gender: '',
                    age: '',
                    language: '',
                    education: '',
                    employment: '',
                    party: '',
                    party_lean: '',
                    political_ideology: '',
                    political_follow: '',
                    rep_id: '',
                    dem_id: '',
                    sm_use: '',
                    sm_use_slider: '',
                    sm_use_poli: '',
                    sm_use_poli_slider: '',
                    sm_post_poli: '',
                    sm_post_poli_slider: '',
                    share_why: '', // initialize as an empty array for multi-select
                };

                // merge collected data with default data
                data.response = { ...defaultData, ...data.response };

                // concatenate share_whycheckbox values
                const shareWhyKeys = [
                    'share_why_1',
                    'share_why_2',
                    'share_why_3',
                    'share_why_4',
                    'share_why_5',
                    'share_why_6',
                    'share_why_7'
                ];

                data.response.share_why = shareWhyKeys
                    .filter(key => data.response[key])
                    .map(key => data.response[key])
                    .join(', ');

                Object.entries(data.response).forEach(([key, value]) => {
                    data[key] = value;
                });
                delete data.response;
            }
            return data;
        }

        // flatten survey responses
        allData.filter({trial_type: 'survey-html-form'}).values().forEach(flattenSurveyResponses);
        
        // The descriptive survey is now handled as part of the survey-html-form processing above
        // No separate handling needed since it uses the same flattenSurveyResponses function

        // var csv = allData.csv // collects all data
        // filter out unnecessary columns - but first handle social media feed flattening
        
        // Create flattened data by processing the jsPsych data directly
        let allTrials = allData.values();
        let flattenedTrials = [];
        
        allTrials.forEach(trial => {
            if (trial.trial_type === 'social-media-feed' && trial.images_shown && Array.isArray(trial.images_shown)) {
                // Flatten this trial into multiple rows
                trial.images_shown.forEach((imagePath, index) => {
                    const fileName = imagePath.split('/').pop();
                    
                    const flattenedTrial = {
                        ...trial, // Copy all original trial data
                        image_shown: fileName,
                        image_category: getImageCategory(fileName),
                        feed_duration_seconds: (index === trial.images_shown.length - 1) ? trial.feed_duration_seconds : '',
                        post_dwell_seconds: trial.post_dwell_times ? trial.post_dwell_times[index] : '',
                        feed_source: trial.feed_sources ? trial.feed_sources[index] : '',
                        like_state: trial.like_states ? trial.like_states[index] : false,
                        share_state: trial.share_states ? trial.share_states[index] : false,
                        image_index: index + 1,
                        scroll_to_bottom: (index === trial.images_shown.length - 1) ? trial.scroll_to_bottom : undefined
                    };
                    
                    // Remove the array fields
                    delete flattenedTrial.images_shown;
                    delete flattenedTrial.like_states;
                    delete flattenedTrial.share_states;
                    delete flattenedTrial.liked_images;
                    delete flattenedTrial.shared_images;
                    delete flattenedTrial.feed_sources;
                    delete flattenedTrial.post_dwell_times;
                    
                    flattenedTrials.push(flattenedTrial);
                });
            } else {
                // Keep original trial as-is
                flattenedTrials.push(trial);
            }
        });
        
        // Create a new data object with the flattened trials
        const flattenedData = {
            values: () => flattenedTrials,
            filterColumns: (columns) => ({
                csv: () => {
                    if (flattenedTrials.length === 0) return '';
                    
                    const headers = columns.join(',');
                    const rows = flattenedTrials.map(row => 
                        columns.map(col => {
                            const value = row[col];
                            if (typeof value === 'string' && value.includes(',')) {
                                return `"${value}"`;
                            }
                            return value || '';
                        }).join(',')
                    );
                    
                    return [headers, ...rows].join('\n');
                }
            })
        };

        // Use the processed data for filtering columns (exactly like main.js)
        var csv = flattenedData.filterColumns([
            'prolific_id', 
            'participant_id', 
            'trial_type', 
            'trial_index', 
            'image_shown',
            'image_category',
            'feed_duration_seconds',
            'post_dwell_seconds',
            'feed_source',
            'like_state',
            'share_state',
            'image_index',
            'scroll_to_bottom',
            'political_affiliation',  // from pre-survey
            'condition',              // algorithmic vs control condition
            'consented',
            'blame_prescriptive',
            'praise_prescriptive',
            'emotion_prescriptive',
            'poli_prescriptive',
            'blame_descriptive',
            'praise_descriptive',
            'emotion_descriptive',
            'political_descriptive',
            'poli_extreme',
            'affect_polarization',
            'blame_prescriptive_ownNetwork',
            'praise_prescriptive_ownNetwork',
            'emotion_prescriptive_ownNetwork',
            'poli_prescriptive_ownNetwork',
            'blame_descriptive_ownNetwork',
            'praise_descriptive_ownNetwork',
            'emotion_descriptive_ownNetwork',
            'political_descriptive_ownNetwork',
            'poli_extreme_ownNetwork',
            'affect_polarization_ownNetwork',
            'gender', 
            'age', 
            'language', 
            'education', 
            'employment', 
            'party', 
            'party_lean', 
            'political_ideology', 
            'political_follow', 
            'rep_id', 
            'dem_id', 
            'sm_use', 
            'sm_use_slider', 
            'sm_use_poli', 
            'sm_use_poli_slider', 
            'sm_post_poli', 
            'sm_post_poli_slider', 
            'share_why'
        ]).csv();

        // console.log("Filtered CSV data length:", csv.length); // Debug log
        // console.log("First 100 characters of CSV:", csv.substring(0, 100)); // Debug log
        
        if (!csv || csv.length === 0) {
            console.error("No data collected during experiment!");
            document.body.innerHTML = '<p>There was an error saving your data. Please contact the researcher.</p>';
            return;
        }
        
        saveExperimentData(csv)
            .then(() => {
                document.body.innerHTML = `
                    <div style="text-align: center; margin-top: 50px;">
                        <p>Thank you for participating! 
                        <a href="https://app.prolific.com/submissions/complete?cc=CS7I5JAE" target="_blank">
                            <b>Click here</b></a> to be redirected to Prolific (completion code <b>CS7I5JAE</b>).
                        </p>
                    </div>
                `;
            })
            .catch(error => {
                console.error('Error saving data:', error);
                document.body.innerHTML = '<p>There was an error saving your data.</p>';
            });
    }
});

// API gateway URLs
const GET_PARTICIPANT_ID_URL = 'https://76mck84wq2.execute-api.us-east-2.amazonaws.com/get-participant-id';
const SAVE_DATA_URL = 'https://76mck84wq2.execute-api.us-east-2.amazonaws.com/save-jspsych-data';

// function to get participant ID
async function getParticipantId(prolificId, politicalAffiliation) {
    console.log('Requesting participant ID for:', prolificId, 'with affiliation:', politicalAffiliation);
    const response = await fetch(`${GET_PARTICIPANT_ID_URL}?prolific_id=${prolificId}&party=${politicalAffiliation}`);
    if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', response.status, errorText);
        throw new Error(`Failed to get participant ID: ${response.status} ${errorText}`);
    }
    const data = await response.json();
    console.log('Received participant ID:', data.participantID);
    return data.participantID;
}

// function to save experiment data
async function saveExperimentData(csvData) {
    try {
        if (!csvData || csvData.length === 0) {
            throw new Error('No data to save');
        }

        // console.log('Attempting to save data of size:', csvData.length);
        // console.log('First 100 characters of data:', csvData.substring(0, 100));
        
        const payload = JSON.stringify({ csv: csvData });
        // console.log('Payload size:', payload.length);

        const response = await fetch(SAVE_DATA_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: payload
        });

        // console.log('Response status:', response.status);
        // console.log('Response headers:', Object.fromEntries(response.headers.entries()));

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response body:', errorText);
            throw new Error(`Failed to save experiment data: ${response.status} ${errorText}`);
        }

        const result = await response.json();
        console.log('Save successful:', result.message);
        return result;
    } catch (error) {
        console.error('Detailed save error:', error);
        throw error;
    }
}

// ************************************************************************************************************* 
// NEW IMAGE SORTING SECTION ***********************************************************************************
// *************************************************************************************************************

const imageCategories = {
    // democrat ingroup praise (Slides 1-5, 31-35, 61-65, etc.)
    'dem_ingroup_praise': [1,2,3,4,5, 31,32,33,34,35, 61,62,63,64,65, 91,92,93,94,95, 121,122,123,124,125, 
                           151,152,153,154,155, 181,182,183,184,185, 211,212,213,214,215, 241,242,243,244,245, 271,272,273,274,275, 
                           301,302,303,304,305, 331,332,333,334,335, 361,362,363,364,365, 391,392,393,394,395, 421,422,423,424,425, 
                           451,452,453,454,455, 481,482,483,484,485, 511,512,513,514,515, 541,542,543,544,545, 571,572,573,574,575
                        ],
    
    // democratoutgroup blame (Slides 6-10, 36-40, 66-70, etc.)
    'dem_outgroup_blame': [6,7,8,9,10, 36,37,38,39,40, 66,67,68,69,70, 96,97,98,99,100, 126,127,128,129,130, 
                           156,157,158,159,160, 186,187,188,189,190, 216,217,218,219,220, 246,247,248,249,250, 276,277,278,279,280, 
                           306,307,308,309,310, 336,337,338,339,340, 366,367,368,369,370, 396,397,398,399,400, 426,427,428,429,430, 
                           456,457,458,459,460, 486,487,488,489,490, 516,517,518,519,520, 546,547,548,549,550, 576,577,578,579,580
                        ],
    
    // republican ingroup praise (Slides 21-25, 51-55, 81-85, etc.)
    'rep_ingroup_praise': [21,22,23,24,25, 51,52,53,54,55, 81,82,83,84,85, 111,112,113,114,115, 141,142,143,144,145, 
                           171,172,173,174,175, 201,202,203,204,205, 231,232,233,234,235, 261,262,263,264,265, 291,292,293,294,295, 
                           321,322,323,324,325, 351,352,353,354,355, 381,382,383,384,385, 411,412,413,414,415, 441,442,443,444,445, 
                           471,472,473,474,475, 501,502,503,504,505, 531,532,533,534,535, 561,562,563,564,565, 591,592,593,594,595
                        ],
    
    // republic outgroup blame (Slides 26-30, 56-60, 86-90, etc.)
    'rep_outgroup_blame': [26,27,28,29,30, 56,57,58,59,60, 86,87,88,89,90, 116,117,118,119,120, 146,147,148,149,150, 
                           176,177,178,179,180, 206,207,208,209,210, 236,237,238,239,240, 266,267,268,269,270, 296,297,298,299,300, 
                           326,327,328,329,330, 356,357,358,359,360, 386,387,388,389,390, 416,417,418,419,420, 446,447,448,449,450, 
                           476,477,478,479,480, 506,507,508,509,510, 536,537,538,539,540, 566,567,568,569,570, 596,597,598,599,600
                        ],
    
    // neutral political (Slides 11-20, 41-50, 71-80, etc.)
    'neutral_political': [11,12,13,14,15,16,17,18,19,20, 41,42,43,44,45,46,47,48,49,50, 71,72,73,74,75,76,77,78,79,80, 
                          101,102,103,104,105,106,107,108,109,110, 131,132,133,134,135,136,137,138,139,140, 161,162,163,164,165,166,167,168,169,170, 
                          191,192,193,194,195,196,197,198,199,200, 221,222,223,224,225,226,227,228,229,230, 251,252,253,254,255,256,257,258,259,260, 
                          281,282,283,284,285,286,287,288,289,290, 311,312,313,314,315,316,317,318,319,320, 341,342,343,344,345,346,347,348,349,350, 
                          371,372,373,374,375,376,377,378,379,380, 401,402,403,404,405,406,407,408,409,410, 431,432,433,434,435,436,437,438,439,440, 
                          461,462,463,464,465,466,467,468,469,470, 491,492,493,494,495,496,497,498,499,500, 521,522,523,524,525,526,527,528,529,530, 
                          551,552,553,554,555,556,557,558,559,560, 581,582,583,584,585,586,587,588,589,590
                        ],
    
    // distractor (Slides 601-700)
    'distractor': Array.from({length: 100}, (_, i) => 601 + i)
};

// Function to determine image category based on slide number
function getImageCategory(fileName) {
    // Extract slide number from filename (e.g., "Slide506.png" -> 506)
    const slideNumber = parseInt(fileName.replace('Slide', '').replace('.png', ''));
    
    // Check each category to find which one contains this slide number
    for (const [category, slides] of Object.entries(imageCategories)) {
        if (slides.includes(slideNumber)) {
            return category;
        }
    }
    
    // Return unknown if not found
    return 'unknown';
}


const firstFeedCategoryQuotas = {
    'dem_ingroup_praise': 14,      // 14% of 100 = 14 images
    'dem_outgroup_blame': 14,      // 14% of 100 = 14 images
    'rep_ingroup_praise': 14,      // 14% of 100 = 14 images
    'rep_outgroup_blame': 14,      // 14% of 100 = 14 images
    'neutral_political': 29,        // 28.6% of 100 = 29 images (rounded)
    'distractor': 15               // 14.3% of 100 = 15 images (rounded)
};


// Function to select balanced images for the first feed
function selectBalancedFirstFeed(participantId) {
    let selectedImages = [];
    
    // For each category, select the specified number of images
    Object.entries(firstFeedCategoryQuotas).forEach(([category, quota]) => {
        // Get all available images for this category
        const categoryImages = imageCategories[category];
        
        // Calculate starting index based on participant ID to ensure different participants get different images
        const startIndex = (participantId - 1) % categoryImages.length;
        
        // Select images starting from the calculated index
        for (let i = 0; i < quota; i++) {
            const imageIndex = (startIndex + i) % categoryImages.length;
            const slideNumber = categoryImages[imageIndex];
            selectedImages.push(`img/full_700/Slide${slideNumber}.png`);
        }
    });
    
    // Shuffle the final selection
    return selectedImages.sort(() => Math.random() - 0.5);
}


// Function to console.log category proportions
function logCategoryProportions(images, feedName) {
    const categoryCounts = {};
    
    // Count images in each category
    images.forEach(imagePath => {
        const fileName = imagePath.split('/').pop(); // Get just the filename
        const category = getImageCategory(fileName);
        categoryCounts[category] = (categoryCounts[category] || 0) + 1;
    });

    console.log('========================\n');
    console.log(`=== ${feedName} Category Analysis ===`);
    console.log(`Total images: ${images.length}`);
    console.log('Category counts:', categoryCounts);
    
    // Log percentages
    Object.entries(categoryCounts).forEach(([category, count]) => {
        const percentage = ((count / images.length) * 100).toFixed(1);
        console.log(`${category}: ${count} images (${percentage}%)`);
    });
}



// Function to determine participant condition (algorithmic vs control)
function getParticipantCondition(participantId) {
    // Odd participant IDs get algorithmic, even get control
    return (participantId % 2 === 1) ? 'algorithmic' : 'control';
}

// Function to select control second feed (similar structure to first feed, but different images)
function selectControlSecondFeed(participantId, firstFeedData) {
    console.log('=== Control Second Feed Selection Process ===');
    
    // Get images shown in first feed to avoid duplicates
    const seenImages = firstFeedData.images_shown || [];
    console.log('Images already seen:', seenImages.length);
    
    // Use the same quotas as first feed
    const controlFeedCategoryQuotas = {
        'dem_ingroup_praise': 14,
        'dem_outgroup_blame': 14,
        'rep_ingroup_praise': 14,
        'rep_outgroup_blame': 14,
        'neutral_political': 29,
        'distractor': 15
    };
    
    let selectedImages = [];
    
    // For each category, select the specified number of images (avoiding seen images)
    Object.entries(controlFeedCategoryQuotas).forEach(([category, quota]) => {
        // Get all available images for this category
        const categoryImages = imageCategories[category];
        
        // Filter out images already seen in first feed
        const availableCategoryImages = categoryImages.filter(slideNumber => {
            const imagePath = `img/full_700/Slide${slideNumber}.png`;
            return !seenImages.includes(imagePath);
        });
        
        // Calculate starting index based on participant ID + offset to get different images than first feed
        const startIndex = ((participantId - 1) + 50) % availableCategoryImages.length; // +50 offset for different selection
        
        // Select images starting from the calculated index
        for (let i = 0; i < quota && i < availableCategoryImages.length; i++) {
            const imageIndex = (startIndex + i) % availableCategoryImages.length;
            const slideNumber = availableCategoryImages[imageIndex];
            selectedImages.push(`img/full_700/Slide${slideNumber}.png`);
        }
    });
    
    // Shuffle the final selection
    const shuffledImages = selectedImages.sort(() => Math.random() - 0.5);
    
    console.log('=== Control Second Feed Final Composition ===');
    console.log('Total images:', shuffledImages.length);
    console.log('Control condition: same structure as first feed, different images');
    
    // Log category analysis
    logCategoryProportions(shuffledImages, 'Control Second Feed');
    
    // Create source map (all images are "control" source for this condition)
    const imageSourceMap = {};
    shuffledImages.forEach(img => imageSourceMap[img] = 'control');
    
    return {
        images: shuffledImages,
        sourceMap: imageSourceMap
    };
}

// Function to select images for the second feed based on first feed interactions
function selectPersonalizedSecondFeed(participantId, firstFeedData, politicalAffiliation) {
    // Algorithm accuracy parameter - 95% personalized, 5% random noise
    const ALGORITHM_ACCURACY = 0.95;
    
    console.log('=== Second Feed Selection Process ===');
    console.log('Political affiliation:', politicalAffiliation);
    
    // Get images shown in first feed
    const seenImages = firstFeedData.images_shown || [];
    console.log('Images already seen:', seenImages.length);
    
    // Get liked and shared images
    const likedImages = firstFeedData.liked_images || [];
    const sharedImages = firstFeedData.shared_images || [];
    const interactedImages = [...new Set([...likedImages, ...sharedImages])];
    
    console.log('Images liked:', likedImages.length);
    console.log('Images shared:', sharedImages.length);
    console.log('Total interactions:', interactedImages.length);
    
    // Analyze categories of interacted images
    const interactionCategoryCounts = {};
    interactedImages.forEach(imagePath => {
        const fileName = imagePath.split('/').pop();
        const category = getImageCategory(fileName);
        interactionCategoryCounts[category] = (interactionCategoryCounts[category] || 0) + 1;
    });
    
    console.log('Categories interacted with:', interactionCategoryCounts);
    
    // Get all available images (excluding already seen)
    const allAvailableImages = [];
    for (let i = 1; i <= 700; i++) {
        const imagePath = `img/full_700/Slide${i}.png`;
        if (!seenImages.includes(imagePath)) {
            allAvailableImages.push(imagePath);
        }
    }
    
    console.log('Available unseen images:', allAvailableImages.length);
    
    // Group available images by category
    const availableByCategory = {};
    Object.keys(imageCategories).forEach(category => {
        availableByCategory[category] = [];
    });
    
    allAvailableImages.forEach(imagePath => {
        const fileName = imagePath.split('/').pop();
        const category = getImageCategory(fileName);
        if (availableByCategory[category]) {
            availableByCategory[category].push(imagePath);
        }
    });
    
    // Calculate personalized selections (50 images)
    const personalizedImages = [];
    const totalInteractions = interactedImages.length;
    
    if (totalInteractions > 0) {
        // Calculate how many images to select from each category based on interactions
        Object.entries(interactionCategoryCounts).forEach(([category, count]) => {
            const proportion = count / totalInteractions;
            const targetPersonalizedCount = Math.round(proportion * 50); // 50% of 100 images
            
            console.log(`${category}: ${count} interactions (${(proportion*100).toFixed(1)}%) -> ${targetPersonalizedCount} target personalized images`);
            
            // Apply 95/5 algorithm accuracy - some selections will be random instead of personalized
            for (let i = 0; i < targetPersonalizedCount; i++) {
                if (Math.random() < ALGORITHM_ACCURACY) {
                    // 95% chance: Select from the preferred category (personalized)
                    const categoryImages = availableByCategory[category] || [];
                    if (categoryImages.length > 0) {
                        const shuffled = categoryImages.sort(() => Math.random() - 0.5);
                        const selected = shuffled[0];
                        if (selected && !personalizedImages.includes(selected)) {
                            personalizedImages.push(selected);
                            // Remove from available to avoid duplicates
                            const index = availableByCategory[category].indexOf(selected);
                            if (index > -1) {
                                availableByCategory[category].splice(index, 1);
                            }
                        }
                    }
                } else {
                    // 5% chance: Select randomly from any category (algorithm "mistake")
                    const allAvailable = Object.values(availableByCategory).flat();
                    const randomlyAvailable = allAvailable.filter(img => !personalizedImages.includes(img));
                    if (randomlyAvailable.length > 0) {
                        const shuffled = randomlyAvailable.sort(() => Math.random() - 0.5);
                        const selected = shuffled[0];
                        personalizedImages.push(selected);
                        
                        // Remove from appropriate category to avoid duplicates
                        const fileName = selected.split('/').pop();
                        const selectedCategory = getImageCategory(fileName);
                        const catImages = availableByCategory[selectedCategory];
                        if (catImages) {
                            const index = catImages.indexOf(selected);
                            if (index > -1) {
                                catImages.splice(index, 1);
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Fill remaining personalized slots if needed
    const remainingPersonalized = 50 - personalizedImages.length;
    if (remainingPersonalized > 0) {
        console.log(`Need ${remainingPersonalized} more personalized images - filling randomly`);
        const unusedImages = allAvailableImages.filter(img => !personalizedImages.includes(img));
        const shuffled = unusedImages.sort(() => Math.random() - 0.5);
        personalizedImages.push(...shuffled.slice(0, remainingPersonalized));
    }
    
    // Select community images (50 images) - from political affiliation-specific directory
    const communityImages = [];
    
    // Determine which directory to use based on political affiliation
    let communityDirectory;
    if (politicalAffiliation === 'democrat' || politicalAffiliation === 'lean_democrat') {
        communityDirectory = 'img/stim_set_top_100_like_share_dem';
    } else if (politicalAffiliation === 'republican' || politicalAffiliation === 'lean_republican') {
        communityDirectory = 'img/stim_set_top_100_like_share_rep';
    } else {
        // Fallback to dem directory if affiliation is unclear
        communityDirectory = 'img/stim_set_top_100_like_share_dem';
        console.log('Warning: Unknown political affiliation, defaulting to dem directory');
    }
    
    console.log('Using community directory:', communityDirectory);
    
    // Define the actual slide numbers in each directory
    // Note: These need to match the actual files in your directories
    let communitySlideNumbers;
    if (politicalAffiliation === 'democrat' || politicalAffiliation === 'lean_democrat') {
        // Slide numbers in stim_set_top_100_like_share_dem directory
        communitySlideNumbers = [1, 3, 5, 6, 7, 8, 10, 11, 13, 33, 50, 62, 66, 91, 92, 94, 95, 98, 
                                 102, 105, 106, 110, 122, 124, 126, 127, 130, 151, 152, 153, 154, 156, 157, 159, 181, 189, 190, 
                                 220, 221, 241, 242, 243, 244, 245, 248, 253, 271, 272, 276, 277, 278, 279, 280, 283, 
                                 303, 304, 305, 306, 308, 309, 310, 313, 314, 336, 361, 362, 363, 364, 366, 374, 376, 397, 398, 
                                 424, 459, 487, 488, 499, 
                                 512, 514, 516, 517, 519, 542, 543, 546, 549, 554, 572, 573, 574, 578, 579, 580, 581, 587, 
                                 602, 642, 643, 646
                                ];
    } else {
        // Slide numbers in stim_set_top_100_like_share_rep directory
        communitySlideNumbers = [21, 23, 24, 28, 29, 58, 59, 81, 83, 85, 86, 87, 88, 89, 
                                 113, 114, 116, 120, 141, 143, 146, 147, 149, 168, 171, 174, 175, 176, 178, 179, 191, 
                                 206, 231, 232, 233, 236, 239, 240, 291, 292, 293, 299, 
                                 300, 313, 314, 321, 323, 324, 351, 354, 356, 357, 358, 360, 381, 
                                 412, 413, 414, 415, 417, 418, 420, 433, 441, 443, 444, 446, 448, 449, 471, 474, 475, 476, 479, 
                                 502, 504, 507, 509, 532, 533, 535, 537, 562, 563, 567, 570, 591, 593, 595, 596, 597, 
                                 602, 604, 608, 633, 642, 643, 645, 646, 692
                                ];
    }
    
    // Generate list of images from the appropriate directory using actual slide numbers
    const communityPool = communitySlideNumbers.map(slideNum => `${communityDirectory}/Slide${slideNum}.png`);
    
    // Filter out any images that were already shown in first feed or selected for personalization
    // Extract slide numbers from seen images and personalized images for proper comparison
    const seenSlideNumbers = seenImages.map(img => {
        const match = img.match(/Slide(\d+)\.png/);
        return match ? parseInt(match[1]) : null;
    }).filter(num => num !== null);
    
    const personalizedSlideNumbers = personalizedImages.map(img => {
        const match = img.match(/Slide(\d+)\.png/);
        return match ? parseInt(match[1]) : null;
    }).filter(num => num !== null);
    
    const allUsedSlideNumbers = [...seenSlideNumbers, ...personalizedSlideNumbers];
    
    const availableCommunityImages = communityPool.filter(img => {
        const match = img.match(/Slide(\d+)\.png/);
        const slideNumber = match ? parseInt(match[1]) : null;
        return slideNumber && !allUsedSlideNumbers.includes(slideNumber);
    });
    
    console.log('Available community images:', availableCommunityImages.length);
    
    // Select 50 random images from available community images
    const shuffledCommunity = availableCommunityImages.sort(() => Math.random() - 0.5);
    communityImages.push(...shuffledCommunity.slice(0, 50));
    
    // Create source mapping for each image
    const imageSourceMap = {};
    personalizedImages.forEach(img => imageSourceMap[img] = 'personalized');
    communityImages.forEach(img => imageSourceMap[img] = 'community');
    
    // Combine and shuffle final selection
    const finalImages = [...personalizedImages, ...communityImages];
    const shuffledFinal = finalImages.sort(() => Math.random() - 0.5);
    
    console.log('=== Second Feed Final Composition ===');
    console.log('Personalized images:', personalizedImages.length);
    console.log('Community images:', communityImages.length);
    console.log('Total images:', shuffledFinal.length);
    console.log(`Algorithm accuracy: ${(ALGORITHM_ACCURACY * 100)}% personalized, ${((1-ALGORITHM_ACCURACY) * 100)}% random noise`);
    
    // Log final category analysis
    logCategoryProportions(shuffledFinal, 'Second Feed');
    
    return {
        images: shuffledFinal,
        sourceMap: imageSourceMap
    };
}

// ************************************************************************************************************* 
// END NEW IMAGE SORTING SECTION **********************************************************************************
// *************************************************************************************************************

// function to generate a list of images for each participant
function generateImageList(ParticipantID, politicalParty) {

    let baseFolder;
    let numImages;
    let availableSlides;
    
    if (politicalParty === 'democrat' || politicalParty === 'lean_democrat') {
        baseFolder = 'dem';
        numImages = 20;
        availableSlides = slideNumbers.dem;
    } else if (politicalParty === 'republican' || politicalParty === 'lean_republican') {
        baseFolder = 'rep';
        numImages = 20;
        availableSlides = slideNumbers.rep;
    } else {
        console.error('Invalid political party');
        return [];
    }

    let images = [];
    for (let k = 0; k < numImages; k++) {
        let array_index;
        if (baseFolder === 'dem') {
            array_index = ((ParticipantID - 1 + 20 * k) % availableSlides.length);
        } else {
            array_index = ((ParticipantID - 1 + 20 * k) % availableSlides.length);
        }
        const actualSlideNumber = availableSlides[array_index];
        images.push(`img/${baseFolder}/Slide${actualSlideNumber}.png`);
    }
    
    return images;
}

// main experiment setup function
async function setupExperiment() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const prolificID = urlParams.get('PROLIFIC_PID');
        console.log('Extracted Prolific ID from URL:', prolificID);
        
        if (!prolificID) {
            throw new Error('No Prolific ID provided');
        }

        var timeline = [];

        var welcome = {
            type: jsPsychInstructions,
            pages: ["<div class='instructions'>Welcome! In this task, you will be scrolling through mock social media feeds. The posts you will see are <b>real messages</b> we've pulled from social media (e.g., X, Bluesky), but we've scrambled the usernames for privacy.<br><br>As you scroll through the feeds, you can <b>like</b> and <b>share</b> posts that you find interesting, just like on a real social media platform. After viewing the feeds, we'll ask you some questions about the content you viewed as well as your own experience using social media.<br><br>Before we begin, please click <b>Next</b> to consent to participate.</div>"],
            show_clickable_nav: true
        };
        timeline.push(welcome);

        timeline.push(consent);

        timeline.push(prePolSurvey);

        // var debugTrial = {
        //     type: jsPsychCallFunction,
        //     func: function() {
        //         const lastTrial = jsPsych.data.get().last(1).values()[0];
        //         console.log("Pre-survey data:", lastTrial);
        //         console.log("Political affiliation:", lastTrial.political_affiliation);
        //     }
        // };
        // timeline.push(debugTrial);

        // Create a variable to store the participant ID and images
        let ParticipantID;  // Add this line
        let participant_images;

        // Add a call-function trial to get participant ID after political survey
        var getParticipantIdTrial = {
            type: jsPsychCallFunction,
            async: true,
            func: async function(done) {  // Add done parameter
                try {
                    const politicalAffiliation = jsPsych.data.get().last(1).values()[0].political_affiliation;
                    // console.log("Getting participant ID for affiliation:", politicalAffiliation);
                    
                    ParticipantID = await getParticipantId(prolificID, politicalAffiliation);
                    // console.log("Successfully received ParticipantID:", ParticipantID);
                    
                    jsPsych.data.addProperties({participant_id: ParticipantID, prolific_id: prolificID});
                    
                    done(); // Signal that the async operation is complete
                } catch (error) {
                    console.error("Error in getParticipantIdTrial:", error);
                    document.body.innerHTML = '<p>There was an error assigning your participant ID. Please contact the researcher.</p>';
                }
            }
        };
        timeline.push(getParticipantIdTrial);

        // Instructions before first social media feed
        var preFirstFeedInstructions = {
            type: jsPsychInstructions,
            pages: ["<div class='instructions'>Great! Now you're ready to begin the main task.<br><br>You will see a social media feed with posts from various users. As you scroll through the feed, your job is simply to <b>like</b> and <b>share</b> posts that you find interesting by clicking the like (<svg class='icon' viewBox='0 0 24 24' style='width: 20px; height: 20px; display: inline-block; vertical-align: middle; fill: #e91e63;'><path d='M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41 0.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z'/></svg>) or share (<svg class='icon' viewBox='0 0 24 24' style='width: 20px; height: 20px; display: inline-block; vertical-align: middle; stroke: #27ae60; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;'><path d='M16 3l4 4-4 4'/><path d='M20 7H8a4 4 0 0 0-4 4'/><path d='M8 21l-4-4 4-4'/><path d='M4 17h12a4 4 0 0 0 4-4'/></svg>) buttons.<br><br>Please scroll through the entire feed at your own pace. You will be able to scroll back up if you'd like to re-read a post.<br><br>Press <b>Next</b> to start viewing the feed.</div>"],
            show_clickable_nav: true
        };
        timeline.push(preFirstFeedInstructions);


        // NEW: SCROLLING SOCIAL MEDIA FEED TRIALS
        // Section 1 with random control images
        var firstFeedTrial = {
            type: jsPsychSocialMediaFeed,
            images: function() {
                const selectedImages = selectBalancedFirstFeed(ParticipantID);
                
                // Log the category analysis
                logCategoryProportions(selectedImages, 'First Feed');
                
                return selectedImages;
            },
            require_scroll_to_bottom: true
        };
        timeline.push(firstFeedTrial);

        // Instructions between sections 1 & 2
        var betweenSectionsInstructions = {
            type: jsPsychInstructions,
            pages: ["<div class='instructions'>Great! You've completed the first section.<br><br>Now you'll see another social media feed. Just like before, you can <b>like</b> and <b>share</b> posts that interest you. <br><br>After you finish scrolling through the second feed, we will ask you some questions about its content.<br><br>Press <b>Next</b> to view the feed.</div>"],
            show_clickable_nav: true
        };
        timeline.push(betweenSectionsInstructions);

        // Second social media feed section
        // Section 2 with condition-based selection (algorithmic vs control)
        var secondFeedTrial = {
            type: jsPsychSocialMediaFeed,
            images: function() {
                // Get data from first feed
                const firstFeedData = jsPsych.data.get().filter({trial_type: 'social-media-feed'}).last(1).values()[0];
                
                // Determine participant condition
                const condition = getParticipantCondition(ParticipantID);
                console.log('Participant condition:', condition);
                
                let secondFeedResult;
                
                if (condition === 'control') {
                    // Control condition: similar structure to first feed, different images
                    secondFeedResult = selectControlSecondFeed(ParticipantID, firstFeedData);
                } else {
                    // Algorithmic condition: personalized based on first feed interactions
                    const politicalAffiliation = jsPsych.data.get().last(1).values()[0].political_affiliation;
                    secondFeedResult = selectPersonalizedSecondFeed(ParticipantID, firstFeedData, politicalAffiliation);
                }
                
                // Store the source map globally so the plugin can access it
                window.currentFeedSourceMap = secondFeedResult.sourceMap;
                
                // Store condition in jsPsych data
                jsPsych.data.addProperties({condition: condition});
                
                return secondFeedResult.images;
            },
            require_scroll_to_bottom: true
        };
        timeline.push(secondFeedTrial);

        // END OF SOCIAL MEDIA FEED TRIALS



        var demo_instruct_1 = {
            type: jsPsychInstructions,
            pages: ["<div class='instructions'>Thank you for scrolling through the social media feeds.<br><br>You will now answer a few questions about the content in the <b>second</b> feed you just viewed.<br><br>Please press <b>Next</b> to continue.</div>"],
            show_clickable_nav: true
        };
        timeline.push(demo_instruct_1);

        timeline.push(prescriptiveSurvey);

        timeline.push(descriptiveSurvey);

        timeline.push(extreme_polarization_survey);

        var demo_instruct_2 = {
            type: jsPsychInstructions,
            pages: ["<div class='instructions'>Now that you've judged the social media feeds from our experiment, we'd like to ask you some questions about <b>your personal social media networks</b>.<br><br>When answering these questions, think about the experience you've had while scrolling on the social media platforms you use most frequently, also keeping in mind that <b>our experiment feeds are meant to simulate real social media feeds</b>.<br><br>Please press <b>Next</b> to continue.</div>"],
            show_clickable_nav: true
        };
        timeline.push(demo_instruct_2);

        timeline.push(prescriptiveSurvey_ownNetwork);

        timeline.push(descriptiveSurvey_ownNetwork);

        timeline.push(extreme_polarization_survey_ownNetwork);

        var demo_instruct_2  = {
            type: jsPsychInstructions,
            pages: ["<div class='instructions'>Thanks for providing your responses.<br><br>To finish the survey, we would like you to answer a few short demographics questions, after which you will be redirected back to Prolific.<br><br>Please press <b>Next</b> to continue.</div>"],
            show_clickable_nav: true
        };
        timeline.push(demo_instruct_2);

        timeline.push(demographicsSurvey);
        timeline.push(politicalSurvey);
        timeline.push(socialMediaSurvey);       

        jsPsych.run(timeline);

    } catch (error) {
        console.error('Error setting up experiment:', error);
        document.body.innerHTML = '<p>There was an error setting up the experiment. Please contact the researcher.</p>';
    }
}

// Start the experiment
setupExperiment();