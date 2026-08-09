# How to do manual testing

## Run smoke tests

## Do manual testing

- Go to the browser (and add a manual PID). Example is `http://jspsych-mirror-view-4.s3-website.us-east-2.amazonaws.com/?PROLIFIC_PID=manual-test-1`
- Follow the logic of the survey.
- After political affiliation, complete the **Political Expression** attention check (select all that apply). Participants always continue even if they fail; filter later on `attention_check_passed` in the saved CSV (`1` = pass, `0` = fail).
- Review S3 + DynamoDB for records.
