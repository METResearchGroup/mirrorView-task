# Local Development Setup for AWS-scroll Branch

This setup allows you to debug the full experiment flow locally, including participant ID assignment and data saving, while keeping the AWS functionality intact for production.

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

## 🔧 How It Works

### Configuration System
- **`config.js`**: Central configuration file that switches between local and AWS endpoints
- **Default Mode**: Set to `local` for development
- **Easy Switching**: Toggle between local and AWS modes without code changes

### Local Server (`server-local.js`)
- **Mimics AWS endpoints** for participant ID assignment and data saving
- **Political party-based assignment** (Democrats: 1-175, Republicans: 176-350)
- **Data storage** in local `local_data/` folder with timestamped CSV files
- **Debug endpoint** at `/debug/assignments` to monitor assignments

### Files Structure
```
├── config.js                 # Configuration system
├── server-local.js          # Local development server
├── public/
│   ├── index-local.html     # Local development HTML
│   ├── main-local.js        # Local development main script
│   └── main.js              # Original AWS production script
└── local_data/              # Local data storage (created automatically)
```

## 🎯 Development Workflow

### 1. **Local Development Mode** (Default)
- Uses local server endpoints
- Data saved to local `local_data/` folder
- Full participant ID assignment functionality
- Perfect for debugging the complete experiment flow

### 2. **AWS Production Mode**
- Uses actual AWS endpoints
- Data sent to AWS Lambda
- Real participant ID assignment
- Use this to test AWS integration

### 3. **Mode Switching**
- **In-browser**: Use the mode switcher in the top-right corner
- **Programmatic**: `window.config.setMode('aws')` or `window.config.setMode('local')`

## 🐛 Debugging Features

### Debug Endpoint
- **URL**: http://localhost:3000/debug/assignments
- **Shows**: Current participant assignments, political party counts, available IDs

### Console Logging
- Participant ID assignment requests and responses
- Data saving attempts and results
- Current endpoint being used

### Visual Indicators
- **Red badge**: Local development mode
- **Blue badge**: AWS production mode
- **Mode switcher**: Easy toggle between modes

## 📊 Testing Different Scenarios

### Test Participant ID Assignment
```bash
# Test Democrat assignment
curl "http://localhost:3000/get-participant-id?prolific_id=TEST1&party=democrat"

# Test Republican assignment  
curl "http://localhost:3000/get-participant-id?prolific_id=TEST2&party=republican"
```

### Test Data Saving
```bash
curl -X POST http://localhost:3000/save-jspsych-data \
  -H "Content-Type: application/json" \
  -d '{"csv":"test,data,here"}'
```

## 🔄 Switching to Production

When you're ready to deploy to AWS:

1. **Keep all your code changes** in the AWS-scroll branch
2. **The configuration system** automatically handles endpoint switching
3. **No code rewrites needed** - just change the mode to 'aws'
4. **Deploy the same codebase** to AWS

## 🚨 Important Notes

- **Local server runs on port 3000** - make sure it's available
- **Data is stored locally** in the `local_data/` folder during development
- **Political party assignments** are tracked and balanced (175 per party)
- **All AWS functionality** is preserved and can be tested locally
- **Debug mode** is automatically enabled in local development

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Missing Dependencies
```bash
npm install
```

### Configuration Not Loading
- Check that `config.js` is accessible from the HTML file
- Verify the script tag path in `index-local.html`

### Data Not Saving
- Check the `local_data/` folder exists and is writable
- Look at server console for error messages
- Verify the endpoint URL in the configuration

## 🎉 Benefits

✅ **Full local debugging** of participant ID assignment  
✅ **Complete data saving** functionality locally  
✅ **Easy switching** between local and AWS modes  
✅ **No code duplication** - same codebase for both modes  
✅ **Political party balancing** maintained locally  
✅ **Debug tools** for monitoring assignments and data  
✅ **Production-ready** - deploy the same code to AWS  

This setup gives you the best of both worlds: full local development capabilities while maintaining all the AWS production functionality!
