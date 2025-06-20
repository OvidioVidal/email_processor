import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import openai
import json
import os

# Page configuration
st.set_page_config(
    page_title="M&A Intelligence Processor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
    }
    
    .deal-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
    }
    
    .deal-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    
    .deal-value {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
    
    .detail-label {
        font-size: 0.8rem;
        color: #7f8c8d;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .detail-value {
        font-size: 0.95rem;
        color: #2c3e50;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    .alert-badge {
        background: #e74c3c;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    
    .stSelectbox > div > div {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

class AIIntelligenceGenerator:
    def __init__(self, api_key: str):
        """Initialize AI Intelligence Generator with OpenAI API key"""
        if api_key:
            openai.api_key = api_key
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
    
    def generate_intelligence_report(self, deals: List[Dict], filters: Dict) -> str:
        """Generate AI-powered intelligence report from parsed deals"""
        if not self.client:
            return "⚠️ OpenAI API key required for AI intelligence reports"
        
        try:
            # Prepare deal data for AI analysis
            deal_summary = self._prepare_deal_data(deals)
            
            # Create detailed prompt for intelligence report
            prompt = self._create_intelligence_prompt(deal_summary, filters)
            
            # Generate report using OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 for better analysis
                messages=[
                    {"role": "system", "content": """Big 4 M&A Intelligence Report Generator
Core Directive
You are an elite M&A intelligence analyst operating at Big 4 consulting firm standards (McKinsey, BCG, Bain, Deloitte). Your reports must demonstrate the analytical rigor, strategic insight, and actionable intelligence that Fortune 500 executives and private equity partners rely on for billion-dollar decisions.

Quality Standards Framework
TIER 1: Data Integrity & Accuracy
- Zero-tolerance for factual errors: Every data point must be verified and cross-referenced
- Precise sector classification: Use standardized industry taxonomies (GICS, NAICS)
- Accurate geographic attribution: Verify company headquarters vs. transaction locations
- Proper deal categorization: Distinguish between M&A, IPOs, funding rounds, and market movements
- Source attribution: All claims must be traceable to primary sources

TIER 2: Financial Analysis Rigor
- Transaction multiples: Calculate and benchmark EV/Revenue, EV/EBITDA where data permits
- Market context: Position deal values against sector medians and historical trends
- Valuation methodology: Explain premium/discount to market comparables
- Financial performance metrics: Include revenue growth, profitability margins, cash generation
- Deal structure analysis: Assess cash vs. equity, earnouts, retained ownership stakes

TIER 3: Strategic Intelligence
- Strategic rationale identification: Why are deals happening (consolidation, technology, geographic expansion)
- Competitive dynamics: Market share implications, competitive response predictions
- Regulatory drivers: Policy changes, compliance requirements, regulatory arbitrage
- Technology disruption: Digital transformation impacts, AI adoption, automation trends
- ESG considerations: Sustainability drivers, carbon reduction strategies, social impact

TIER 4: Market Intelligence
- Deal velocity trends: Compare current activity to 12-month rolling averages
- Sector rotation patterns: Identify hot vs. cold sectors with supporting metrics
- Geographic capital flows: Cross-border vs. domestic activity patterns
- Sponsor behavior analysis: PE dry powder deployment, hold period trends, exit strategies
- Public market correlation: How public valuations affect private deal activity

Report Architecture Standards
Executive Summary (McKinsey Style)
- Lead with the "So What": Start with the most important strategic insight
- Quantify everything: Use specific metrics, not vague qualifiers
- Three key takeaways maximum: Focus on actionable insights only
- Forward-looking perspective: What this means for market participants

Market Analysis (BCG Framework)
- Total Addressable Market sizing: Quantify market opportunity where relevant
- Growth vectors identification: What's driving expansion/contraction
- Competitive landscape mapping: Market share dynamics, new entrant threats
- Value pool analysis: Where profit pools are shifting between players

Deal Analysis (Bain Approach)
- Strategic logic assessment: Rate deal rationale on strategic merit
- Synergy quantification: Estimate revenue/cost synergies where applicable
- Integration complexity: Assess cultural, operational, technology integration challenges
- Value creation probability: High/Medium/Low probability of achieving stated objectives

Sector Deep Dives (Deloitte Method)
- Industry life cycle positioning: Growth, maturity, decline phase analysis
- Regulatory environment: Current and anticipated policy impacts
- Technology disruption timeline: 12-24 month outlook for sector transformation
- Capital allocation priorities: Where strategic and financial buyers are focusing

Analytical Frameworks to Apply
Strategic Rationale Classification
- Scale Economics: Market consolidation for cost synergies
- Scope Economics: Adjacent market expansion, cross-selling
- Speed to Market: Technology acquisition, geographic acceleration
- Scarce Assets: Talent, IP, regulatory licenses, natural resources
- Defensive: Competitive threats, disruption response

Deal Quality Scoring (1-5 Scale)
- Strategic Logic: Does the deal make strategic sense?
- Financial Attractiveness: Valuation vs. fundamentals assessment
- Execution Probability: Regulatory, financing, integration risks
- Market Timing: Cyclical positioning, valuation environment
- Management Track Record: Acquirer's historical M&A performance

Risk Assessment Matrix
- Regulatory Risk: Antitrust, foreign investment review, sector-specific
- Integration Risk: Cultural fit, systems integration, talent retention
- Market Risk: Economic cycle, sector headwinds, competitive response
- Financial Risk: Leverage levels, cash flow stability, FX exposure

Language & Tone Standards
Precision Requirements
- Use specific numbers: "€847M" not "approximately €850M"
- Quantify trends: "15% increase YoY" not "significant growth"
- Avoid hedge words: Replace "could potentially" with "likely will"
- Be definitive: "This signals..." not "This might suggest..."

Professional Terminology
- Strategic buyers vs. financial sponsors (not "companies" vs. "PE firms")
- Enterprise value vs. equity value (be precise about valuation metrics)
- Multiple expansion vs. multiple compression (for valuation trends)
- Bolt-on acquisition vs. platform investment (for PE strategy)

Executive Communication Style
- Lead with conclusions, support with evidence
- Use pyramid principle: key message → supporting arguments → detailed evidence
- Employ signposting: "Three factors drive this trend:"
- End sections with implications: "This suggests..."

Success Metrics
Your report quality will be measured against:
- Accuracy: Zero factual errors tolerance
- Insight Density: Strategic insights per page ratio
- Actionability: Specific, implementable recommendations
- Differentiation: Unique perspectives not available in public sources
- Executive Readiness: Could this brief a Fortune 500 CEO effectively?

Remember: You are crafting intelligence that will influence billion-dollar investment decisions. Every word must add value, every insight must be defendable, and every recommendation must be actionable. Think like the analysts at KKR, Blackstone, and Apollo who use your reports to deploy capital."""},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3  # Lower temperature for more consistent, professional output
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"⚠️ Error generating AI report: {str(e)}"
    
    def _prepare_deal_data(self, deals: List[Dict]) -> str:
        """Prepare deal data for AI analysis"""
        deal_data = []
        for deal in deals:
            deal_info = {
                'title': deal['title'],
                'sector': deal['sector'], 
                'geography': deal['geography'],
                'value': deal['value'],
                'grade': deal['grade'],
                'size': deal['size'],
                'key_points': deal['details'][:3]  # Top 3 key points
            }
            deal_data.append(deal_info)
        
        return json.dumps(deal_data, indent=2)
    
    def _create_intelligence_prompt(self, deal_data: str, filters: Dict) -> str:
        """Create comprehensive prompt for intelligence report generation"""
        return f"""
        Analyze the following M&A deals and create a comprehensive intelligence report:

        **DEAL DATA:**
        {deal_data}

        **ANALYSIS FILTERS APPLIED:**
        - Sector Focus: {filters.get('sector', 'All Sectors')}
        - Geography: {filters.get('geography', 'All Regions')}  
        - Min Deal Value: {filters.get('value', 'Any Value')}

        **REPORT REQUIREMENTS:**
        Create a professional M&A intelligence report with the following sections:

        1. **EXECUTIVE SUMMARY** (3-4 sentences)
           - Key market trends and deal activity overview
           - Most significant transactions highlighted

        2. **SECTOR ANALYSIS** 
           - Dominant sectors and activity levels
           - Sector-specific trends and drivers
           - Cross-sector consolidation patterns

        3. **GEOGRAPHIC INSIGHTS**
           - Regional deal concentration 
           - Cross-border activity trends
           - Key geographic drivers

        4. **DEAL VALUE ASSESSMENT**
           - Valuation trends and multiples insight
           - Large vs mid-market activity
           - Value creation opportunities

        5. **KEY STRATEGIC THEMES**
           - Consolidation patterns
           - Technology/digital transformation deals
           - Market expansion strategies

        6. **ACTIONABLE RECOMMENDATIONS** 
           - Investment opportunities 
           - Sectors to watch
           - Timing considerations

        **STYLE GUIDELINES:**
        - Professional, concise language
        - Data-driven insights
        - Actionable intelligence focus
        - Use bullet points for clarity
        - Include specific deal references where relevant
        """

class MAProcessor:
    def __init__(self):
        self.sector_keywords = {
            'automotive': ['auto', 'car', 'vehicle', 'motor', 'automotive', 'tesla', 'ford', 'bmw'],
            'technology': ['tech', 'software', 'AI', 'digital', 'data', 'cyber', 'SaaS', 'IT', 'cloud', 'app'],
            'financial': ['bank', 'finance', 'capital', 'investment', 'insurance', 'fund', 'fintech'],
            'industrial': ['construction', 'industrial', 'manufacturing', 'engineering', 'chemical', 'steel'],
            'energy': ['energy', 'oil', 'gas', 'renewable', 'power', 'solar', 'wind', 'nuclear'],
            'healthcare': ['health', 'medical', 'pharma', 'biotech', 'hospital', 'drug', 'medicine'],
            'consumer': ['retail', 'consumer', 'food', 'beauty', 'fashion', 'beverage', 'brand'],
            'real_estate': ['real estate', 'property', 'reit', 'building', 'development'],
            'agriculture': ['agriculture', 'farming', 'food', 'crop', 'livestock']
        }
        
        self.geo_keywords = {
            'uk': ['uk', 'britain', 'london', 'england', 'scotland', 'wales', 'british'],
            'germany': ['german', 'germany', 'berlin', 'munich', 'deutsche'],
            'france': ['france', 'french', 'paris'],
            'europe': ['europe', 'european', 'eu'],
            'usa': ['us', 'usa', 'america', 'american', 'new york', 'california'],
            'china': ['china', 'chinese', 'beijing', 'shanghai'],
            'asia': ['asia', 'asian', 'japan', 'singapore', 'hong kong']
        }

    def extract_sector(self, title: str) -> str:
        """Extract sector from deal title"""
        lower_title = title.lower()
        for sector, keywords in self.sector_keywords.items():
            if any(keyword in lower_title for keyword in keywords):
                return sector.replace('_', ' ').title()
        return 'Other'

    def extract_geography(self, title: str) -> str:
        """Extract geography from deal title"""
        lower_title = title.lower()
        for geo, keywords in self.geo_keywords.items():
            if any(keyword in lower_title for keyword in keywords):
                return geo.upper()
        return 'Global'

    def extract_value(self, text: str) -> str:
        """Extract monetary value from text"""
        # Look for currency patterns
        value_patterns = [
            r'(EUR|USD|GBP)\s*([\d,\.]+)\s*([bmk]?)',
            r'([\d,\.]+)\s*(EUR|USD|GBP|million|billion)',
            r'\$\s*([\d,\.]+)\s*([bmk]?)',
            r'£\s*([\d,\.]+)\s*([bmk]?)',
            r'€\s*([\d,\.]+)\s*([bmk]?)'
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return 'TBD'

    def parse_email_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse M&A email content into structured deals"""
        deals = []
        lines = content.split('\n')
        current_deal = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check for deal header (numbered item)
            deal_match = re.match(r'^(\d+)\.\s*(.+)', line)
            if deal_match:
                # Save previous deal
                if current_deal:
                    deals.append(current_deal)
                
                # Start new deal
                deal_id = deal_match.group(1)
                title = deal_match.group(2)
                
                current_deal = {
                    'id': deal_id,
                    'title': title,
                    'sector': self.extract_sector(title),
                    'geography': self.extract_geography(title),
                    'details': [],
                    'summary': '',
                    'value': self.extract_value(title),
                    'grade': '',
                    'size': '',
                    'original_text': ''
                }
                
                # Collect next few lines for context
                context_lines = []
                for j in range(i + 1, min(i + 10, len(lines))):
                    context_line = lines[j].strip()
                    if context_line and not context_line.startswith(str(int(deal_id) + 1) + '.'):
                        context_lines.append(context_line)
                    else:
                        break
                
                current_deal['original_text'] = '\n'.join(context_lines)
                
                # Extract additional info from context
                for context_line in context_lines:
                    if context_line.startswith('*'):
                        current_deal['details'].append(context_line[1:].strip())
                    elif 'Size:' in context_line:
                        current_deal['size'] = context_line.split('Size:')[1].strip()
                    elif 'Grade:' in context_line:
                        current_deal['grade'] = context_line.split('Grade:')[1].strip()
                    elif any(curr in context_line for curr in ['EUR', 'USD', 'GBP', 'billion', 'million']):
                        if not current_deal['value'] or current_deal['value'] == 'TBD':
                            current_deal['value'] = self.extract_value(context_line)
                
                # Create summary from first meaningful line
                meaningful_lines = [cl for cl in context_lines if len(cl) > 30 and not cl.startswith('*')]
                if meaningful_lines:
                    current_deal['summary'] = meaningful_lines[0][:200]
        
        # Don't forget the last deal
        if current_deal:
            deals.append(current_deal)
        
        return deals

    def apply_filters(self, deals: List[Dict], sector_filter: str, value_filter: str, geo_filter: str) -> List[Dict]:
        """Apply filters to deals"""
        filtered_deals = []
        
        for deal in deals:
            # Sector filter
            if sector_filter != 'All Sectors' and deal['sector'] != sector_filter:
                continue
            
            # Geography filter
            if geo_filter != 'All Regions' and deal['geography'] != geo_filter.upper():
                continue
            
            # Value filter (simplified)
            if value_filter != 'Any Value':
                min_value = int(value_filter.split('£')[1].split('M')[0])
                deal_has_large_value = any(indicator in deal['value'] + deal['size'] 
                                        for indicator in ['billion', 'bn', '300m', '> 60m'])
                if min_value > 60 and not deal_has_large_value:
                    continue
            
            filtered_deals.append(deal)
        
        return filtered_deals

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 M&A Intelligence Processor</h1>
        <p>Transform raw M&A data into actionable intelligence for strategic decision-making</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize processor
    if 'processor' not in st.session_state:
        st.session_state.processor = MAProcessor()
    
    # Sidebar controls
    st.sidebar.header("🔧 Analysis Controls")
    
    # AI Configuration Section
    st.sidebar.markdown("---")
    st.sidebar.header("🤖 AI Intelligence")
    
    # OpenAI API Key input - check environment variable first
    env_api_key = os.getenv("OPENAI_API_KEY")
    if env_api_key:
        openai_api_key = env_api_key
        st.sidebar.success("✅ OpenAI API key loaded from environment")
    else:
        openai_api_key = st.sidebar.text_input(
            "OpenAI API Key", 
            type="password",
            help="Enter your OpenAI API key to enable AI-powered intelligence reports"
        )
    
    # Initialize AI generator
    if 'ai_generator' not in st.session_state or openai_api_key:
        st.session_state.ai_generator = AIIntelligenceGenerator(openai_api_key)
    
    st.sidebar.markdown("---")
    
    sector_filter = st.sidebar.selectbox(
        "Sector Focus",
        ['All Sectors', 'Automotive', 'Technology', 'Financial', 'Industrial', 
         'Energy', 'Healthcare', 'Consumer', 'Real Estate', 'Agriculture']
    )
    
    value_filter = st.sidebar.selectbox(
        "Minimum Deal Value",
        ['Any Value', '£30M+', '£60M+', '£300M+', '£1B+']
    )
    
    geo_filter = st.sidebar.selectbox(
        "Geography",
        ['All Regions', 'UK', 'Germany', 'France', 'Europe', 'USA', 'China', 'Asia']
    )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📧 Raw M&A Email Input")
        
        # Sample data
        sample_data = """Agriculture
1. Stora Enso divests forest assets for EUR 900m

Automotive
2. Magirus could expand outside of Germany through acquisitions - report (translated)
* Subsidiaries planned in Switzerland, Spain, Poland, and UAE
* Aims to set up production sites in Romania, Croatia through acquisitions
* Aims to double sales to EUR 750m by 2030

3. Changan Auto-owned DEEPAL in talks for JV factory in Europe
* Ford Motor and Mazda Motor in talks
* Germany, Hungary, Italy, UK as potential venues

Computer software
8. Adarga seeks GBP 6m-GBP 8m in new funding – report
* Previous USD 20m investment round led by BOKA Group

9. Enerim sponsor KLAR Partners preps sale via Macquarie
* Mandate awarded last autumn, launch timing unclear
* Sellside awaits better visibility on 2025 financials

10. CoreWeave's USD 2bn of post-listing gains leads global IPO outperformance - Analysis
* Post results surge huge boon for CoreWeave IPO investors
* AI hyperscaler represents a quarter of all new listing gains globally"""
        
        email_input = st.text_area(
            "Paste M&A email content here:",
            value=sample_data,
            height=400,
            help="Paste your raw M&A email content. The system will automatically parse and structure the data."
        )
        
        process_button = st.button("🚀 Process & Analyze", type="primary")
    
    with col2:
        st.subheader("📊 Intelligence Report")
        
        if process_button and email_input:
            with st.spinner("Processing M&A intelligence..."):
                # Parse deals
                deals = st.session_state.processor.parse_email_content(email_input)
                
                # Apply filters
                filtered_deals = st.session_state.processor.apply_filters(
                    deals, sector_filter, value_filter, geo_filter
                )
                
                # Store in session state
                st.session_state.deals = deals
                st.session_state.filtered_deals = filtered_deals
        
        # Display results if available
        if 'filtered_deals' in st.session_state:
            deals = st.session_state.deals
            filtered_deals = st.session_state.filtered_deals
            
            # Metrics row
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric("Total Deals", len(deals))
            
            with col_b:
                st.metric("Filtered Results", len(filtered_deals))
            
            with col_c:
                avg_value = 150 if filtered_deals else 0  # Simplified calculation
                st.metric("Avg Deal Value", f"${avg_value}M")
            
            with col_d:
                if filtered_deals:
                    sectors = [deal['sector'] for deal in filtered_deals]
                    top_sector = max(set(sectors), key=sectors.count) if sectors else 'N/A'
                else:
                    top_sector = 'N/A'
                st.metric("Top Sector", top_sector)
            
            st.markdown("---")
            
            # Display filtered deals
            if filtered_deals:
                for deal in filtered_deals:
                    with st.container():
                        st.markdown(f"""
                        <div class="deal-card">
                            <div class="deal-header">{deal['title']}</div>
                            <div class="deal-value">{deal['value'] if deal['value'] != 'TBD' else deal['size'] or 'Value TBD'}</div>
                            
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                                <div>
                                    <div class="detail-label">Sector</div>
                                    <div class="detail-value">{deal['sector']}</div>
                                </div>
                                <div>
                                    <div class="detail-label">Geography</div>
                                    <div class="detail-value">{deal['geography']}</div>
                                </div>
                                <div>
                                    <div class="detail-label">Grade</div>
                                    <div class="detail-value">{deal['grade'] or 'Pending'} {'<span class="alert-badge">HOT</span>' if deal['grade'] == 'Strong evidence' else ''}</div>
                                </div>
                                <div>
                                    <div class="detail-label">Deal ID</div>
                                    <div class="detail-value">#{deal['id']}</div>
                                </div>
                            </div>
                            
                            {f'<div class="detail-label">Key Points</div><div class="detail-value">{"<br>".join([f"• {detail}" for detail in deal["details"][:3]])}</div>' if deal['details'] else ''}
                            
                            {f'<div style="background: #ecf0f1; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; line-height: 1.5; color: #34495e;">{deal["summary"][:200]}{"..." if len(deal["summary"]) > 200 else ""}</div>' if deal['summary'] else ''}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Expandable details
                        with st.expander("View Raw Details"):
                            st.text(deal['original_text'])
            else:
                st.info("No deals match your current filters. Try adjusting the filter criteria.")
        else:
            st.info("Ready to process M&A intelligence. Paste email content and click 'Process & Analyze'")
    
    # AI Intelligence Report Section
    if 'filtered_deals' in st.session_state and st.session_state.filtered_deals:
        st.markdown("---")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("🤖 AI Intelligence Report")
        with col2:
            generate_ai_report = st.button("🚀 Generate AI Report", type="primary")
        
        if generate_ai_report:
            if not openai_api_key:
                st.error("⚠️ Please enter your OpenAI API key in the sidebar to generate AI reports")
            else:
                with st.spinner("🤖 AI is analyzing deals and generating intelligence report..."):
                    # Prepare filter context for AI
                    filter_context = {
                        'sector': sector_filter,
                        'geography': geo_filter, 
                        'value': value_filter
                    }
                    
                    # Generate AI report
                    ai_report = st.session_state.ai_generator.generate_intelligence_report(
                        st.session_state.filtered_deals,
                        filter_context
                    )
                    
                    # Store AI report in session state
                    st.session_state.ai_report = ai_report
        
        # Display AI report if available
        if 'ai_report' in st.session_state:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                        padding: 2rem; border-radius: 15px; 
                        border-left: 5px solid #28a745; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            st.markdown("### 📊 AI-Generated Intelligence Report")
            st.markdown(st.session_state.ai_report)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Download AI report
            st.download_button(
                label="📥 Download AI Report",
                data=st.session_state.ai_report,
                file_name=f"ai_intelligence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    # Analytics section
    if 'filtered_deals' in st.session_state and st.session_state.filtered_deals:
        st.markdown("---")
        st.subheader("📈 Deal Analytics")
        
        deals = st.session_state.filtered_deals
        
        # Create analytics
        col1, col2 = st.columns(2)
        
        with col1:
            # Sector distribution
            sectors = [deal['sector'] for deal in deals]
            sector_counts = pd.Series(sectors).value_counts()
            
            fig_sector = px.pie(
                values=sector_counts.values,
                names=sector_counts.index,
                title="Deal Distribution by Sector"
            )
            fig_sector.update_layout(height=300)
            st.plotly_chart(fig_sector, use_container_width=True)
        
        with col2:
            # Geography distribution
            geos = [deal['geography'] for deal in deals]
            geo_counts = pd.Series(geos).value_counts()
            
            fig_geo = px.bar(
                x=geo_counts.index,
                y=geo_counts.values,
                title="Deal Distribution by Geography"
            )
            fig_geo.update_layout(height=300)
            st.plotly_chart(fig_geo, use_container_width=True)
        
        # Export functionality
        st.markdown("---")
        st.subheader("📤 Export Data")
        
        # Convert to DataFrame for export
        df = pd.DataFrame(deals)
        
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"ma_deals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Create a summary report
            summary_report = f"""
            # M&A Intelligence Report
            
            Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            ## Summary Statistics
            - Total Deals Processed: {len(st.session_state.deals)}
            - Deals After Filtering: {len(deals)}
            - Top Sector: {max(set(sectors), key=sectors.count) if sectors else 'N/A'}
            - Geographic Spread: {len(set(geos))} regions
            
            ## Key Deals
            {chr(10).join([f"- {deal['title']} ({deal['value'] or deal['size'] or 'Value TBD'})" for deal in deals[:5]])}
            """
            
            st.download_button(
                label="Download Summary Report",
                data=summary_report,
                file_name=f"ma_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()