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
    page_title="Smart Text Formatter & M&A Intelligence Processor",
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
    
    .formatted-text {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
    }
    
    .email-formatted {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid #e9ecef;
        margin-bottom: 1rem;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.5;
        white-space: pre-wrap;
    }
    
    .copy-button {
        background: #27ae60;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        cursor: pointer;
    }
    
    .section-header {
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.1rem;
        margin: 1.5rem 0 1rem 0;
    }
    
    .bullet-point {
        color: #2c3e50;
        margin: 0.5rem 0;
        padding-left: 1rem;
        border-left: 3px solid #3498db;
    }
    
    .highlight-text {
        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

class SmartTextProcessor:
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

    def format_raw_text(self, content: str) -> str:
        """Format raw text into a more readable structure with HTML"""
        if not content.strip():
            return "No content to format."
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Check if line is a section header (single word/short phrase, all caps or title case)
            if self._is_section_header(line):
                formatted_lines.append(f'<div class="section-header">📊 {line.upper()}</div>')
            
            # Check if line is a numbered item (deal/topic)
            elif re.match(r'^\d+\.', line):
                formatted_lines.append(f'<h3 style="color: #2c3e50; margin-top: 2rem; margin-bottom: 1rem;">🔸 {line}</h3>')
            
            # Check if line is a bullet point
            elif line.startswith('*') or line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()
                formatted_lines.append(f'<div class="bullet-point">• {bullet_text}</div>')
            
            # Check if line contains monetary values
            elif self._contains_monetary_value(line):
                highlighted_line = self._highlight_monetary_values(line)
                formatted_lines.append(f'<p style="margin: 1rem 0; color: #2c3e50;"><strong>{highlighted_line}</strong></p>')
            
            # Check if line contains key metadata (Source:, Size:, etc.)
            elif ':' in line and self._is_metadata_line(line):
                key, value = line.split(':', 1)
                formatted_lines.append(f'<p style="margin: 0.5rem 0; color: #7f8c8d;"><span style="font-weight: 600;">{key.strip()}:</span> {value.strip()}</p>')
            
            # Regular paragraph text
            else:
                # Highlight important terms
                highlighted_text = self._highlight_important_terms(line)
                formatted_lines.append(f'<p style="margin: 1rem 0; color: #2c3e50; line-height: 1.6;">{highlighted_text}</p>')
        
        return '\n'.join(formatted_lines)

    def format_for_email(self, content: str) -> str:
        """Format raw text for email-friendly plain text"""
        if not content.strip():
            return "No content to format."
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Check if line is a section header
            if self._is_section_header(line):
                formatted_lines.append('')
                formatted_lines.append('═' * 60)
                formatted_lines.append(f'📊 {line.upper()}')
                formatted_lines.append('═' * 60)
                formatted_lines.append('')
            
            # Check if line is a numbered item (deal/topic)
            elif re.match(r'^\d+\.', line):
                formatted_lines.append('')
                formatted_lines.append('─' * 50)
                formatted_lines.append(f'🔸 {line}')
                formatted_lines.append('─' * 50)
            
            # Check if line is a bullet point
            elif line.startswith('*') or line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()
                formatted_lines.append(f'   • {bullet_text}')
            
            # Check if line contains monetary values
            elif self._contains_monetary_value(line):
                # Mark monetary values with ** for emphasis
                highlighted_line = self._mark_monetary_values_for_email(line)
                formatted_lines.append(f'💰 {highlighted_line}')
            
            # Check if line contains key metadata
            elif ':' in line and self._is_metadata_line(line):
                key, value = line.split(':', 1)
                formatted_lines.append(f'   {key.strip()}: {value.strip()}')
            
            # Regular paragraph text
            else:
                # Mark important terms with ** for emphasis
                emphasized_text = self._emphasize_important_terms_for_email(line)
                formatted_lines.append(f'{emphasized_text}')
        
        # Add header and footer for professional email format
        email_header = f"""📧 FORMATTED INTELLIGENCE REPORT
Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

{'=' * 70}"""
        
        email_footer = f"""{'=' * 70}

This report was automatically formatted for email distribution.
Generated by Smart Text Formatter & M&A Intelligence Processor
"""
        
        formatted_content = '\n'.join(formatted_lines)
        return f"{email_header}\n\n{formatted_content}\n{email_footer}"

    def _mark_monetary_values_for_email(self, line: str) -> str:
        """Mark monetary values with ** for email emphasis"""
        # Pattern for currency values
        currency_pattern = r'((?:EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+(?:\s*(?:million|billion|bn|m))?)'
        line = re.sub(currency_pattern, r'**\1**', line, flags=re.IGNORECASE)
        
        # Pattern for standalone monetary amounts
        amount_pattern = r'([\d,\.]+\s*(?:million|billion|bn|m)\b)'
        line = re.sub(amount_pattern, r'**\1**', line, flags=re.IGNORECASE)
        
        return line

    def _emphasize_important_terms_for_email(self, line: str) -> str:
        """Emphasize important business terms with ** for email"""
        important_terms = [
            'acquisition', 'merger', 'joint venture', 'investment', 'funding',
            'ipo', 'listing', 'talks', 'discussions', 'announced', 'completed',
            'signed', 'agreement', 'deal', 'transaction', 'partnership'
        ]
        
        for term in important_terms:
            pattern = r'\b(' + re.escape(term) + r')\b'
            line = re.sub(pattern, r'**\1**', line, flags=re.IGNORECASE)
        
        return line
    
    def _is_section_header(self, line: str) -> bool:
        """Check if line is likely a section header"""
        words = line.split()
        return (len(words) <= 3 and 
                len(line) < 50 and
                (line.isupper() or line.istitle()) and
                not line.startswith('*') and
                not re.match(r'^\d+\.', line) and
                not any(char in line for char in ['(', ')', '€', '$', '£', ':']))
    
    def _contains_monetary_value(self, line: str) -> bool:
        """Check if line contains monetary values"""
        return bool(re.search(r'(EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+', line, re.IGNORECASE) or
                   re.search(r'[\d,\.]+\s*(million|billion|bn|m)\b', line, re.IGNORECASE))
    
    def _highlight_monetary_values(self, line: str) -> str:
        """Highlight monetary values in text"""
        # Pattern for currency values
        currency_pattern = r'((?:EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+(?:\s*(?:million|billion|bn|m))?)'
        line = re.sub(currency_pattern, r'<span class="highlight-text">\1</span>', line, flags=re.IGNORECASE)
        
        # Pattern for standalone monetary amounts
        amount_pattern = r'([\d,\.]+\s*(?:million|billion|bn|m)\b)'
        line = re.sub(amount_pattern, r'<span class="highlight-text">\1</span>', line, flags=re.IGNORECASE)
        
        return line
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line contains metadata (Source:, Size:, etc.)"""
        metadata_keys = ['source', 'size', 'grade', 'intelligence id', 'stake value', 'alert']
        key_part = line.split(':', 1)[0].lower().strip()
        return any(meta_key in key_part for meta_key in metadata_keys)
    
    def _highlight_important_terms(self, line: str) -> str:
        """Highlight important business terms"""
        important_terms = [
            'acquisition', 'merger', 'joint venture', 'investment', 'funding',
            'ipo', 'listing', 'talks', 'discussions', 'announced', 'completed',
            'signed', 'agreement', 'deal', 'transaction', 'partnership'
        ]
        
        for term in important_terms:
            pattern = r'\b(' + re.escape(term) + r')\b'
            line = re.sub(pattern, r'<strong>\1</strong>', line, flags=re.IGNORECASE)
        
        return line

    def extract_key_information(self, content: str) -> Dict[str, Any]:
        """Extract key information from the text"""
        lines = content.split('\n')
        
        info = {
            'total_lines': len([l for l in lines if l.strip()]),
            'sections': [],
            'deals': [],
            'monetary_values': [],
            'companies': [],
            'metadata': {}
        }
        
        current_section = None
        deal_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Track sections
            if self._is_section_header(line):
                current_section = line
                info['sections'].append(line)
            
            # Track numbered deals
            if re.match(r'^\d+\.', line):
                deal_count += 1
                info['deals'].append({
                    'number': deal_count,
                    'title': line,
                    'section': current_section
                })
            
            # Extract monetary values
            monetary_matches = re.findall(r'((?:EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+(?:\s*(?:million|billion|bn|m))?)', line, re.IGNORECASE)
            info['monetary_values'].extend(monetary_matches)
            
            # Extract metadata
            if ':' in line and self._is_metadata_line(line):
                key, value = line.split(':', 1)
                info['metadata'][key.strip()] = value.strip()
        
        return info

    def create_summary(self, content: str) -> str:
        """Create a professional summary of the content"""
        info = self.extract_key_information(content)
        
        summary = f"""📊 DOCUMENT ANALYSIS SUMMARY
{datetime.now().strftime('%B %d, %Y')}

CONTENT OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Total Content Lines: {info['total_lines']}
• Identified Sections: {len(info['sections'])}
• Numbered Items/Deals: {len(info['deals'])}
• Monetary References: {len(set(info['monetary_values']))}

{f"SECTIONS IDENTIFIED{chr(10)}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{chr(10)}{chr(10).join([f'• {section}' for section in info['sections']])}" if info['sections'] else ""}

{f"KEY ITEMS{chr(10)}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{chr(10)}{chr(10).join([f'• {deal["title"][:100]}...' if len(deal["title"]) > 100 else f'• {deal["title"]}' for deal in info['deals'][:10]])}" if info['deals'] else ""}

{f"MONETARY VALUES DETECTED{chr(10)}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{chr(10)}{chr(10).join([f'• {value}' for value in list(set(info['monetary_values']))[:10]])}" if info['monetary_values'] else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated by Smart Text Formatter"""
        
        return summary.strip()

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Smart Text Formatter & M&A Intelligence Processor</h1>
        <p>Transform raw text and M&A data into professionally formatted, readable content</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize processor
    if 'processor' not in st.session_state:
        st.session_state.processor = SmartTextProcessor()
    
    # Main layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Raw Text Input")
        
        # Sample data for demonstration
        sample_data = """Automotive

2. Magirus could expand outside of Germany through acquisitions - report (translated)

* Subsidiaries planned in Switzerland, Spain, Poland, and UAE
* Aims to set up production sites in Romania, Croatia through acquisitions
* Aims to double sales to EUR 750m by 2030

Magirus, the German fire protection group, could acquire to expand its business outside of Germany, Schwäbische Zeitung reported.

Without citing a specific source, the German daily said Magirus wants to establish subsidiaries in Switzerland, Spain, Poland and the United Arab Emirates.

Source: Schwäbische Zeitung
Size: 60m-300m (GBP)
Grade: Rumoured
Intelligence ID: intelcms-2bxt7z

Technology

3. Adarga seeks GBP 6m-GBP 8m in new funding – report

* Previous USD 20m investment round led by BOKA Group

Adarga is engaged in extensive discussions with a potential investor regarding a capital infusion ranging from GBP 6m to GBP 8m, Sky News reported.

The company specializes in artificial intelligence solutions for defense applications and has been growing rapidly in the UK market.

Source: Sky News
Size: 5m-30m (GBP)
Grade: Strong evidence
Intelligence ID: intelcms-k9mrqp"""
        
        text_input = st.text_area(
            "Paste your raw text here:",
            value=sample_data,
            height=500,
            help="Paste any raw text content. The system will automatically format it for better readability."
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            format_button = st.button("🚀 Format Text", type="primary", use_container_width=True)
        
        with col_b:
            clear_button = st.button("🗑️ Clear", use_container_width=True)
        
        if clear_button:
            st.rerun()
    
    with col2:
        st.subheader("📊 Formatted Output")
        
        if format_button and text_input:
            with st.spinner("Formatting your text..."):
                # Format the text for both web and email
                formatted_text = st.session_state.processor.format_raw_text(text_input)
                email_formatted_text = st.session_state.processor.format_for_email(text_input)
                
                # Store in session state
                st.session_state.formatted_text = formatted_text
                st.session_state.email_formatted_text = email_formatted_text
                st.session_state.raw_input = text_input
        
        # Display formatted text if available
        if 'formatted_text' in st.session_state:
            # Tabs for different viewing options
            tab1, tab2 = st.tabs(["🖥️ Web View", "📧 Email Ready"])
            
            with tab1:
                st.markdown(f"""
                <div class="formatted-text">
                    {st.session_state.formatted_text}
                </div>
                """, unsafe_allow_html=True)
            
            with tab2:
                st.markdown("### 📧 Email-Ready Format")
                st.info("💡 This format is optimized for copying and pasting into emails. It uses plain text formatting that works in any email client.")
                
                # Display email-formatted text in a copyable text area
                st.text_area(
                    "Copy this text for email:",
                    value=st.session_state.email_formatted_text,
                    height=600,
                    help="Select all (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C) to paste into your email."
                )
                
                # Download button for email format
                st.download_button(
                    label="📧 Download Email Format",
                    data=st.session_state.email_formatted_text,
                    file_name=f"email_ready_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    help="Download as a text file that you can copy from or attach to emails."
                )
        else:
            st.info("Ready to format your text. Paste content and click 'Format Text'")
    
    # Additional features
    if 'formatted_text' in st.session_state:
        st.markdown("---")
        
        # Tabs for additional features
        tab1, tab2, tab3 = st.tabs(["📊 Content Analysis", "📋 Professional Summary", "💾 Export Options"])
        
        with tab1:
            st.subheader("📊 Content Analysis")
            
            # Extract and display key information
            key_info = st.session_state.processor.extract_key_information(st.session_state.raw_input)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Lines", key_info['total_lines'])
            
            with col2:
                st.metric("Sections", len(key_info['sections']))
            
            with col3:
                st.metric("Key Items", len(key_info['deals']))
            
            with col4:
                st.metric("Monetary Values", len(set(key_info['monetary_values'])))
            
            if key_info['sections']:
                st.markdown("### 📁 Sections Identified")
                for i, section in enumerate(key_info['sections'], 1):
                    st.markdown(f"{i}. **{section}**")
            
            if key_info['deals']:
                st.markdown("### 🎯 Key Items/Deals")
                deals_df = pd.DataFrame(key_info['deals'])
                st.dataframe(deals_df, use_container_width=True, hide_index=True)
            
            if key_info['monetary_values']:
                st.markdown("### 💰 Monetary Values Found")
                unique_values = list(set(key_info['monetary_values']))
                for value in unique_values:
                    st.markdown(f"• {value}")
        
        with tab2:
            st.subheader("📋 Professional Summary")
            
            summary = st.session_state.processor.create_summary(st.session_state.raw_input)
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                        padding: 2rem; border-radius: 15px; 
                        border-left: 5px solid #2c3e50; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            st.text_area("Professional Summary:", summary, height=400)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab3:
            st.subheader("💾 Export Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Export formatted HTML
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Formatted Document</title>
                    <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 2rem; line-height: 1.6; }}
                    .section-header {{ background: #2c3e50; color: white; padding: 1rem; border-radius: 8px; margin: 1.5rem 0 1rem 0; }}
                    .bullet-point {{ color: #2c3e50; margin: 0.5rem 0; padding-left: 1rem; border-left: 3px solid #3498db; }}
                    .highlight-text {{ background: #f39c12; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; }}
                    </style>
                </head>
                <body>
                    <h1>Formatted Document</h1>
                    <div class="formatted-text">
                        {st.session_state.formatted_text}
                    </div>
                </body>
                </html>
                """
                
                st.download_button(
                    label="📄 Download HTML",
                    data=html_content,
                    file_name=f"formatted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True
                )
            
            with col2:
                # Export email format
                st.download_button(
                    label="📧 Download Email Format",
                    data=st.session_state.email_formatted_text,
                    file_name=f"email_format_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col3:
                # Export summary
                summary = st.session_state.processor.create_summary(st.session_state.raw_input)
                st.download_button(
                    label="📊 Download Summary",
                    data=summary,
                    file_name=f"content_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

if __name__ == "__main__":
    main()