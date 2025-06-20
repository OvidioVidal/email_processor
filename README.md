# M&A Intelligence Processor

A sophisticated Streamlit application for processing and analyzing M&A email content, transforming raw data into actionable intelligence with AI-powered insights.

## Features

- 🎯 Automated M&A deal parsing from email content
- 📊 Interactive filtering by sector, geography, and deal value  
- 📈 Visual analytics with charts and metrics
- 🤖 **AI-powered intelligence reports** using OpenAI GPT-4
- 📤 Export functionality (CSV and summary reports)
- 🎨 Modern, professional UI design

## AI Intelligence Reports

The app now includes AI-powered intelligence generation that provides:
- **Executive summaries** of deal activity
- **Sector analysis** with trends and drivers  
- **Geographic insights** and cross-border patterns
- **Deal value assessments** and market dynamics
- **Strategic themes** and consolidation patterns
- **Actionable recommendations** for investment decisions

## Quick Start

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Get your OpenAI API key:
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Generate an API key from your dashboard
   - Add billing information (GPT-4 access required)
4. Run the app:
   ```bash
   streamlit run email.py
   ```
5. Enter your OpenAI API key in the sidebar to enable AI reports

### Deploy on Streamlit Community Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Select `email.py` as your main application file
5. **For AI functionality**: Add your OpenAI API key as a secret:
   - In Streamlit Cloud, go to your app settings
   - Add `OPENAI_API_KEY` as a secret with your API key value
6. Deploy!

### Environment Variables (Production)

For production deployment, you can set the OpenAI API key as an environment variable:
```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Usage

1. Paste your M&A email content into the input area
2. Use the sidebar filters to focus on specific sectors, geographies, or deal values
3. Click "Process & Analyze" to generate intelligence reports
4. View structured deal information with key metrics
5. Export results as CSV or summary reports

## App Structure

- `email.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `README.md` - Documentation

## Dependencies

- Streamlit: Web app framework
- Pandas: Data manipulation
- Plotly: Interactive visualizations 