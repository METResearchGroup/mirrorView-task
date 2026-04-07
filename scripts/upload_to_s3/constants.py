"""Shared constants for S3 upload tooling."""

from pathlib import Path

AWS_REGION = "us-east-2"
TARGET_BUCKET = "jspsych-mirror-view-3"
API_NAME = "jspsych-scroll-api"
API_STAGE = "prod"
SOURCE_PUBLIC_DIR = Path("public")
STAGING_ROOT = Path("s3_upload")
PROTECTED_PREFIXES = ("data/",)
CRITICAL_S3_KEYS = (
    "index.html",
    "config.js",
    "main.js",
    "consent.js",
    "pre_surveys.js",
    "post_surveys.js",
    "meriel.css",
    "jspsych/jspsych.js",
    "jspsych/jspsych.css",
    "plugins/plugin-instructions.js",
    "plugins/plugin-survey-html-form.js",
    "plugins/plugin-html-button-response.js",
    "plugins/plugin-call-function.js",
    "plugins/plugin-mirror-preference.js",
    "plugins/plugin-mirror-practice.js",
    "plugins/plugin-moderation-trial.js",
    "img/all_mirrors_claude.csv",
)

SKIP_STAGING_NAMES = {".DS_Store", ".gitkeep"}
