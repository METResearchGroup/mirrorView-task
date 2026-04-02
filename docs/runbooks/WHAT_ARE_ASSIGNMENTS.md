# Assignments

In production, we "assign" users to condition + posts.

## What is an "assignment"?

When we have a user, we want to assign them a condition and posts to show. The combination of "condition + posts to show to a user" = "assignment". When a user logs in and we figure out their political lean (left/right), we can then give them their assigned condition + posts that they'll be shown.

## Pending vs. committed assignments

- Committed assignments (post_assignments.json): the durable record of what each participant ended up getting.
- Pending assignments (pending_assignments.json): a temporary reservation so repeated calls are idempotent, and so dropouts don’t affect “seen/unseen” balancing until data is actually saved.

Another way to see it is

- Pending assignment: a reservation written immediately when a participant requests posts, so repeated requests are idempotent and concurrent sign-ups can be pending-aware. Stored in pending_assignments.json.
- Committed assignment: the final record written only after the participant successfully saves data. Stored in post_assignments.json (plus per-post counters).

## How does this run in the app?

When a user logs into the study, how are their conditions actually assigned to them?

### 1. Client loads the full post catalog (stimulus data)

`public/main.js` fetches `img/all_mirrors_claude.csv` and parses it into `allMirrorData`. This is stored locally.

### 2. Client requests an assignment for a given user

#### Client-side

Once the user fills out the onboarding and we then know `party_group`, `public/main.js` then calls the assignment endpiont from `public/config.js`:

```javascript
aws: {
    POST_ASSIGNMENTS_URL: 'https://ngxqzz3qhd.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments',
    SAVE_DATA_URL: 'https://ngxqzz3qhd.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data',
    ...
},
```

```javascript
const response = await fetch(postAssignmentUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prolific_id: currentProlificID,
    party_group: partyGroup,
    condition: requestedConditionOverride || assignedCondition,
    is_test: isTestParticipant
  })
});
```

#### Server-side

`lambda-get-post-assigments.mjs` loads comitted and pending state from S3, then either reuses existing state or creates a new assignment.

Logic:

- Load committed assignments (`post_assignments.json`) and initialize if missing.
- Load pending assignments (`pending_assignments.json`) in the same way.
- Reuse previous assignments if present.

```javascript
let assignments;

...

```

TODO: still unclear to me what's exactly the difference between `post_assignments.json` and `pending_assignments.json`.

NOTE: can still refactor the lambdas to have single functions even if they're all in the same file.

When would someone have a pending assignment but not a committed one?
This is the state you said you don’t understand, and it’s the key one.

A participant has a pending assignment but not a committed assignment in the time window after:

the assignment endpoint has already given them posts
but before the save endpoint has successfully stored their study results
Examples:

The participant loads the study and gets their 20 posts, then spends 15 minutes doing the task.

During those 15 minutes, they are in pending_assignments.json
They are not yet in post_assignments.json
The participant gets posts, then refreshes the page before finishing.

On refresh, the client asks for posts again
The Lambda sees them in pending_assignments.json
It returns the same reserved posts instead of generating a different set
The participant gets posts, but closes the browser before submitting.

Their assignment stays pending
It never becomes committed unless a successful save happens later
The participant finishes the study, but the save request fails due to network/server error.

Their assignment was generated and reserved
But since save did not succeed, it never gets copied into post_assignments.json
So the phrase “the user has not yet successfully submitted/saved study data” means:

the frontend has not yet made the final save call successfully, or
it did try, but the save Lambda did not complete successfully.
It does not mean “the user definitely quit.” It just means: “we have given them posts, but we do not yet have a successful final data-save event.”

---- My writeup: ----

We make a distinction between the "permanent" and the "pending" assignments. We first assign users to a "pending" assignment, a temporary assignment, and then once they are confirmed to complete the study, we move them to a "permanent" assignment, as this is the "durable" record.

I think the naming convention that I'll go with is something like "reserved" or "issued" vs. "persisted" or "final" or "recorded" or "finalized"...

OK, I think I'll go with "issued" vs. "finalized". We want to distinguish between the content we issue to them vs. the content that is "finalized".

The assignments then are "issued", and then given to the users, and then once they've completed the study, it's "finalized".

---
