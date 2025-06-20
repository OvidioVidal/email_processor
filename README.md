# M&A Intelligence Processor

A sophisticated Streamlit application for processing and analyzing M&A email content, transforming raw data into actionable intelligence.

## Features

- 🎯 Automated M&A deal parsing from email content
- 📊 Interactive filtering by sector, geography, and deal value  
- 📈 Visual analytics with charts and metrics
- 📤 Export functionality (CSV and summary reports)
- 🎨 Modern, professional UI design

## Quick Start

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run email.py
   ```

### Deploy on Streamlit Community Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Select `email.py` as your main application file
5. Deploy!

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