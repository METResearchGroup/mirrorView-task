# MirrorView Task

A jsPsych-based experimental task framework with AWS deployment capabilities. This project is based on the AWS-scroll branch of the rateTweets repository and provides a clean starting point for psychological experiments.

The deployable web stack (static site, Lambdas, Terraform, S3 upload tooling) lives under `webapp/`. Python analysis / ML tooling stays at the repo root.

## Quick Start

Local serve uses a static HTTP server (do **not** rely on `npm run dev` / `npm start` — those scripts point at missing `server-local.js` / `index-local.html`).

### 1. Install web dependencies (optional; not required for static serve)
```bash
cd webapp && npm install
```

### 2. Stage the local stimulus catalog
```bash
mkdir -p webapp/public/img && cp jobs/mirrorview_scaled_2026_06_18/flips.csv webapp/public/img/flips_scaled_2026_06_18.csv
```

### 3. Serve the experiment
```bash
python3 -m http.server 3000 --directory webapp/public
```

### 4. Access the experiment
- http://localhost:3000/index.html?PROLIFIC_PID=TEST123

See `AGENTS.md` for agent/bootstrap notes (live API Gateway URLs in `webapp/public/config.js`, etc.).

## Project Structure

```
├── webapp/                      # Deployable MirrorView web unit
│   ├── public/                  # Static site (S3 website assets)
│   │   ├── index.html           # Main experiment page
│   │   ├── main.js              # Main experiment script
│   │   ├── config.js            # API URLs + study identity
│   │   ├── jspsych/             # jsPsych library
│   │   ├── plugins/             # jsPsych plugins
│   │   ├── lib/                 # Additional libraries
│   │   ├── img/                 # Image / catalog assets (often gitignored)
│   │   └── *.js                 # Survey and utility scripts
│   ├── lambdas/                 # AWS Lambda sources
│   │   ├── lambda-get-post-assignments.mjs
│   │   └── lambda-save-jspsych-data.mjs
│   ├── infra/                   # Terraform (S3, Lambda, API Gateway)
│   ├── scripts/upload_to_s3/    # Staging + upload toolchain
│   ├── testing/smoke_tests/     # Smoke stubs (hit live prod)
│   ├── package.json
│   └── package-lock.json
├── jobs/                        # Job configs + stimulus source-of-record
├── experiments/                 # Offline experiments / analysis
├── scripts/                     # Root Python analysis scripts
├── lib/                         # Shared Python packages
├── local_data/                  # Local data storage
└── docs/runbooks/               # Operator runbooks
```

## Features

### Dual-Mode Configuration
- **Local Development**: Static serve of `webapp/public/` against live API endpoints
- **AWS Production**: Scalable cloud deployment (S3 + API Gateway + Lambdas)

### AWS Integration
- **Lambda Functions**: Post assignment and data saving
- **S3 Storage**: Static hosting and data storage
- **API Gateway**: RESTful endpoints
- **Complete Deployment Guide**: Step-by-step AWS setup

## Customization

### Adding Your Experiment

1. **Update Main Script**: Modify `webapp/public/main.js` with your experimental logic
2. **Add Stimuli**: Place your images / catalog under `webapp/public/img/`
3. **Customize Surveys**: Edit `webapp/public/pre_surveys.js` and `webapp/public/post_surveys.js`
4. **Update Post Assignment Logic**: Modify `webapp/lambdas/lambda-get-post-assignments.mjs` if needed

### Configuration

The `webapp/public/config.js` file controls the experiment configuration:
- API endpoints
- Study identity (`STUDY_ID`, `STUDY_ITERATION_ID`)
- Prolific completion settings

## Data Collection

### Local Development
- Browser hits live assignment/save APIs from `webapp/public/config.js`
- Stimulus catalog is loaded from the local static tree

### AWS Production
- Data saved to S3 bucket
- Post assignment via Lambda
- Scalable for large studies

## Deployment

### Local Testing
1. Copy the stimulus CSV (see Quick Start)
2. Serve `webapp/public/` with `python3 -m http.server`
3. Visit http://localhost:3000/index.html?PROLIFIC_PID=TEST123

### AWS Deployment
1. Follow the complete guide in `docs/runbooks/AWS_DEPLOYMENT_GUIDE.md`
2. Terraform from `webapp/infra/`
3. Upload with `bash webapp/scripts/upload_to_s3/run_upload.sh`
4. Test the full production flow

## Documentation

- **`AGENTS.md`**: Local serve + agent bootstrap
- **`docs/runbooks/AWS_DEPLOYMENT_GUIDE.md`**: AWS deployment instructions
- **`docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`**: New study iteration checklist
- **`docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md`**: Stimulus catalog replacement
- **jsPsych Documentation**: https://www.jspsych.org/

## Migration from rateTweets

This project maintains the same structure and functionality as the original rateTweets AWS-scroll branch, with the following changes:
- Cleaned data files and participant-specific content
- Updated project name and documentation
- Generic stimuli directory structure
- Ready for customization with your experimental content
- Web deployable unit collocated under `webapp/`

## Troubleshooting

### Common Issues
- **Port in use**: Kill process with `lsof -ti:3000 | xargs kill -9`
- **Assignment Error / unknown post IDs**: Missing local catalog — copy `jobs/.../flips.csv` into `webapp/public/img/flips_scaled_2026_06_18.csv`
- **Configuration errors**: Check `webapp/public/config.js` accessibility and API URLs

### Getting Help
- Check the detailed documentation files
- Review console logs for error messages
- Verify AWS permissions and configurations

## License

ISC License - Feel free to use this framework for your research projects.
