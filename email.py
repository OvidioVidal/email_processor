import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sqlite3
import hashlib

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
    
    .database-info {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #27ae60;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class DatabaseManager:
    def __init__(self, db_path="ma_intelligence.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE,
                raw_content TEXT,
                formatted_content TEXT,
                processed_date DATETIME,
                total_deals INTEGER,
                total_sections INTEGER,
                total_monetary_values INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create deals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                deal_number INTEGER,
                title TEXT,
                sector TEXT,
                geography TEXT,
                value_text TEXT,
                size_category TEXT,
                grade TEXT,
                source TEXT,
                intelligence_id TEXT,
                stake_value TEXT,
                identified_sector TEXT,
                is_priority BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create sections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                section_name TEXT,
                deal_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create monetary_values table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monetary_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                value_text TEXT,
                currency TEXT,
                amount REAL,
                unit TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                key TEXT,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Migration: Add new columns to existing databases
        try:
            cursor.execute('ALTER TABLE deals ADD COLUMN identified_sector TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE deals ADD COLUMN is_priority BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
    
    def get_content_hash(self, content: str) -> str:
        """Generate a hash for the content to avoid duplicates"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def save_email_data(self, raw_content: str, formatted_content: str, deals_data: List[Dict], key_info: Dict) -> int:
        """Save email and all extracted data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        content_hash = self.get_content_hash(raw_content)
        
        try:
            # Check if email already exists
            cursor.execute('SELECT id FROM emails WHERE content_hash = ?', (content_hash,))
            existing = cursor.fetchone()
            
            if existing:
                st.warning("This email content has already been processed and saved.")
                return existing[0]
            
            # Insert email record
            cursor.execute('''
                INSERT INTO emails (content_hash, raw_content, formatted_content, processed_date, 
                                  total_deals, total_sections, total_monetary_values)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_hash,
                raw_content,
                formatted_content,
                datetime.now().isoformat(),
                len(key_info['deals']),
                len(key_info['sections']),
                len(set(key_info['monetary_values']))
            ))
            
            email_id = cursor.lastrowid
            
            # Insert deals data
            for deal in key_info['deals']:
                # Extract additional info from deals_data if available
                deal_info = next((d for d in deals_data if d.get('id') == str(deal['number'])), {})
                
                cursor.execute('''
                    INSERT INTO deals (email_id, deal_number, title, sector, geography, 
                                     value_text, size_category, grade, source, intelligence_id, stake_value,
                                     identified_sector, is_priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email_id,
                    deal['number'],
                    deal['title'],
                    deal.get('section', 'Unknown'),
                    deal_info.get('geography', 'Unknown'),
                    deal_info.get('value', ''),
                    deal_info.get('size', ''),
                    deal_info.get('grade', ''),
                    deal_info.get('source', ''),
                    deal_info.get('intelligence_id', ''),
                    deal_info.get('stake_value', ''),
                    deal_info.get('identified_sector', 'Other'),
                    deal_info.get('is_priority', False)
                ))
            
            # Insert sections
            section_counts = {}
            for deal in key_info['deals']:
                section = deal.get('section', 'Unknown')
                section_counts[section] = section_counts.get(section, 0) + 1
            
            for section, count in section_counts.items():
                cursor.execute('''
                    INSERT INTO sections (email_id, section_name, deal_count)
                    VALUES (?, ?, ?)
                ''', (email_id, section, count))
            
            # Insert monetary values
            for value in set(key_info['monetary_values']):
                # Parse currency and amount
                currency, amount, unit = self.parse_monetary_value(value)
                cursor.execute('''
                    INSERT INTO monetary_values (email_id, value_text, currency, amount, unit)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email_id, value, currency, amount, unit))
            
            # Insert metadata
            for key, value in key_info['metadata'].items():
                cursor.execute('''
                    INSERT INTO metadata (email_id, key, value)
                    VALUES (?, ?, ?)
                ''', (email_id, key, value))
            
            conn.commit()
            st.success(f"✅ Email data saved to database! Email ID: {email_id}")
            return email_id
            
        except Exception as e:
            conn.rollback()
            st.error(f"Error saving to database: {str(e)}")
            return None
        finally:
            conn.close()
    
    def parse_monetary_value(self, value_text: str) -> tuple:
        """Parse monetary value to extract currency, amount, and unit"""
        # Extract currency
        currency_match = re.search(r'(EUR|USD|GBP|CNY|\$|£|€)', value_text, re.IGNORECASE)
        currency = currency_match.group(1) if currency_match else ''
        
        # Extract amount with improved handling
        amount_match = re.search(r'([\d,\.]+)', value_text)
        amount = 0.0
        if amount_match:
            try:
                # Clean the amount string - remove trailing periods and commas
                amount_str = amount_match.group(1).replace(',', '').rstrip('.')
                # Handle cases where there might be multiple periods
                if amount_str.count('.') > 1:
                    # Keep only the last period as decimal separator
                    parts = amount_str.split('.')
                    amount_str = ''.join(parts[:-1]) + '.' + parts[-1] if len(parts) > 1 else parts[0]
                
                amount = float(amount_str) if amount_str and amount_str != '.' else 0.0
            except (ValueError, AttributeError):
                # If conversion fails, default to 0.0
                amount = 0.0
        
        # Extract unit
        unit_match = re.search(r'(million|billion|bn|m|k)\b', value_text, re.IGNORECASE)
        unit = unit_match.group(1) if unit_match else ''
        
        return currency, amount, unit
    
    def get_market_insights(self) -> Dict[str, Any]:
        """Get market insights from stored data"""
        conn = sqlite3.connect(self.db_path)
        
        # Get overview stats
        overview_query = '''
            SELECT 
                COUNT(*) as total_emails,
                SUM(total_deals) as total_deals,
                AVG(total_deals) as avg_deals_per_email,
                COUNT(DISTINCT DATE(created_at)) as active_days
            FROM emails
        '''
        overview = pd.read_sql_query(overview_query, conn)
        
        # Get sector trends
        sector_query = '''
            SELECT 
                sector,
                COUNT(*) as deal_count,
                DATE(created_at) as date
            FROM deals
            WHERE sector != 'Unknown'
            GROUP BY sector, DATE(created_at)
            ORDER BY date DESC
        '''
        sector_trends = pd.read_sql_query(sector_query, conn)
        
        # Get top sectors
        top_sectors_query = '''
            SELECT 
                sector,
                COUNT(*) as deal_count
            FROM deals
            WHERE sector != 'Unknown'
            GROUP BY sector
            ORDER BY deal_count DESC
            LIMIT 10
        '''
        top_sectors = pd.read_sql_query(top_sectors_query, conn)
        
        # Get recent activity
        recent_query = '''
            SELECT 
                e.processed_date,
                e.total_deals,
                e.total_sections
            FROM emails e
            ORDER BY e.created_at DESC
            LIMIT 30
        '''
        recent_activity = pd.read_sql_query(recent_query, conn)
        
        # Get value distribution
        value_query = '''
            SELECT 
                currency,
                AVG(amount) as avg_amount,
                COUNT(*) as count,
                unit
            FROM monetary_values
            WHERE amount > 0
            GROUP BY currency, unit
        '''
        value_distribution = pd.read_sql_query(value_query, conn)
        
        conn.close()
        
        return {
            'overview': overview,
            'sector_trends': sector_trends,
            'top_sectors': top_sectors,
            'recent_activity': recent_activity,
            'value_distribution': value_distribution
        }
    
    def get_all_database_contents(self) -> Dict[str, pd.DataFrame]:
        """Get all database contents for viewing"""
        conn = sqlite3.connect(self.db_path)
        
        # Get all emails
        emails_query = '''
            SELECT 
                id,
                content_hash,
                SUBSTR(raw_content, 1, 100) || '...' as content_preview,
                processed_date,
                total_deals,
                total_sections,
                total_monetary_values,
                created_at
            FROM emails
            ORDER BY created_at DESC
        '''
        emails = pd.read_sql_query(emails_query, conn)
        
        # Get all deals
        deals_query = '''
            SELECT 
                d.id,
                d.email_id,
                d.deal_number,
                d.title,
                d.sector,
                d.geography,
                d.value_text,
                d.size_category,
                d.grade,
                d.source,
                d.intelligence_id,
                d.stake_value,
                d.identified_sector,
                d.is_priority,
                d.created_at
            FROM deals d
            ORDER BY d.created_at DESC
        '''
        deals = pd.read_sql_query(deals_query, conn)
        
        # Get all sections
        sections_query = '''
            SELECT 
                s.id,
                s.email_id,
                s.section_name,
                s.deal_count,
                s.created_at
            FROM sections s
            ORDER BY s.created_at DESC
        '''
        sections = pd.read_sql_query(sections_query, conn)
        
        # Get all monetary values
        monetary_query = '''
            SELECT 
                m.id,
                m.email_id,
                m.value_text,
                m.currency,
                m.amount,
                m.unit,
                m.created_at
            FROM monetary_values m
            ORDER BY m.created_at DESC
        '''
        monetary_values = pd.read_sql_query(monetary_query, conn)
        
        # Get all metadata
        metadata_query = '''
            SELECT 
                m.id,
                m.email_id,
                m.key,
                m.value,
                m.created_at
            FROM metadata m
            ORDER BY m.created_at DESC
        '''
        metadata = pd.read_sql_query(metadata_query, conn)
        
        conn.close()
        
        return {
            'emails': emails,
            'deals': deals,
            'sections': sections,
            'monetary_values': monetary_values,
            'metadata': metadata
        }
    
    def get_email_details(self, email_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific email"""
        conn = sqlite3.connect(self.db_path)
        
        # Get email info
        email_query = 'SELECT * FROM emails WHERE id = ?'
        email_info = pd.read_sql_query(email_query, conn, params=(email_id,))
        
        # Get related deals
        deals_query = 'SELECT * FROM deals WHERE email_id = ?'
        deals = pd.read_sql_query(deals_query, conn, params=(email_id,))
        
        # Get related sections
        sections_query = 'SELECT * FROM sections WHERE email_id = ?'
        sections = pd.read_sql_query(sections_query, conn, params=(email_id,))
        
        # Get related monetary values
        monetary_query = 'SELECT * FROM monetary_values WHERE email_id = ?'
        monetary_values = pd.read_sql_query(monetary_query, conn, params=(email_id,))
        
        # Get related metadata
        metadata_query = 'SELECT * FROM metadata WHERE email_id = ?'
        metadata = pd.read_sql_query(metadata_query, conn, params=(email_id,))
        
        conn.close()
        
        return {
            'email_info': email_info,
            'deals': deals,
            'sections': sections,
            'monetary_values': monetary_values,
            'metadata': metadata
        }
    
    def delete_email(self, email_id: int) -> bool:
        """Delete an email and all its associated data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete associated data first (foreign key constraints)
            cursor.execute('DELETE FROM deals WHERE email_id = ?', (email_id,))
            cursor.execute('DELETE FROM sections WHERE email_id = ?', (email_id,))
            cursor.execute('DELETE FROM monetary_values WHERE email_id = ?', (email_id,))
            cursor.execute('DELETE FROM metadata WHERE email_id = ?', (email_id,))
            
            # Delete the email
            cursor.execute('DELETE FROM emails WHERE id = ?', (email_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error deleting email: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_deal(self, deal_id: int) -> bool:
        """Delete a specific deal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM deals WHERE id = ?', (deal_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error deleting deal: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_all_data(self) -> bool:
        """Delete all data from the database (nuclear option)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete all data from all tables
            cursor.execute('DELETE FROM deals')
            cursor.execute('DELETE FROM sections')
            cursor.execute('DELETE FROM monetary_values')
            cursor.execute('DELETE FROM metadata')
            cursor.execute('DELETE FROM emails')
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error deleting all data: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        tables = ['emails', 'deals', 'sections', 'monetary_values', 'metadata']
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def get_priority_sector_deals(self, priority_sectors: List[str]) -> pd.DataFrame:
        """Get deals filtered by priority sectors"""
        conn = sqlite3.connect(self.db_path)
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?'] * len(priority_sectors))
        
        deals_query = f'''
            SELECT 
                d.id,
                d.email_id,
                d.deal_number,
                d.title,
                d.sector,
                d.geography,
                d.value_text,
                d.size_category,
                d.grade,
                d.source,
                d.intelligence_id,
                d.stake_value,
                d.identified_sector,
                d.is_priority,
                d.created_at
            FROM deals d
            WHERE d.identified_sector IN ({placeholders})
            ORDER BY d.created_at DESC
        '''
        
        deals = pd.read_sql_query(deals_query, conn, params=priority_sectors)
        conn.close()
        
        return deals

class SmartTextProcessor:
    def __init__(self):
        # Priority sectors that are important to the user
        self.priority_sectors = [
            'Computer software',
            'Consumer: Foods',
            'Consumer: Other', 
            'Consumer: Retail',
            'Defense',
            'Financial Services',
            'Industrial automation',
            'Industrial products and services',
            'Industrial: Electronics',
            'Services (other)'
        ]
        
        # Mapping from common email section headers to priority sectors
        self.section_to_priority_mapping = {
            'AUTOMOTIVE': 'Industrial products and services',
            'TECHNOLOGY': 'Computer software',
            'TECH': 'Computer software',
            'SOFTWARE': 'Computer software',
            'FINANCIAL': 'Financial Services',
            'FINANCE': 'Financial Services',
            'BANKING': 'Financial Services',
            'DEFENSE': 'Defense',
            'DEFENCE': 'Defense',
            'MILITARY': 'Defense',
            'CONSUMER': 'Consumer: Other',
            'RETAIL': 'Consumer: Retail',
            'FOOD': 'Consumer: Foods',
            'FOODS': 'Consumer: Foods',
            'INDUSTRIAL': 'Industrial products and services',
            'MANUFACTURING': 'Industrial products and services',
            'ELECTRONICS': 'Industrial: Electronics',
            'AUTOMATION': 'Industrial automation',
            'SERVICES': 'Services (other)',
            'CONSULTING': 'Services (other)',
            'ENERGY': 'Industrial products and services',
            'HEALTHCARE': 'Services (other)',
            'REAL ESTATE': 'Services (other)',
            'TELECOMMUNICATIONS': 'Computer software',
            'TELECOM': 'Computer software'
        }
        
        self.sector_keywords = {
            'Computer software': ['software', 'tech', 'AI', 'digital', 'data', 'cyber', 'SaaS', 'IT', 'cloud', 'app', 'platform', 'programming', 'coding', 'database', 'analytics'],
            'Consumer: Foods': ['food', 'beverage', 'restaurant', 'cafe', 'catering', 'nutrition', 'organic', 'dairy', 'meat', 'snack', 'drink', 'culinary', 'grocery'],
            'Consumer: Other': ['consumer', 'lifestyle', 'personal', 'household', 'beauty', 'cosmetic', 'fashion', 'apparel', 'entertainment', 'media', 'leisure'],
            'Consumer: Retail': ['retail', 'store', 'shop', 'e-commerce', 'marketplace', 'outlet', 'chain', 'brand', 'merchandise', 'commerce', 'sales'],
            'Defense': ['defense', 'defence', 'military', 'aerospace', 'security', 'surveillance', 'weapons', 'armament', 'naval', 'aviation', 'tactical'],
            'Financial Services': ['bank', 'finance', 'financial', 'capital', 'investment', 'insurance', 'fund', 'fintech', 'trading', 'lending', 'credit', 'wealth', 'asset'],
            'Industrial automation': ['automation', 'robotics', 'control', 'process', 'manufacturing', 'assembly', 'conveyor', 'sensor', 'plc', 'scada', 'industrial control'],
            'Industrial products and services': ['industrial', 'manufacturing', 'engineering', 'construction', 'machinery', 'equipment', 'tools', 'materials', 'components', 'fabrication'],
            'Industrial: Electronics': ['electronics', 'semiconductor', 'circuit', 'chip', 'component', 'pcb', 'embedded', 'microprocessor', 'sensor', 'electronic'],
            'Services (other)': ['services', 'consulting', 'professional', 'advisory', 'support', 'maintenance', 'repair', 'logistics', 'transportation', 'outsourcing']
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
        
        # Apply content filtering based on current filter settings
        try:
            import streamlit as st
            filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
            selected_sectors = st.session_state.get('selected_sectors', self.priority_sectors)
            content = self._filter_content_by_priority_sections(content, filter_mode, selected_sectors)
        except:
            # Fallback if session state is not available
            pass
        
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
        """Format raw text for email-friendly plain text matching the specific format"""
        if not content.strip():
            return "No content to format."
        
        # Apply content filtering based on current filter settings
        try:
            import streamlit as st
            filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
            selected_sectors = st.session_state.get('selected_sectors', self.priority_sectors)
            content = self._filter_content_by_priority_sections(content, filter_mode, selected_sectors)
        except:
            # Fallback if session state is not available
            pass
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Check if line is a section header (clean, simple format)
            if self._is_section_header(line):
                # Add spacing before section headers
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(line)
                formatted_lines.append('')
            
            # Check if line is a numbered item (deal/topic)
            elif re.match(r'^\d+\.', line):
                formatted_lines.append(line)
                formatted_lines.append('')  # Add blank line after numbered items
            
            # Check if line is a bullet point
            elif line.startswith('*') or line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()
                formatted_lines.append(f'* {bullet_text}')
            
            # Check if line contains key metadata (Source:, Size:, etc.)
            elif ':' in line and self._is_metadata_line(line):
                formatted_lines.append(line)
            
            # Regular paragraph text
            else:
                formatted_lines.append(line)
        
        # Clean up multiple consecutive blank lines
        cleaned_lines = []
        prev_was_blank = False
        
        for line in formatted_lines:
            if line == '':
                if not prev_was_blank:
                    cleaned_lines.append(line)
                prev_was_blank = True
            else:
                cleaned_lines.append(line)
                prev_was_blank = False
        
        # Remove trailing blank lines
        while cleaned_lines and cleaned_lines[-1] == '':
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)

    def parse_deals_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse deals with enhanced information extraction"""
        deals = []
        lines = content.split('\n')
        current_deal = None
        current_sector = "Other"
        current_priority_sector = "Other"
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check for sector header
            if self._is_section_header(line):
                current_sector = line.title()
                # Map the section to priority sector immediately
                current_priority_sector = self.map_section_to_priority(line)
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
                    'sector': current_sector,
                    'geography': self.extract_geography(title),
                    'details': [],
                    'value': self.extract_value(title),
                    'grade': '',
                    'size': '',
                    'source': '',
                    'intelligence_id': '',
                    'stake_value': 'N/A',
                    'original_text': title,
                    'identified_sector': current_priority_sector,  # Start with section mapping
                    'is_priority': self.is_priority_sector(current_priority_sector),
                    'section_mapped_sector': current_priority_sector  # Keep track of section mapping
                }
                
                # Collect subsequent lines for this deal
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    
                    # Stop if we hit the next numbered deal or sector
                    if re.match(r'^\d+\.', next_line) or self._is_section_header(next_line):
                        break
                    
                    current_deal['original_text'] += '\n' + next_line
                    
                    if next_line.startswith('*'):
                        current_deal['details'].append(next_line[1:].strip())
                    elif 'Size:' in next_line:
                        current_deal['size'] = next_line.split('Size:')[1].strip()
                    elif 'Grade:' in next_line:
                        current_deal['grade'] = next_line.split('Grade:')[1].strip()
                    elif 'Source:' in next_line:
                        current_deal['source'] = next_line.split('Source:')[1].strip()
                    elif 'Intelligence ID:' in next_line:
                        current_deal['intelligence_id'] = next_line.split('Intelligence ID:')[1].strip()
                    elif 'Stake Value:' in next_line:
                        current_deal['stake_value'] = next_line.split('Stake Value:')[1].strip()
                    elif self._contains_monetary_value(next_line):
                        if not current_deal['value'] or current_deal['value'] == 'TBD':
                            current_deal['value'] = self.extract_value(next_line)
                    
                    j += 1
        
        # Don't forget the last deal
        if current_deal:
            # Enhance sector identification by combining section mapping with content analysis
            content_identified_sector = self.identify_sector(current_deal['original_text'])
            section_mapped_sector = current_deal.get('section_mapped_sector', 'Other')
            
            # Use section mapping if it's a priority sector, otherwise use content analysis
            if self.is_priority_sector(section_mapped_sector):
                final_sector = section_mapped_sector
            elif self.is_priority_sector(content_identified_sector):
                final_sector = content_identified_sector
            else:
                # If neither are priority, prefer content analysis
                final_sector = content_identified_sector
            
            current_deal['identified_sector'] = final_sector
            current_deal['is_priority'] = self.is_priority_sector(final_sector)
            deals.append(current_deal)
        
        # Process all deals to enhance sector identification
        for deal in deals:
            content_identified_sector = self.identify_sector(deal['original_text'])
            section_mapped_sector = deal.get('section_mapped_sector', 'Other')
            
            # Use section mapping if it's a priority sector, otherwise use content analysis
            if self.is_priority_sector(section_mapped_sector):
                final_sector = section_mapped_sector
            elif self.is_priority_sector(content_identified_sector):
                final_sector = content_identified_sector
            else:
                # If neither are priority, prefer content analysis
                final_sector = content_identified_sector
            
            deal['identified_sector'] = final_sector
            deal['is_priority'] = self.is_priority_sector(final_sector)
        
        return deals

    def extract_geography(self, title: str) -> str:
        """Extract geography from deal title"""
        lower_title = title.lower()
        for geo, keywords in self.geo_keywords.items():
            if any(keyword in lower_title for keyword in keywords):
                return geo.upper()
        return 'Global'
    
    def identify_sector(self, text: str) -> str:
        """Identify sector based on content using priority sectors first"""
        upper_text = text.upper()
        lower_text = text.lower()
        
        # First, check if we can directly map from section headers
        for section_header, priority_sector in self.section_to_priority_mapping.items():
            if section_header in upper_text:
                return priority_sector
        
        # Then check priority sectors using keyword matching
        sector_scores = {}
        for sector, keywords in self.sector_keywords.items():
            score = sum(1 for keyword in keywords if keyword in lower_text)
            if score > 0:
                sector_scores[sector] = score
        
        if sector_scores:
            # Return the sector with the highest keyword match score
            best_sector = max(sector_scores, key=sector_scores.get)
            return best_sector
        
        return 'Other'
    
    def map_section_to_priority(self, section_name: str) -> str:
        """Map original email section to priority sector"""
        section_upper = section_name.upper().strip()
        
        # Direct mapping first
        if section_upper in self.section_to_priority_mapping:
            return self.section_to_priority_mapping[section_upper]
        
        # Partial matching for more complex section names
        for header, priority_sector in self.section_to_priority_mapping.items():
            if header in section_upper or section_upper in header:
                return priority_sector
        
        # If no mapping found, return the original section or 'Other'
        return section_name if section_name != 'Unknown' else 'Other'
    
    def is_priority_sector(self, sector: str) -> bool:
        """Check if a sector is in the priority list"""
        return sector in self.priority_sectors
    
    def _filter_content_by_priority_sections(self, content: str, filter_mode: str = "Priority Sectors Only", selected_sectors: List[str] = None) -> str:
        """Filter content to only include sections that match the filtering criteria"""
        if filter_mode == "Show All Sectors":
            return content  # No filtering
        
        # Get the sections to keep based on filter mode
        if filter_mode == "Priority Sectors Only":
            sections_to_keep = set(self.priority_sectors)
            # Also include mapped section headers that map to priority sectors
            for header, priority in self.section_to_priority_mapping.items():
                if priority in self.priority_sectors:
                    sections_to_keep.add(header.title())
                    sections_to_keep.add(header.upper())
                    sections_to_keep.add(header.lower())
        elif filter_mode == "Custom Selection" and selected_sectors:
            sections_to_keep = set(selected_sectors)
            # Also include mapped section headers
            for header, priority in self.section_to_priority_mapping.items():
                if priority in selected_sectors:
                    sections_to_keep.add(header.title())
                    sections_to_keep.add(header.upper())
                    sections_to_keep.add(header.lower())
        else:
            return content  # Fallback to no filtering
        
        lines = content.split('\n')
        filtered_lines = []
        current_section = None
        include_current_section = True
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this is a section header
            if self._is_section_header(line_stripped):
                current_section = line_stripped
                # Check if we should include this section
                section_mapped = self.map_section_to_priority(current_section)
                include_current_section = (
                    current_section in sections_to_keep or
                    current_section.upper() in sections_to_keep or
                    current_section.lower() in sections_to_keep or
                    current_section.title() in sections_to_keep or
                    section_mapped in sections_to_keep
                )
                
                if include_current_section:
                    filtered_lines.append(line)
            else:
                # Include this line only if we're including the current section
                if include_current_section:
                    filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def filter_deals_by_priority_sectors(self, deals: List[Dict]) -> List[Dict]:
        """Filter deals to only include priority sectors"""
        return [deal for deal in deals if self.is_priority_sector(deal.get('sector', 'Other'))]

    def extract_value(self, text: str) -> str:
        """Extract monetary value from text"""
        value_patterns = [
            r'(EUR|USD|GBP|CNY)\s*([\d,\.]+)\s*([bmk]?)',
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
        """Create a clean professional summary without decorative separators"""
        info = self.extract_key_information(content)
        
        summary_parts = []
        
        summary_parts.append(f"DOCUMENT ANALYSIS SUMMARY")
        summary_parts.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
        summary_parts.append("")
        
        summary_parts.append("CONTENT OVERVIEW")
        summary_parts.append("")
        summary_parts.append(f"• Total Content Lines: {info['total_lines']}")
        summary_parts.append(f"• Identified Sections: {len(info['sections'])}")
        summary_parts.append(f"• Numbered Items/Deals: {len(info['deals'])}")
        summary_parts.append(f"• Monetary References: {len(set(info['monetary_values']))}")
        summary_parts.append("")
        
        if info['sections']:
            summary_parts.append("SECTIONS IDENTIFIED")
            summary_parts.append("")
            for section in info['sections']:
                summary_parts.append(f"• {section}")
            summary_parts.append("")
        
        if info['deals']:
            summary_parts.append("KEY ITEMS")
            summary_parts.append("")
            for deal in info['deals'][:10]:
                title = deal["title"][:100] + "..." if len(deal["title"]) > 100 else deal["title"]
                summary_parts.append(f"• {title}")
            summary_parts.append("")
        
        if info['monetary_values']:
            summary_parts.append("MONETARY VALUES DETECTED")
            summary_parts.append("")
            unique_values = list(set(info['monetary_values']))[:10]
            for value in unique_values:
                summary_parts.append(f"• {value}")
            summary_parts.append("")
        
        summary_parts.append("Generated by Smart Text Formatter")
        
        return '\n'.join(summary_parts)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Smart Text Formatter & M&A Intelligence Processor</h1>
        <p>Transform raw text and M&A data into professionally formatted, readable content</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize processor and database
    if 'processor' not in st.session_state:
        st.session_state.processor = SmartTextProcessor()
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    
    # Sidebar for filtering
    with st.sidebar:
        st.header("🎯 Sector Filtering")
        st.markdown("### Priority Sectors")
        
        # Show priority sectors
        priority_sectors = st.session_state.processor.priority_sectors
        
        # Sector filter options
        filter_mode = st.radio(
            "Filter Mode:",
            ["Show All Sectors", "Priority Sectors Only", "Custom Selection"],
            index=1,  # Default to priority sectors only
            help="Choose how to filter deals and insights by sector"
        )
        
        if filter_mode == "Custom Selection":
            # Allow custom selection of sectors
            all_sectors = priority_sectors + ['Other']
            selected_sectors = st.multiselect(
                "Select Sectors:",
                all_sectors,
                default=priority_sectors,
                help="Choose which sectors to focus on"
            )
        elif filter_mode == "Priority Sectors Only":
            selected_sectors = priority_sectors
        else:
            selected_sectors = None  # Show all
        
        # Store filter settings in session state
        st.session_state.filter_mode = filter_mode
        st.session_state.selected_sectors = selected_sectors
        
        # Display current filter status
        if filter_mode == "Show All Sectors":
            st.info("📊 Showing all sectors")
        elif filter_mode == "Priority Sectors Only":
            st.success(f"🎯 Filtering to {len(priority_sectors)} priority sectors")
        else:
            st.info(f"✅ Custom filter: {len(selected_sectors) if selected_sectors else 0} sectors")
        
        # Priority sectors list
        st.markdown("### 🎯 Your Priority Sectors:")
        for i, sector in enumerate(priority_sectors, 1):
            st.markdown(f"{i}. **{sector}**")
        
        # Show section mappings
        st.markdown("### 📧 Email Section Mappings")
        st.markdown("Email headers like these will be mapped:")
        
        # Show some key mappings
        key_mappings = {
            'AUTOMOTIVE': 'Industrial products',
            'TECHNOLOGY': 'Computer software', 
            'FINANCIAL': 'Financial Services',
            'DEFENSE': 'Defense',
            'CONSUMER': 'Consumer sectors',
            'INDUSTRIAL': 'Industrial products'
        }
        
        for email_header, maps_to in key_mappings.items():
            st.markdown(f"• **{email_header}** → {maps_to}")
        
        with st.expander("📋 View All Mappings"):
            for header, priority in st.session_state.processor.section_to_priority_mapping.items():
                st.markdown(f"• **{header}** → {priority}")
    
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
            height=400,
            help="Paste any raw text content. The system will automatically format it for better readability."
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            format_button = st.button("🚀 Format Text", type="primary", use_container_width=True)
        
        with col_b:
            clear_button = st.button("🗑️ Clear", use_container_width=True)
        
        # Save to database option
        save_to_db = st.checkbox("💾 Save to database for market insights", value=True, help="Save processed data to database for trend analysis")
        
        if clear_button:
            st.rerun()
    
    with col2:
        st.subheader("📊 Formatted Output")
        
        if format_button and text_input:
            with st.spinner("Formatting your text..."):
                # Show filtering status
                filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
                if filter_mode != "Show All Sectors":
                    if filter_mode == "Priority Sectors Only":
                        st.info(f"🎯 Applying priority sector filter: showing only {len(st.session_state.processor.priority_sectors)} priority sectors")
                    else:
                        selected_sectors = st.session_state.get('selected_sectors', [])
                        st.info(f"✅ Applying custom sector filter: showing {len(selected_sectors) if selected_sectors else 0} selected sectors")
                
                # Format the text for both web and email
                formatted_text = st.session_state.processor.format_raw_text(text_input)
                email_formatted_text = st.session_state.processor.format_for_email(text_input)
                
                # Extract key information and deals
                key_info = st.session_state.processor.extract_key_information(text_input)
                deals_data = st.session_state.processor.parse_deals_from_content(text_input)
                
                # Store in session state
                st.session_state.formatted_text = formatted_text
                st.session_state.email_formatted_text = email_formatted_text
                st.session_state.raw_input = text_input
                st.session_state.key_info = key_info
                st.session_state.deals_data = deals_data
                
                # Save to database if option is checked
                if save_to_db:
                    email_id = st.session_state.db_manager.save_email_data(
                        text_input, 
                        email_formatted_text, 
                        deals_data, 
                        key_info
                    )
                    
                    if email_id:
                        st.markdown(f"""
                        <div class="database-info">
                            <strong>✅ Data Saved to Database</strong><br>
                            Email ID: {email_id} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 
                            Deals: {len(key_info['deals'])} | Sections: {len(key_info['sections'])}
                        </div>
                        """, unsafe_allow_html=True)
        
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
                st.info("💡 Clean format with no decorative separators - perfect for email.")
                
                # Display email-formatted text in a copyable text area
                st.text_area(
                    "Copy this text for email:",
                    value=st.session_state.email_formatted_text,
                    height=600,
                    help="Select all (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C) to paste into your email.",
                    key="email_text_area"
                )
                
                col_copy, col_download = st.columns(2) 
                
                with col_copy:
                    if st.button("📋 Copy to Clipboard", use_container_width=True):
                        st.success("Select the text above and use Ctrl+C (or Cmd+C) to copy!")
                
                with col_download:
                    # Download button for email format
                    st.download_button(
                        label="📧 Download Email Format",
                        data=st.session_state.email_formatted_text,
                        file_name=f"email_ready_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        help="Download as a text file that you can copy from or attach to emails.",
                        use_container_width=True
                    )
        else:
            st.info("Ready to format your text. Paste content and click 'Format Text'")
    
    # Additional features
    if 'formatted_text' in st.session_state:
        st.markdown("---")
        
        # Tabs for additional features
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Content Analysis", "📋 Professional Summary", "💾 Export Options", "📈 Market Insights", "🗃️ Database Viewer"])
        
        with tab1:
            st.subheader("📊 Content Analysis")
            
            # Extract and display key information
            key_info = st.session_state.key_info
            
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
                
                # Analyze deal priorities
                deals_data = st.session_state.deals_data
                priority_deals = [deal for deal in deals_data if deal.get('is_priority', False)]
                
                # Show priority deal summary
                if priority_deals:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Deals", len(deals_data))
                    with col2:
                        st.metric("Priority Deals", len(priority_deals), delta=f"{len(priority_deals)/len(deals_data)*100:.1f}%")
                    with col3:
                        priority_sectors_found = set(deal.get('identified_sector', 'Other') for deal in priority_deals)
                        st.metric("Priority Sectors Found", len(priority_sectors_found))
                
                # Filter deals based on current filter setting
                filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
                selected_sectors = st.session_state.get('selected_sectors', st.session_state.processor.priority_sectors)
                
                if filter_mode == "Show All Sectors":
                    filtered_deals = deals_data
                elif filter_mode == "Priority Sectors Only":
                    filtered_deals = priority_deals
                else:  # Custom selection
                    filtered_deals = [deal for deal in deals_data if deal.get('identified_sector', 'Other') in (selected_sectors or [])]
                
                if filtered_deals:
                    st.success(f"🎯 Showing {len(filtered_deals)} deals matching your filter")
                    
                    # Enhanced deals dataframe with priority indicators
                    enhanced_deals = []
                    for deal in filtered_deals:
                        enhanced_deal = {
                            'Priority': '🎯' if deal.get('is_priority', False) else '📄',
                            'Deal #': deal.get('id', ''),
                            'Title': deal.get('title', '')[:80] + '...' if len(deal.get('title', '')) > 80 else deal.get('title', ''),
                            'Section': deal.get('sector', 'Unknown'),
                            'Identified Sector': deal.get('identified_sector', 'Other'),
                            'Geography': deal.get('geography', 'Unknown'),
                            'Value': deal.get('value', 'TBD')
                        }
                        enhanced_deals.append(enhanced_deal)
                    
                    enhanced_df = pd.DataFrame(enhanced_deals)
                    st.dataframe(enhanced_df, use_container_width=True, hide_index=True)
                    
                    # Show sector breakdown for filtered deals
                    if len(filtered_deals) > 1:
                        sector_counts = pd.DataFrame(filtered_deals)['identified_sector'].value_counts()
                        st.markdown("#### Sector Breakdown (Filtered)")
                        fig = px.bar(
                            x=sector_counts.values, 
                            y=sector_counts.index,
                            orientation='h',
                            title="Deals by Identified Sector"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                else:
                    st.warning("No deals found matching your current filter settings")
                
                # Debugging section
                with st.expander("🔍 Sector Identification Debug"):
                    st.markdown("#### How sectors were identified:")
                    debug_data = []
                    for deal in deals_data:
                        debug_data.append({
                            'Deal #': deal.get('id', ''),
                            'Original Section': deal.get('sector', 'Unknown'),
                            'Section Mapped': deal.get('section_mapped_sector', 'Not mapped'),
                            'Content Analysis': st.session_state.processor.identify_sector(deal.get('original_text', '')),
                            'Final Identified': deal.get('identified_sector', 'Not identified'),
                            'Is Priority': '🎯' if deal.get('is_priority', False) else '❌',
                            'Title (First 30 chars)': deal.get('title', '')[:30] + '...' if len(deal.get('title', '')) > 30 else deal.get('title', '')
                        })
                    
                    debug_df = pd.DataFrame(debug_data)
                    st.dataframe(debug_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("#### Your Priority Sectors:")
                    for i, sector in enumerate(st.session_state.processor.priority_sectors, 1):
                        st.markdown(f"{i}. **{sector}**")
                    
                    st.markdown("#### Section Header Mappings:")
                    st.markdown("These email section headers are automatically mapped to your priority sectors:")
                    mapping_data = []
                    for header, priority in st.session_state.processor.section_to_priority_mapping.items():
                        mapping_data.append({
                            'Email Section Header': header,
                            'Maps to Priority Sector': priority
                        })
                    
                    mapping_df = pd.DataFrame(mapping_data)
                    st.dataframe(mapping_df, use_container_width=True, hide_index=True)
                
                # Original deals table (unfiltered)
                if filter_mode != "Show All Sectors":
                    with st.expander("📋 View All Deals (Unfiltered)"):
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
            
            st.text_area("Clean Professional Summary:", summary, height=400, key="summary_text_area")
            
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
        
        with tab4:
            st.subheader("📈 Market Insights")
            
            if st.button("🔄 Load Market Insights", use_container_width=True):
                with st.spinner("Analyzing market data..."):
                    insights = st.session_state.db_manager.get_market_insights()
                    
                    if not insights['overview'].empty:
                        # Overview metrics
                        overview = insights['overview'].iloc[0]
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Emails", int(overview['total_emails']))
                        with col2:
                            st.metric("Total Deals", int(overview['total_deals']))
                        with col3:
                            st.metric("Avg Deals/Email", f"{overview['avg_deals_per_email']:.1f}")
                        with col4:
                            st.metric("Active Days", int(overview['active_days']))
                        
                        # Sector insights
                        if not insights['top_sectors'].empty:
                            st.markdown("### 🏭 Top Sectors by Deal Volume")
                            
                            fig = px.bar(
                                insights['top_sectors'].head(8), 
                                x='deal_count', 
                                y='sector',
                                orientation='h',
                                title="Most Active Sectors"
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Recent activity
                        if not insights['recent_activity'].empty:
                            st.markdown("### 📅 Recent Activity Trends")
                            insights['recent_activity']['processed_date'] = pd.to_datetime(insights['recent_activity']['processed_date'])
                            
                            fig = px.line(
                                insights['recent_activity'].sort_values('processed_date'),
                                x='processed_date',
                                y='total_deals',
                                title="Daily Deal Volume"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Value distribution
                        if not insights['value_distribution'].empty:
                            st.markdown("### 💰 Value Distribution by Currency")
                            st.dataframe(insights['value_distribution'], use_container_width=True)
                    
                    else:
                        st.info("No historical data available yet. Process some emails first!")
        
        with tab5:
            st.subheader("🗃️ Database Viewer")
            st.info("View all data stored in the database from processed emails")
            
            # Load database contents
            if st.button("🔄 Load Database Contents", use_container_width=True):
                with st.spinner("Loading database contents..."):
                    db_contents = st.session_state.db_manager.get_all_database_contents()
                    st.session_state.db_contents = db_contents
            
            if 'db_contents' in st.session_state:
                db_contents = st.session_state.db_contents
                
                # Create sub-tabs for different tables
                db_tab1, db_tab2, db_tab3, db_tab4, db_tab5 = st.tabs(["📧 Emails", "🤝 Deals", "📁 Sections", "💰 Values", "📋 Metadata"])
                
                with db_tab1:
                    st.markdown("### 📧 Processed Emails")
                    if not db_contents['emails'].empty:
                        st.dataframe(db_contents['emails'], use_container_width=True, hide_index=True)
                        
                        # Email management controls
                        st.markdown("#### 🔧 Email Management")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("##### 🔍 View Email Details")
                            email_ids = db_contents['emails']['id'].tolist()
                            selected_email_id = st.selectbox("Select Email ID to view details:", email_ids, key="view_email_select")
                            
                            if st.button("📖 View Full Email Details", key="view_email_btn"):
                                email_details = st.session_state.db_manager.get_email_details(selected_email_id)
                                
                                st.markdown("##### Email Information")
                                st.dataframe(email_details['email_info'], use_container_width=True, hide_index=True)
                                
                                if not email_details['deals'].empty:
                                    st.markdown("##### Associated Deals")
                                    st.dataframe(email_details['deals'], use_container_width=True, hide_index=True)
                                
                                if not email_details['sections'].empty:
                                    st.markdown("##### Associated Sections")  
                                    st.dataframe(email_details['sections'], use_container_width=True, hide_index=True)
                                
                                if not email_details['monetary_values'].empty:
                                    st.markdown("##### Associated Monetary Values")
                                    st.dataframe(email_details['monetary_values'], use_container_width=True, hide_index=True)
                                
                                if not email_details['metadata'].empty:
                                    st.markdown("##### Associated Metadata")
                                    st.dataframe(email_details['metadata'], use_container_width=True, hide_index=True)
                        
                        with col2:
                            st.markdown("##### 🗑️ Delete Email")
                            st.warning("⚠️ This will delete the email and ALL associated data!")
                            
                            delete_email_id = st.selectbox("Select Email ID to delete:", email_ids, key="delete_email_select")
                            
                            # Confirmation checkbox
                            confirm_delete = st.checkbox("I confirm I want to delete this email and all its data", key="confirm_delete_email")
                            
                            if st.button("🗑️ Delete Email", type="secondary", disabled=not confirm_delete, key="delete_email_btn"):
                                if st.session_state.db_manager.delete_email(delete_email_id):
                                    st.success(f"✅ Email {delete_email_id} and all associated data deleted successfully!")
                                    # Refresh the data
                                    st.session_state.db_contents = st.session_state.db_manager.get_all_database_contents()
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete email")
                    else:
                        st.info("No emails found in database")
                
                with db_tab2:
                    st.markdown("### 🤝 All Deals")
                    if not db_contents['deals'].empty:
                        # Apply filtering based on sidebar settings
                        filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
                        selected_sectors = st.session_state.get('selected_sectors', st.session_state.processor.priority_sectors)
                        
                        # Filter deals based on sector
                        all_deals = db_contents['deals']
                        
                        if filter_mode == "Show All Sectors":
                            filtered_deals_db = all_deals
                        elif filter_mode == "Priority Sectors Only":
                            # Use is_priority column if it exists, otherwise fall back to identified_sector
                            if 'is_priority' in all_deals.columns:
                                filtered_deals_db = all_deals[all_deals['is_priority'] == True]
                            elif 'identified_sector' in all_deals.columns:
                                filtered_deals_db = all_deals[all_deals['identified_sector'].isin(st.session_state.processor.priority_sectors)]
                            else:
                                # Legacy fallback for old data
                                filtered_deals_db = all_deals[all_deals['sector'].isin(st.session_state.processor.priority_sectors)]
                        else:  # Custom selection
                            if selected_sectors:
                                if 'identified_sector' in all_deals.columns:
                                    filtered_deals_db = all_deals[all_deals['identified_sector'].isin(selected_sectors)]
                                else:
                                    # Legacy fallback
                                    filtered_deals_db = all_deals[all_deals['sector'].isin(selected_sectors)]
                            else:
                                filtered_deals_db = pd.DataFrame()  # Empty if no sectors selected
                        
                        # Show filtering info
                        if len(filtered_deals_db) != len(all_deals):
                            st.info(f"🎯 Filtered view: {len(filtered_deals_db)} of {len(all_deals)} deals shown (based on sidebar filter)")
                        
                        if not filtered_deals_db.empty:
                            # Add priority indicators
                            display_deals = filtered_deals_db.copy()
                            if 'is_priority' in display_deals.columns:
                                display_deals['Priority'] = display_deals['is_priority'].apply(
                                    lambda x: '🎯' if x else '📄'
                                )
                            elif 'identified_sector' in display_deals.columns:
                                display_deals['Priority'] = display_deals['identified_sector'].apply(
                                    lambda x: '🎯' if x in st.session_state.processor.priority_sectors else '📄'
                                )
                            else:
                                # Legacy fallback
                                display_deals['Priority'] = display_deals['sector'].apply(
                                    lambda x: '🎯' if x in st.session_state.processor.priority_sectors else '📄'
                                )
                            
                            # Reorder columns to show priority first
                            cols = ['Priority'] + [col for col in display_deals.columns if col != 'Priority']
                            display_deals = display_deals[cols]
                            
                            st.dataframe(display_deals, use_container_width=True, hide_index=True)
                            
                            # Quick stats for filtered deals
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Filtered Deals", len(filtered_deals_db))
                            with col2:
                                if 'is_priority' in filtered_deals_db.columns:
                                    priority_count = len(filtered_deals_db[filtered_deals_db['is_priority'] == True])
                                elif 'identified_sector' in filtered_deals_db.columns:
                                    priority_count = len(filtered_deals_db[filtered_deals_db['identified_sector'].isin(st.session_state.processor.priority_sectors)])
                                else:
                                    priority_count = len(filtered_deals_db[filtered_deals_db['sector'].isin(st.session_state.processor.priority_sectors)])
                                st.metric("Priority Deals", priority_count)
                            with col3:
                                top_sector = filtered_deals_db['sector'].mode().iloc[0] if len(filtered_deals_db) > 0 else 'N/A'
                                st.metric("Top Sector", top_sector)
                            with col4:
                                top_geo = filtered_deals_db['geography'].mode().iloc[0] if len(filtered_deals_db) > 0 else 'N/A'
                                st.metric("Top Geography", top_geo)
                            
                            # Priority sector breakdown
                            if 'is_priority' in filtered_deals_db.columns:
                                priority_deals_in_view = filtered_deals_db[filtered_deals_db['is_priority'] == True]
                                sector_col = 'identified_sector' if 'identified_sector' in priority_deals_in_view.columns else 'sector'
                            elif 'identified_sector' in filtered_deals_db.columns:
                                priority_deals_in_view = filtered_deals_db[filtered_deals_db['identified_sector'].isin(st.session_state.processor.priority_sectors)]
                                sector_col = 'identified_sector'
                            else:
                                priority_deals_in_view = filtered_deals_db[filtered_deals_db['sector'].isin(st.session_state.processor.priority_sectors)]
                                sector_col = 'sector'
                            
                            if not priority_deals_in_view.empty:
                                st.markdown("#### 🎯 Priority Sector Breakdown")
                                sector_counts = priority_deals_in_view[sector_col].value_counts()
                                fig = px.bar(
                                    x=sector_counts.values,
                                    y=sector_counts.index,
                                    orientation='h',
                                    title="Priority Deals by Sector",
                                    color_discrete_sequence=['#2E8B57']  # Green color for priority
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        
                        else:
                            st.warning("No deals found matching your current filter settings")
                            
                        # Show unfiltered data in expander if filtering is active
                        if filter_mode != "Show All Sectors":
                            with st.expander("📋 View All Deals (Unfiltered)"):
                                st.dataframe(all_deals, use_container_width=True, hide_index=True)
                        
                        # Deal deletion
                        st.markdown("#### 🗑️ Delete Individual Deal")
                        st.warning("⚠️ This will delete the selected deal only!")
                        
                        deal_ids = db_contents['deals']['id'].tolist()
                        deal_titles = db_contents['deals']['title'].tolist()
                        deal_options = [f"ID {deal_id}: {title[:50]}..." if len(title) > 50 else f"ID {deal_id}: {title}" 
                                      for deal_id, title in zip(deal_ids, deal_titles)]
                        
                        selected_deal_option = st.selectbox("Select Deal to delete:", deal_options, key="delete_deal_select")
                        selected_deal_id = int(selected_deal_option.split(":")[0].replace("ID ", ""))
                        
                        confirm_delete_deal = st.checkbox("I confirm I want to delete this deal", key="confirm_delete_deal")
                        
                        if st.button("🗑️ Delete Deal", type="secondary", disabled=not confirm_delete_deal, key="delete_deal_btn"):
                            if st.session_state.db_manager.delete_deal(selected_deal_id):
                                st.success(f"✅ Deal {selected_deal_id} deleted successfully!")
                                # Refresh the data
                                st.session_state.db_contents = st.session_state.db_manager.get_all_database_contents()
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete deal")
                    else:
                        st.info("No deals found in database")
                
                with db_tab3:
                    st.markdown("### 📁 Sections")
                    if not db_contents['sections'].empty:
                        st.dataframe(db_contents['sections'], use_container_width=True, hide_index=True)
                        
                        # Section summary
                        section_summary = db_contents['sections'].groupby('section_name')['deal_count'].sum().reset_index()
                        section_summary = section_summary.sort_values('deal_count', ascending=False)
                        
                        st.markdown("#### Section Deal Counts")
                        fig = px.bar(section_summary, x='section_name', y='deal_count', 
                                   title="Total Deals by Section")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No sections found in database")
                
                with db_tab4:
                    st.markdown("### 💰 Monetary Values")
                    if not db_contents['monetary_values'].empty:
                        st.dataframe(db_contents['monetary_values'], use_container_width=True, hide_index=True)
                        
                        # Currency distribution
                        currency_dist = db_contents['monetary_values']['currency'].value_counts().reset_index()
                        currency_dist.columns = ['currency', 'count']
                        
                        if not currency_dist.empty:
                            st.markdown("#### Currency Distribution")
                            fig = px.pie(currency_dist, values='count', names='currency', 
                                       title="Distribution of Currencies")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No monetary values found in database")
                
                with db_tab5:
                    st.markdown("### 📋 Metadata")
                    if not db_contents['metadata'].empty:
                        st.dataframe(db_contents['metadata'], use_container_width=True, hide_index=True)
                        
                        # Metadata keys distribution
                        key_dist = db_contents['metadata']['key'].value_counts().reset_index()
                        key_dist.columns = ['key', 'count']
                        
                        if not key_dist.empty:
                            st.markdown("#### Metadata Keys Distribution")
                            fig = px.bar(key_dist, x='key', y='count', 
                                       title="Frequency of Metadata Keys")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No metadata found in database")
                
                # Database statistics
                st.markdown("---")
                st.markdown("### 📊 Database Statistics")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Total Emails", len(db_contents['emails']))
                with col2:
                    st.metric("Total Deals", len(db_contents['deals']))
                with col3:
                    st.metric("Total Sections", len(db_contents['sections']))
                with col4:
                    st.metric("Total Values", len(db_contents['monetary_values']))
                with col5:
                    st.metric("Total Metadata", len(db_contents['metadata']))
                
                # Database Management
                st.markdown("---")
                st.markdown("### ⚙️ Database Management")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🔄 Refresh Database")
                    if st.button("🔄 Refresh All Data", use_container_width=True):
                        with st.spinner("Refreshing database contents..."):
                            st.session_state.db_contents = st.session_state.db_manager.get_all_database_contents()
                            st.success("✅ Database contents refreshed!")
                            st.rerun()
                
                with col2:
                    st.markdown("#### 🚨 Clear All Data")
                    st.error("⚠️ DANGER ZONE: This will delete ALL data from the database!")
                    
                    # Double confirmation for nuclear option
                    confirm_nuclear_1 = st.checkbox("I understand this will delete ALL emails and data", key="nuclear_confirm_1")
                    confirm_nuclear_2 = st.checkbox("I really want to delete everything", key="nuclear_confirm_2")
                    
                    nuclear_enabled = confirm_nuclear_1 and confirm_nuclear_2
                    
                    if st.button("🚨 DELETE ALL DATA", type="secondary", disabled=not nuclear_enabled, key="nuclear_delete_btn"):
                        if st.session_state.db_manager.delete_all_data():
                            st.success("✅ All database data has been deleted!")
                            # Clear session state
                            if 'db_contents' in st.session_state:
                                del st.session_state.db_contents
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete all data")
            
            else:
                st.info("Click 'Load Database Contents' to view stored data")

if __name__ == "__main__":
    main()