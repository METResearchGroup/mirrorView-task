var jsPsychSocialMediaFeed = (function (jspsych) {
  'use strict';

  const info = {
    name: "social-media-feed",
    version: "1.0.0",
    parameters: {
      images: {
        type: jspsych.ParameterType.ARRAY,
        default: []
      },
      trial_duration: {
        type: jspsych.ParameterType.INT,
        default: null
      },
      require_scroll_to_bottom: {
        type: jspsych.ParameterType.BOOL,
        default: true
      }
    },
    data: {
      images_shown: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      },
      like_states: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      },
      share_states: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      },
      liked_images: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      },
      shared_images: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      },
      scroll_to_bottom: {
        type: jspsych.ParameterType.BOOL
      },
      feed_sources: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      },
      feed_duration_seconds: {
        type: jspsych.ParameterType.FLOAT
      },
      post_dwell_times: {
        type: jspsych.ParameterType.ARRAY,
        array: true
      }
    }
  };

  class SocialMediaFeedPlugin {
    constructor(jsPsych) {
      this.jsPsych = jsPsych;
    }
    
    static info = info;
    
    trial(display_element, trial) {
      // Record start time for duration tracking
      var startTime = performance.now();
      
      // Create the feed container
      var feedHTML = `
        <div class="social-media-feed-container">
          <div class="feed-header">
            <h2>Social Media Feed</h2>
            <p>Scroll through the posts below. You can like and share posts you find interesting.</p>
          </div>
          <div class="feed-content" id="feed-content">
            ${trial.images.map((img, index) => `
              <div class="feed-post" data-image="${img}" data-index="${index}">
                <div class="post-content">
                  <img src="${img}" alt="Post content" class="post-image">
                </div>
                <div class="post-actions" style="display: flex; justify-content: flex-end; padding: 15px; border-top: 1px solid #f1f3f4;">
                <button class="like-btn" data-index="${index}" onclick="toggleLike(${index})" aria-pressed="false" aria-label="Like">
                  <svg class="icon like-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path class="heart" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 
                        2 5.42 4.42 3 7.5 3c1.74 0 3.41 0.81 4.5 2.09C13.09 3.81 
                        14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 
                        11.54L12 21.35z"/>
                  </svg>
                  <span class="like-count">0</span>
                </button>
                <button class="share-btn" data-index="${index}" onclick="toggleShare(${index})" aria-pressed="false" aria-label="Repost">
                  <svg class="icon share-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <!-- Two bent arrows, stroke-only; uses currentColor -->
                    <path d="M16 3l4 4-4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M20 7H8a4 4 0 0 0-4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M8 21l-4-4 4-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M4 17h12a4 4 0 0 0 4-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span class="share-count">0</span>
                </button>
                </div>
              </div>
            `).join('')}
          </div>
          <div class="feed-footer">
            <button id="continue-btn" class="continue-button" disabled>Continue</button>
          </div>
        </div>
      `;
      display_element.innerHTML = feedHTML;
      
      // Initialize like/share tracking
      var likeStates = new Array(trial.images.length).fill(false);
      var shareStates = new Array(trial.images.length).fill(false);
      var scrollToBottom = false;
      
      // Initialize dwell time tracking
      var postDwellTimes = new Array(trial.images.length).fill(0);
      var postVisibilityStart = new Array(trial.images.length).fill(null);
      var currentlyVisible = new Set();

      // Global functions for like/share buttons
      window.toggleLike = function(index) {
        likeStates[index] = !likeStates[index];
        var btn = document.querySelector(`[data-index="${index}"].like-btn`);
        var count = btn.querySelector('.like-count');
      
        if (likeStates[index]) {
          btn.classList.add('like-active');
          count.textContent = parseInt(count.textContent) + 1;
          btn.setAttribute('aria-pressed', 'true');
        } else {
          btn.classList.remove('like-active');
          count.textContent = Math.max(0, parseInt(count.textContent) - 1);
          btn.setAttribute('aria-pressed', 'false');
        }
      };

      window.toggleShare = function(index) {
        shareStates[index] = !shareStates[index];
        var btn = document.querySelector(`[data-index="${index}"].share-btn`);
        var count = btn.querySelector('.share-count');
      
        if (shareStates[index]) {
          btn.classList.add('retweet-active');              // <-- color via CSS (affects SVG stroke)
          count.textContent = parseInt(count.textContent) + 1;
          btn.setAttribute('aria-pressed', 'true');
        } else {
          btn.classList.remove('retweet-active');
          count.textContent = Math.max(0, parseInt(count.textContent) - 1);
          btn.setAttribute('aria-pressed', 'false');
        }
      };

      // Setup intersection observer for dwell time tracking
      var observerOptions = {
        root: document.getElementById('feed-content'),
        rootMargin: '0px',
        threshold: 0.5 // Post is considered "viewed" when 50% is visible
      };
      
      var postObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          var postIndex = parseInt(entry.target.getAttribute('data-index'));
          var currentTime = performance.now();
          
          if (entry.isIntersecting) {
            // Post became visible
            if (!currentlyVisible.has(postIndex)) {
              currentlyVisible.add(postIndex);
              postVisibilityStart[postIndex] = currentTime;
            }
          } else {
            // Post left view
            if (currentlyVisible.has(postIndex) && postVisibilityStart[postIndex] !== null) {
              currentlyVisible.delete(postIndex);
              var dwellTime = (currentTime - postVisibilityStart[postIndex]) / 1000;
              postDwellTimes[postIndex] += Math.round(dwellTime * 10000) / 10000;
              postVisibilityStart[postIndex] = null;
            }
          }
        });
      }, observerOptions);
      
      // Observe all posts
      document.querySelectorAll('.feed-post').forEach(function(post) {
        postObserver.observe(post);
      });

      // Handle scrolling
      var feedContent = document.getElementById('feed-content');
      var continueBtn = document.getElementById('continue-btn');

      feedContent.addEventListener('scroll', function() {
        if (trial.require_scroll_to_bottom) {
          var scrollTop = feedContent.scrollTop;
          var scrollHeight = feedContent.scrollHeight;
          var clientHeight = feedContent.clientHeight;
          
          if (scrollTop + clientHeight >= scrollHeight - 10) {
            scrollToBottom = true;
            continueBtn.disabled = false;
          }
        }
      });

      // Continue button handler
      continueBtn.addEventListener('click', function() {
        // Calculate duration in seconds
        var endTime = performance.now();
        var durationSeconds = Math.round((endTime - startTime) / 1000 * 10000) / 10000;
        
        // Finalize dwell times for any currently visible posts
        currentlyVisible.forEach(function(postIndex) {
          if (postVisibilityStart[postIndex] !== null) {
            var dwellTime = (endTime - postVisibilityStart[postIndex]) / 1000;
            postDwellTimes[postIndex] += dwellTime;
          }
        });
        
        // Round all dwell times to 4 decimal places
        postDwellTimes = postDwellTimes.map(function(time) {
          return Math.round(time * 10000) / 10000;
        });
        
        // Disconnect the observer to clean up
        postObserver.disconnect();
        
        // Get feed sources from global variable (if available)
        var feedSources = [];
        if (window.currentFeedSourceMap) {
          feedSources = trial.images.map(img => window.currentFeedSourceMap[img] || '');
          // Clean up the global variable
          delete window.currentFeedSourceMap;
        } else {
          // Default to empty strings if no source map available
          feedSources = new Array(trial.images.length).fill('');
        }
        
        // Clean up global functions
        delete window.toggleLike;
        delete window.toggleShare;
        
        // Use global jsPsych instead of this.jsPsych
        jsPsych.finishTrial({
          images_shown: trial.images,
          like_states: likeStates,
          share_states: shareStates,
          liked_images: trial.images.filter((_, i) => likeStates[i]),
          shared_images: trial.images.filter((_, i) => shareStates[i]),
          scroll_to_bottom: scrollToBottom,
          feed_sources: feedSources,
          feed_duration_seconds: durationSeconds,
          post_dwell_times: postDwellTimes
        });
      });

      // Auto-enable continue button if scroll requirement is disabled
      if (!trial.require_scroll_to_bottom) {
        continueBtn.disabled = false;
      }
    }
  }

  return SocialMediaFeedPlugin;

})(jsPsychModule);


// DEBUG: Check if plugin was registered
// console.log("jsPsych object keys:", Object.keys(jsPsych));
// console.log("jsPsychModule object keys:", Object.keys(jsPsychModule));
// console.log("window object has jsPsychSocialMediaFeed:", typeof window.jsPsychSocialMediaFeed !== 'undefined');
// console.log("window object has jsPsychInstructions:", typeof window.jsPsychInstructions !== 'undefined');
// console.log("window object has jsPsychHtmlSliderResponse:", typeof window.jsPsychHtmlSliderResponse !== 'undefined');

// DEBUG: Check what randomization methods are available
// console.log("jsPsych.randomization keys:", Object.keys(jsPsych.randomization));
// console.log("jsPsych.randomization methods:", typeof jsPsych.randomization);