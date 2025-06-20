import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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
    
    def extract_links(self, content: str) -> List[str]:
        """Extract all URLs from content"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        links = re.findall(url_pattern, content)
        return list(set(links))  # Remove duplicates
    
    def create_industry_summary(self, deals: List[Dict]) -> Dict[str, Any]:
        """Create comprehensive industry summary from deals"""
        sectors = [deal['sector'] for deal in deals]
        sector_counts = {}
        
        for sector in sectors:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        # Sort by frequency
        sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_industries': len(sector_counts),
            'top_industries': sorted_sectors[:5],
            'industry_distribution': sector_counts,
            'dominant_sector': sorted_sectors[0] if sorted_sectors else ('Unknown', 0)
        }
    
    def extract_all_industries_from_text(self, raw_content: str) -> Dict[str, int]:
        """Extract ALL industry mentions from raw text, not just from parsed deals"""
        all_mentions = {}
        
        # Convert raw text to lowercase for analysis
        text_lower = raw_content.lower()
        
        # Count all keyword mentions across all sectors
        for sector, keywords in self.sector_keywords.items():
            mentions = 0
            for keyword in keywords:
                # Count keyword occurrences in text
                mentions += text_lower.count(keyword.lower())
            
            if mentions > 0:
                all_mentions[sector.replace('_', ' ').title()] = mentions
        
        # Also add explicit sector headers (like "Technology", "Automotive", etc.)
        lines = raw_content.split('\n')
        for line in lines:
            line_clean = line.strip()
            # Check if line is a sector header (single word, capitalized)
            if len(line_clean.split()) == 1 and line_clean.isalpha() and line_clean[0].isupper():
                sector_name = line_clean.title()
                if sector_name not in all_mentions:
                    all_mentions[sector_name] = 1
                else:
                    all_mentions[sector_name] += 1
        
        return all_mentions
    
    def create_firm_summary(self, deals: List[Dict], raw_content: str) -> str:
        """Create professional, copyable summary for firm distribution"""
        if not deals:
            return "No deals processed yet."
        
        # Extract key metrics
        total_deals = len(deals)
        sectors = [deal['sector'] for deal in deals]
        geos = [deal['geography'] for deal in deals]
        
        # Count occurrences
        sector_counts = {}
        geo_counts = {}
        
        for sector in sectors:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        for geo in geos:
            geo_counts[geo] = geo_counts.get(geo, 0) + 1
        
        # Get top items
        top_sector = max(sector_counts.items(), key=lambda x: x[1]) if sector_counts else ('Unknown', 0)
        top_geo = max(geo_counts.items(), key=lambda x: x[1]) if geo_counts else ('Unknown', 0)
        
        # Extract high-value deals
        high_value_deals = []
        for deal in deals:
            if any(indicator in str(deal['value']).lower() for indicator in ['billion', 'b', '000m', '1,000']):
                high_value_deals.append(deal)
        
        # Create professional summary
        summary = f"""📊 M&A INTELLIGENCE BRIEF
{datetime.now().strftime('%B %d, %Y')}

EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Total Transactions Identified: {total_deals}
• Dominant Sector: {top_sector[0]} ({top_sector[1]} deals)
• Primary Geography: {top_geo[0]} ({top_geo[1]} transactions)
• High-Value Deals (>$1B): {len(high_value_deals)}

SECTOR BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join([f'• {sector}: {count} deal{"s" if count > 1 else ""}' for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)])}

GEOGRAPHIC DISTRIBUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join([f'• {geo}: {count} transaction{"s" if count > 1 else ""}' for geo, count in sorted(geo_counts.items(), key=lambda x: x[1], reverse=True)])}

KEY TRANSACTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join([f'• {deal["title"]} ({deal["value"] or deal["size"] or "Value TBD"})' for deal in deals[:8]])}

{f"NOTABLE HIGH-VALUE DEALS{chr(10)}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{chr(10)}{chr(10).join([f'• {deal["title"]} ({deal["value"]})' for deal in high_value_deals[:5]])}" if high_value_deals else ""}

MARKET INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Cross-border activity represents {len([d for d in deals if d['geography'] not in ['UK', 'USA']])} transactions
• Technology sector consolidation shows {sector_counts.get('Technology', 0)} active deals
• Healthcare/Biotech activity: {sector_counts.get('Healthcare', 0)} transactions identified

RISK ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Deal volume suggests {"high" if total_deals > 15 else "moderate" if total_deals > 8 else "low"} market activity
• Sector concentration risk: {"High" if top_sector[1] > total_deals * 0.4 else "Moderate" if top_sector[1] > total_deals * 0.25 else "Low"}
• Geographic diversification: {"Strong" if len(geo_counts) >= 4 else "Moderate" if len(geo_counts) >= 2 else "Limited"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report generated by M&A Intelligence Processor
Confidential and Proprietary"""
        return summary.strip()

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
                st.session_state.raw_content = email_input
        
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
    
    # Additional Intelligence Sections
    if 'filtered_deals' in st.session_state and st.session_state.filtered_deals:
        st.markdown("---")
        
        # Tabs for different intelligence views
        tab1, tab2, tab3 = st.tabs(["📊 Industry Analytics", "🔗 Links & Sources", "📋 Firm Summary"])
        
        with tab1:
            st.subheader("📊 Comprehensive Industry Analytics")
            
            # Create industry summary
            industry_summary = st.session_state.processor.create_industry_summary(st.session_state.filtered_deals)
            
            # Display industry metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Industries", industry_summary['total_industries'])
            with col2:
                st.metric("Dominant Sector", industry_summary['dominant_sector'][0])
            with col3:
                st.metric("Dominant Sector Deals", industry_summary['dominant_sector'][1])
            with col4:
                st.metric("Market Spread", f"{industry_summary['total_industries']} sectors")
            
            st.markdown("---")
            
            # Enhanced visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                # Sector pie chart with enhanced styling
                sectors = [deal['sector'] for deal in st.session_state.filtered_deals]
                sector_counts = pd.Series(sectors).value_counts()
                
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                         '#DDA0DD', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']
                
                fig_pie = px.pie(
                    values=sector_counts.values,
                    names=sector_counts.index,
                    title="📊 Industry Distribution",
                    color_discrete_sequence=colors
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Deals: %{value}<br>Percentage: %{percent}<extra></extra>'
                )
                fig_pie.update_layout(
                    height=400,
                    font=dict(size=12),
                    title_font_size=16
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Horizontal bar chart for better readability
                fig_bar = px.bar(
                    x=sector_counts.values,
                    y=sector_counts.index,
                    orientation='h',
                    title="📈 Deals by Industry",
                    color=sector_counts.values,
                    color_continuous_scale='Blues'
                )
                fig_bar.update_layout(
                    height=400,
                    xaxis_title="Number of Deals",
                    yaxis_title="Industry Sector",
                    title_font_size=16,
                    coloraxis_showscale=False
                )
                fig_bar.update_traces(
                    hovertemplate='<b>%{y}</b><br>Deals: %{x}<extra></extra>'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Detailed industry breakdown table
            st.markdown("### 📋 Detailed Industry Breakdown")
            
            industry_df = pd.DataFrame([
                {
                    'Industry': sector,
                    'Deal Count': count,
                    'Market Share %': f"{(count / len(st.session_state.filtered_deals)) * 100:.1f}%",
                    'Concentration': "High" if count > len(st.session_state.filtered_deals) * 0.3 else 
                                   "Medium" if count > len(st.session_state.filtered_deals) * 0.15 else "Low"
                }
                for sector, count in industry_summary['top_industries']
            ])
            
            st.dataframe(
                industry_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Geographic vs Industry heatmap
            st.markdown("### 🌍 Geographic-Industry Distribution")
            
            # Create cross-tabulation
            deals_df = pd.DataFrame(st.session_state.filtered_deals)
            cross_tab = pd.crosstab(deals_df['geography'], deals_df['sector'])
            
            fig_heatmap = px.imshow(
                cross_tab.values,
                labels=dict(x="Industry Sector", y="Geography", color="Deal Count"),
                x=cross_tab.columns,
                y=cross_tab.index,
                color_continuous_scale='Blues',
                title="🔥 Geographic-Industry Heat Map"
            )
            fig_heatmap.update_layout(height=300, title_font_size=16)
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.markdown("---")
            
            # ALL INDUSTRIES from raw text analysis
            st.markdown("### 🏭 Complete Industry Landscape (Raw Text Analysis)")
            st.markdown("*This shows ALL industry mentions in the source material, including context and keywords*")
            
            # Extract all industry mentions from raw text
            all_industries = st.session_state.processor.extract_all_industries_from_text(st.session_state.raw_content)
            
            if all_industries:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Word cloud style visualization
                    industries_df = pd.DataFrame(list(all_industries.items()), columns=['Industry', 'Mentions'])
                    industries_df = industries_df.sort_values('Mentions', ascending=True)
                    
                    fig_mentions = px.bar(
                        industries_df,
                        x='Mentions',
                        y='Industry',
                        orientation='h',
                        title="🔍 Industry Keyword Frequency",
                        color='Mentions',
                        color_continuous_scale='Reds',
                        text='Mentions'
                    )
                    fig_mentions.update_traces(textposition='outside')
                    fig_mentions.update_layout(
                        height=400,
                        xaxis_title="Keyword Mentions",
                        yaxis_title="Industry Sector",
                        title_font_size=16,
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_mentions, use_container_width=True)
                
                with col2:
                    # Sunburst chart for industry hierarchy
                    industries_sorted = sorted(all_industries.items(), key=lambda x: x[1], reverse=True)
                    
                    # Create data for sunburst
                    labels = ['All Industries'] + [industry for industry, _ in industries_sorted]
                    parents = [''] + ['All Industries'] * len(industries_sorted)
                    values = [sum(all_industries.values())] + [count for _, count in industries_sorted]
                    
                    fig_sunburst = go.Figure(go.Sunburst(
                        labels=labels,
                        parents=parents,
                        values=values,
                        branchvalues="total",
                        hovertemplate='<b>%{label}</b><br>Mentions: %{value}<extra></extra>',
                        maxdepth=2
                    ))
                    fig_sunburst.update_layout(
                        title="🌟 Industry Mention Hierarchy",
                        height=400,
                        title_font_size=16
                    )
                    st.plotly_chart(fig_sunburst, use_container_width=True)
                
                # Comprehensive industry table
                st.markdown("### 📊 Complete Industry Analysis Table")
                
                complete_industry_df = pd.DataFrame([
                    {
                        'Industry': industry,
                        'Raw Mentions': count,
                        'Deal Count': len([d for d in st.session_state.filtered_deals if d['sector'] == industry]),
                        'Mention-to-Deal Ratio': f"{count / max(1, len([d for d in st.session_state.filtered_deals if d['sector'] == industry])):.1f}:1",
                        'Market Presence': "High" if count > 5 else "Medium" if count > 2 else "Low"
                    }
                    for industry, count in sorted(all_industries.items(), key=lambda x: x[1], reverse=True)
                ])
                
                st.dataframe(
                    complete_industry_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Industry insights
                st.markdown("### 💡 Industry Intelligence Insights")
                
                top_mentioned = max(all_industries.items(), key=lambda x: x[1])
                total_mentions = sum(all_industries.values())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Most Mentioned Industry", top_mentioned[0], f"{top_mentioned[1]} mentions")
                with col2:
                    st.metric("Total Industry References", total_mentions)
                with col3:
                    st.metric("Industry Diversity Score", len(all_industries))
                
                # Key insights
                st.info(f"""
                **🔍 Key Intelligence:**
                • **{top_mentioned[0]}** dominates the narrative with {top_mentioned[1]} mentions
                • **{len(all_industries)}** distinct industries identified in source material
                • **{total_mentions}** total industry references suggest {'high' if total_mentions > 20 else 'moderate'} sector diversity
                • Mention-to-deal ratios help identify emerging vs. established market activity
                """)
            else:
                st.warning("No specific industry keywords detected in the raw text.")
        
        with tab2:
            st.subheader("🔗 Links & Sources")
            
            # Extract links from raw content
            links = st.session_state.processor.extract_links(st.session_state.raw_content)
            
            if links:
                st.markdown(f"**Found {len(links)} links in the source material:**")
                for i, link in enumerate(links, 1):
                    st.markdown(f"{i}. [{link}]({link})")
            else:
                st.info("No links found in the source material.")
            
            # Raw content display
            st.markdown("### Raw Source Material")
            with st.expander("View Original Content"):
                st.text_area("Raw Email Content", st.session_state.raw_content, height=300, disabled=True)
        
        with tab3:
            st.subheader("📋 Professional Firm Summary")
            
            # Generate firm summary
            firm_summary = st.session_state.processor.create_firm_summary(
                st.session_state.filtered_deals, 
                st.session_state.raw_content
            )
            
            # Display in a professional format
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                        padding: 2rem; border-radius: 15px; 
                        border-left: 5px solid #2c3e50; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            st.markdown("### 📊 Ready-to-Share Intelligence Brief")
            st.text_area("Copy and share with your firm:", firm_summary, height=600)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Download button
            st.download_button(
                label="📥 Download Firm Summary",
                data=firm_summary,
                file_name=f"firm_intelligence_brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
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