# MirrorView Task

A jsPsych-based experimental task framework with AWS deployment capabilities. This project is based on the AWS-scroll branch of the rateTweets repository and provides a clean starting point for psychological experiments.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Local Development Server
```bash
npm run dev
# or
npm start
```

### 3. Access the Experiment
- **Local Development**: http://localhost:3000/index-local.html?PROLIFIC_PID=TEST123
- **Production Mode**: http://localhost:3000/?PROLIFIC_PID=TEST123

## 📁 Project Structure

```
├── public/                   # Web assets
│   ├── index.html           # Main experiment page
│   ├── index-local.html     # Local development page
│   ├── main.js              # Main experiment script
│   ├── main-local.js        # Local development script
│   ├── config.js            # Configuration system
│   ├── jspsych/             # jsPsych library
│   ├── plugins/             # jsPsych plugins
│   ├── lib/                 # Additional libraries
│   ├── img/                 # Image assets
│   │   └── stimuli/         # Experimental stimuli (add your images here)
│   └── *.js                 # Survey and utility scripts
├── lambda-*.mjs             # AWS Lambda functions
├── server-local.js          # Local development server
├── local_data/              # Local data storage
├── analysis/                # Data analysis scripts
├── test_data/               # Test data
└── *.py                     # Utility scripts
```

## 🔧 Features

### Dual-Mode Configuration
- **Local Development**: Full debugging with local server
- **AWS Production**: Scalable cloud deployment
- **Easy Switching**: Toggle between modes without code changes

### AWS Integration
- **Lambda Functions**: Post assignment and data saving
- **S3 Storage**: Static hosting and data storage
- **API Gateway**: RESTful endpoints
- **Complete Deployment Guide**: Step-by-step AWS setup

### Development Tools
- **Local Server**: Mimics AWS endpoints for debugging
- **Debug Endpoints**: Monitor participant assignments
- **Data Validation**: Automatic data saving and validation
- **Console Logging**: Comprehensive debugging information

## 🛠️ Customization

### Adding Your Experiment

1. **Update Main Script**: Modify `public/main.js` and `public/main-local.js` with your experimental logic
2. **Add Stimuli**: Place your images in `public/img/stimuli/`
3. **Customize Surveys**: Edit `public/pre_surveys.js` and `public/post_surveys.js`
4. **Update Post Assignment Logic**: Modify `lambda-get-post-assignments.mjs` if needed

### Configuration

The `public/config.js` file controls the experiment configuration:
- API endpoints (local vs AWS)
- Debug settings
- Mode switching

## 📊 Data Collection

### Local Development
- Data saved to `local_data/` folder
- Timestamped CSV files
- Debug endpoint at `/debug/assignments`

### AWS Production
- Data saved to S3 bucket
- Post assignment via Lambda
- Scalable for large studies

## 🚀 Deployment

### Local Testing
1. Run `npm start`
2. Visit http://localhost:3000/index-local.html
3. Test with different participant IDs

### AWS Deployment
1. Follow the complete guide in `AWS_DEPLOYMENT_GUIDE.md`
2. Set up S3, Lambda, and API Gateway
3. Upload files and configure endpoints
4. Test the full production flow

## 📖 Documentation

- **`README-LOCAL-DEV.md`**: Detailed local development setup
- **`AWS_DEPLOYMENT_GUIDE.md`**: Complete AWS deployment instructions
- **jsPsych Documentation**: https://www.jspsych.org/

## 🔄 Migration from rateTweets

This project maintains the same structure and functionality as the original rateTweets AWS-scroll branch, with the following changes:
- Cleaned data files and participant-specific content
- Updated project name and documentation
- Generic stimuli directory structure
- Ready for customization with your experimental content

## 🆘 Troubleshooting

### Common Issues
- **Port in use**: Kill process with `lsof -ti:3000 | xargs kill -9`
- **Missing dependencies**: Run `npm install`
- **Configuration errors**: Check `config.js` accessibility
- **Data not saving**: Verify `local_data/` folder permissions

### Getting Help
- Check the detailed documentation files
- Review console logs for error messages
- Test with the debug endpoints
- Verify AWS permissions and configurations

## 📝 License

ISC License - Feel free to use this framework for your research projects.

---

**Ready to start your experiment?** Follow the Quick Start guide above and customize the experimental logic for your specific research needs!

