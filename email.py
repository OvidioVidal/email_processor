import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any, Tuple
import plotly.express as px
from datetime import datetime
import json
from dataclasses import dataclass
from functools import lru_cache
import hashlib

# Configuration
@dataclass
class MAConfig:
    base_currency: str = "USD"
    confidence_threshold: float = 0.7
    cache_ttl: int = 3600
    enable_real_time_data: bool = True
    big4_standards: bool = True

CONFIG = MAConfig()

# Page configuration
st.set_page_config(
    page_title="Enhanced M&A Intelligence Processor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
    }
    
    .deal-card {
        background: white;
        padding: 1.8rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #e74c3c;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .deal-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
    }
    
    .confidence-high {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .confidence-medium {
        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .confidence-low {
        background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .financial-highlight {
        background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .sector-badge {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-right: 0.5rem;
    }
    
    .risk-indicator {
        padding: 0.2rem 0.6rem;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .risk-low { background: #d5f4e6; color: #27ae60; }
    .risk-medium { background: #fef9e7; color: #f39c12; }
    .risk-high { background: #fadbd8; color: #e74c3c; }
</style>
""", unsafe_allow_html=True)

class EnhancedMAProcessor:
    def __init__(self):
        # Enhanced sector taxonomy with hierarchical classification
        self.sector_taxonomy = {
            'technology': {
                'keywords': ['tech', 'software', 'AI', 'digital', 'data', 'cyber', 'SaaS', 'IT', 'cloud', 'app'],
                'subsectors': {
                    'saas': ['software as a service', 'subscription', 'cloud platform'],
                    'fintech': ['financial technology', 'payments', 'digital banking', 'blockchain'],
                    'ai_ml': ['artificial intelligence', 'machine learning', 'neural network'],
                    'cybersecurity': ['security', 'cyber', 'data protection', 'firewall'],
                    'medtech': ['health tech', 'digital health', 'telemedicine']
                }
            },
            'financial': {
                'keywords': ['bank', 'finance', 'capital', 'investment', 'insurance', 'fund', 'fintech'],
                'subsectors': {
                    'banking': ['commercial bank', 'investment bank', 'retail bank'],
                    'insurance': ['life insurance', 'property insurance', 'reinsurance'],
                    'asset_management': ['fund management', 'private equity', 'hedge fund'],
                    'payments': ['payment processing', 'mobile payments', 'digital wallet']
                }
            },
            'healthcare': {
                'keywords': ['health', 'medical', 'pharma', 'biotech', 'hospital', 'drug', 'medicine'],
                'subsectors': {
                    'pharmaceutical': ['drug development', 'biotech', 'clinical trials'],
                    'medical_devices': ['medical device', 'diagnostics', 'imaging'],
                    'healthcare_services': ['hospital', 'clinic', 'telehealth']
                }
            },
            'industrial': {
                'keywords': ['construction', 'industrial', 'manufacturing', 'engineering', 'chemical', 'steel', 'machinery'],
                'subsectors': {
                    'chemicals': ['specialty chemicals', 'petrochemicals', 'fertilizers'],
                    'construction': ['construction services', 'building materials', 'infrastructure'],
                    'machinery': ['industrial equipment', 'automation', 'robotics']
                }
            },
            'energy': {
                'keywords': ['energy', 'oil', 'gas', 'renewable', 'power', 'solar', 'wind', 'nuclear'],
                'subsectors': {
                    'renewable': ['solar', 'wind', 'hydroelectric', 'geothermal'],
                    'oil_gas': ['petroleum', 'natural gas', 'exploration', 'refining'],
                    'utilities': ['electric utility', 'water utility', 'gas distribution']
                }
            },
            'consumer': {
                'keywords': ['retail', 'consumer', 'food', 'beauty', 'fashion', 'beverage', 'brand'],
                'subsectors': {
                    'retail': ['e-commerce', 'department store', 'specialty retail'],
                    'food_beverage': ['food processing', 'restaurants', 'beverages'],
                    'personal_care': ['cosmetics', 'personal care', 'luxury goods']
                }
            },
            'automotive': {
                'keywords': ['auto', 'car', 'vehicle', 'motor', 'automotive', 'electric vehicle', 'ev'],
                'subsectors': {
                    'oem': ['car manufacturer', 'auto assembly', 'vehicle production'],
                    'suppliers': ['auto parts', 'automotive components', 'tier 1 supplier'],
                    'ev_battery': ['electric vehicle', 'battery technology', 'charging']
                }
            },
            'real_estate': {
                'keywords': ['real estate', 'property', 'reit', 'building', 'development', 'construction'],
                'subsectors': {
                    'commercial': ['office buildings', 'retail properties', 'industrial real estate'],
                    'residential': ['residential development', 'housing', 'apartments'],
                    'reits': ['real estate investment trust', 'property fund']
                }
            },
            'materials': {
                'keywords': ['materials', 'mining', 'metals', 'forestry', 'paper', 'packaging'],
                'subsectors': {
                    'metals_mining': ['iron ore', 'copper', 'gold mining', 'steel production'],
                    'forest_products': ['lumber', 'pulp', 'paper products', 'forestry'],
                    'packaging': ['packaging materials', 'containers', 'flexible packaging']
                }
            }
        }
        
        # Enhanced geography mapping
        self.geo_taxonomy = {
            'uk': {
                'keywords': ['uk', 'britain', 'london', 'england', 'scotland', 'wales', 'british'],
                'major_cities': ['london', 'manchester', 'birmingham', 'edinburgh']
            },
            'germany': {
                'keywords': ['german', 'germany', 'berlin', 'munich', 'deutsche', 'frankfurt'],
                'major_cities': ['berlin', 'munich', 'frankfurt', 'hamburg', 'cologne']
            },
            'france': {
                'keywords': ['france', 'french', 'paris', 'lyon', 'marseille'],
                'major_cities': ['paris', 'lyon', 'marseille', 'toulouse']
            },
            'europe': {
                'keywords': ['europe', 'european', 'eu', 'eurozone'],
                'regions': ['western europe', 'northern europe', 'southern europe']
            },
            'usa': {
                'keywords': ['us', 'usa', 'america', 'american', 'new york', 'california', 'texas'],
                'major_cities': ['new york', 'los angeles', 'chicago', 'houston', 'boston']
            },
            'china': {
                'keywords': ['china', 'chinese', 'beijing', 'shanghai', 'shenzhen'],
                'major_cities': ['beijing', 'shanghai', 'shenzhen', 'guangzhou']
            },
            'asia': {
                'keywords': ['asia', 'asian', 'japan', 'singapore', 'hong kong', 'south korea'],
                'regions': ['east asia', 'southeast asia', 'south asia']
            }
        }
        
        # Professional confidence framework
        self.confidence_framework = {
            'confirmed': {
                'weight': 0.95,
                'indicators': ['press release', 'sec filing', 'signed agreement', 'completed', 'closed', 'finalized'],
                'exclusions': ['rumor', 'speculation', 'potential', 'considering']
            },
            'strong_evidence': {
                'weight': 0.8,
                'indicators': ['talks', 'discussions', 'due diligence', 'board approval', 'agreement in principle', 'sources familiar'],
                'exclusions': ['denied', 'rejected', 'canceled']
            },
            'developing': {
                'weight': 0.6,
                'indicators': ['considering', 'exploring', 'evaluating', 'seeking', 'planning'],
                'exclusions': ['ruled out', 'abandoned']
            },
            'rumored': {
                'weight': 0.4,
                'indicators': ['rumor', 'speculation', 'sources said', 'reportedly', 'allegedly'],
                'exclusions': ['confirmed', 'official', 'announced']
            }
        }

    @lru_cache(maxsize=1000)
    def extract_sector_enhanced(self, title: str, content: str = "") -> Tuple[str, str, float]:
        """Enhanced sector extraction with subsector identification and confidence scoring"""
        text = (title + " " + content).lower()
        best_match = None
        best_score = 0
        best_subsector = None
        
        for sector, data in self.sector_taxonomy.items():
            score = 0
            matched_subsector = None
            
            # Check main keywords
            for keyword in data['keywords']:
                if keyword in text:
                    score += 1
            
            # Check subsector keywords (higher weight)
            for subsector, subsector_keywords in data['subsectors'].items():
                for keyword in subsector_keywords:
                    if keyword in text:
                        score += 2
                        matched_subsector = subsector
            
            # Normalize score
            total_keywords = len(data['keywords']) + sum(len(sk) for sk in data['subsectors'].values())
            normalized_score = score / total_keywords if total_keywords > 0 else 0
            
            if normalized_score > best_score:
                best_score = normalized_score
                best_match = sector
                best_subsector = matched_subsector
        
        if best_match and best_score >= CONFIG.confidence_threshold:
            sector_name = best_match.replace('_', ' ').title()
            subsector_name = best_subsector.replace('_', ' ').title() if best_subsector else ""
            return sector_name, subsector_name, best_score
        
        return 'Other', '', 0.0

    def extract_geography_enhanced(self, title: str, content: str = "") -> Tuple[str, List[str], float]:
        """Enhanced geography extraction with multiple locations and confidence"""
        text = (title + " " + content).lower()
        locations = []
        confidence_scores = []
        
        for geo, data in self.geo_taxonomy.items():
            score = 0
            for keyword in data['keywords']:
                if keyword in text:
                    score += 1
            
            # Check for specific cities (higher confidence)
            if 'major_cities' in data:
                for city in data['major_cities']:
                    if city in text:
                        score += 2
            
            if score > 0:
                normalized_score = min(score / len(data['keywords']), 1.0)
                locations.append(geo.upper())
                confidence_scores.append(normalized_score)
        
        if locations:
            # Return primary location (highest confidence) and all detected locations
            max_idx = confidence_scores.index(max(confidence_scores))
            primary_location = locations[max_idx]
            return primary_location, locations, confidence_scores[max_idx]
        
        return 'Global', [], 0.0

    def extract_financial_data_enhanced(self, text: str) -> Dict[str, Any]:
        """Enhanced financial data extraction with multiple value types"""
        financial_data = {
            'enterprise_value': None,
            'equity_value': None,
            'transaction_value': None,
            'revenue_multiple': None,
            'currency': None,
            'value_text': '',
            'confidence': 0.0
        }
        
        # Enhanced value patterns
        value_patterns = [
            # Enterprise value patterns
            r'enterprise value.*?([A-Z]{3})\s*([\d,\.]+)\s*([bmk]?illion)?',
            r'ev.*?([A-Z]{3})\s*([\d,\.]+)\s*([bmk]?illion)?',
            
            # Transaction value patterns
            r'transaction value.*?([A-Z]{3})\s*([\d,\.]+)\s*([bmk]?illion)?',
            r'deal value.*?([A-Z]{3})\s*([\d,\.]+)\s*([bmk]?illion)?',
            
            # General currency patterns
            r'([A-Z]{3})\s*([\d,\.]+)\s*([bmk]?illion)?',
            r'\$\s*([\d,\.]+)\s*([bmk]?illion)?',
            r'£\s*([\d,\.]+)\s*([bmk]?illion)?',
            r'€\s*([\d,\.]+)\s*([bmk]?illion)?'
        ]
        
        text_lower = text.lower()
        
        for pattern in value_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) >= 2:
                        if match.group(1) and match.group(1).upper() in ['USD', 'EUR', 'GBP']:
                            currency = match.group(1).upper()
                        elif '$' in match.group(0):
                            currency = 'USD'
                        elif '£' in match.group(0):
                            currency = 'GBP'
                        elif '€' in match.group(0):
                            currency = 'EUR'
                        else:
                            currency = 'USD'  # Default
                        
                        value_str = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                        value = float(value_str.replace(',', ''))
                        
                        # Handle multipliers
                        if len(match.groups()) >= 3 and match.group(3):
                            multiplier_text = match.group(3).lower()
                            if 'billion' in multiplier_text or 'b' in multiplier_text:
                                value *= 1000
                            # Million is base unit
                        
                        # Classify value type based on context
                        context = text_lower[max(0, match.start()-50):match.end()+50]
                        
                        if any(term in context for term in ['enterprise value', 'ev']):
                            financial_data['enterprise_value'] = value
                            financial_data['currency'] = currency
                        elif any(term in context for term in ['equity value', 'market cap']):
                            financial_data['equity_value'] = value
                            financial_data['currency'] = currency
                        else:
                            financial_data['transaction_value'] = value
                            financial_data['currency'] = currency
                        
                        financial_data['value_text'] = match.group(0)
                        financial_data['confidence'] = 0.8
                        break
                except (ValueError, IndexError):
                    continue
        
        return financial_data

    def assign_confidence_score(self, deal: Dict) -> Tuple[str, float, List[str]]:
        """Professional confidence scoring based on Big 4 standards"""
        text = (deal['title'] + ' ' + deal.get('content', '')).lower()
        confidence_indicators = []
        
        for grade, framework in self.confidence_framework.items():
            score = 0
            matched_indicators = []
            
            # Check positive indicators
            for indicator in framework['indicators']:
                if indicator in text:
                    score += 1
                    matched_indicators.append(indicator)
            
            # Check exclusions (negative indicators)
            exclusion_penalty = 0
            for exclusion in framework['exclusions']:
                if exclusion in text:
                    exclusion_penalty += 1
            
            # Calculate final score
            final_score = max(0, score - exclusion_penalty)
            
            if final_score > 0:
                confidence_score = min(framework['weight'] * (final_score / len(framework['indicators'])), 1.0)
                return grade.replace('_', ' ').title(), confidence_score, matched_indicators
        
        return 'Pending Assessment', 0.3, []

    def calculate_deal_size_category(self, financial_data: Dict) -> str:
        """Calculate deal size category based on financial data"""
        # Get the highest value available
        values = [
            financial_data.get('enterprise_value'),
            financial_data.get('equity_value'),
            financial_data.get('transaction_value')
        ]
        
        max_value = max([v for v in values if v is not None], default=0)
        
        if max_value >= 1000:  # 1B+
            return 'Mega Deal (>$1B)'
        elif max_value >= 300:   # 300M+
            return 'Large Cap ($300M-$1B)'
        elif max_value >= 60:    # 60M+
            return 'Mid Cap ($60M-$300M)'
        elif max_value >= 10:    # 10M+
            return 'Small Cap ($10M-$60M)'
        elif max_value > 0:      # Any value
            return 'Micro Cap (<$10M)'
        else:
            return 'Value TBD'

    def assess_strategic_rationale(self, deal: Dict) -> Dict[str, Any]:
        """Assess strategic rationale and business logic"""
        text = (deal['title'] + ' ' + deal.get('content', '')).lower()
        
        rationale_indicators = {
            'market_expansion': ['expand', 'expansion', 'new market', 'geographic', 'international'],
            'scale_economics': ['consolidate', 'consolidation', 'scale', 'synergies', 'cost savings'],
            'technology_acquisition': ['technology', 'digital', 'innovation', 'capabilities', 'platform'],
            'vertical_integration': ['supply chain', 'vertical', 'upstream', 'downstream', 'integration'],
            'portfolio_optimization': ['divest', 'spin-off', 'carve-out', 'focus', 'core business'],
            'talent_acquisition': ['team', 'talent', 'expertise', 'capabilities', 'know-how']
        }
        
        identified_rationales = {}
        for rationale, keywords in rationale_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                identified_rationales[rationale] = score / len(keywords)
        
        # Get primary rationale
        primary_rationale = max(identified_rationales.items(), key=lambda x: x[1])[0] if identified_rationales else 'Strategic Expansion'
        
        return {
            'primary_rationale': primary_rationale.replace('_', ' ').title(),
            'all_rationales': identified_rationales,
            'strategic_logic_score': max(identified_rationales.values()) if identified_rationales else 0.5
        }

    def parse_email_content_enhanced(self, content: str) -> List[Dict[str, Any]]:
        """Enhanced parsing with professional intelligence standards"""
        deals = []
        lines = content.split('\n')
        current_deal = None
        current_sector = "Other"
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Enhanced sector header detection
            if (len(line.split()) <= 3 and 
                line[0].isupper() and 
                not re.match(r'^\d+\.', line) and
                not line.startswith('*') and
                not any(char in line for char in ['(', ')', '-', '€', '$', '£', 'Size:', 'Grade:', 'Source:'])):
                current_sector = line.title()
                continue
                
            # Deal header detection
            deal_match = re.match(r'^(\d+)\.\s*(.+)', line)
            if deal_match:
                # Save previous deal
                if current_deal:
                    deals.append(self._finalize_deal(current_deal))
                
                # Start new deal
                deal_id = deal_match.group(1)
                title = deal_match.group(2)
                
                current_deal = {
                    'id': deal_id,
                    'title': title,
                    'sector_header': current_sector,
                    'details': [],
                    'content': '',
                    'metadata': {},
                    'original_text': title
                }
                
                # Collect deal content
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    
                    # Stop conditions
                    if re.match(r'^\d+\.', next_line):
                        break
                    if (len(next_line.split()) <= 3 and 
                        next_line[0].isupper() and 
                        not next_line.startswith('*') and
                        not any(char in next_line for char in ['(', ')', '-', '€', '$', '£'])):
                        break
                    
                    current_deal['original_text'] += '\n' + next_line
                    
                    # Parse different types of content
                    if next_line.startswith('*'):
                        current_deal['details'].append(next_line[1:].strip())
                    elif ':' in next_line and any(keyword in next_line.lower() for keyword in 
                                                ['size', 'grade', 'source', 'value', 'stake', 'intelligence']):
                        key, value = next_line.split(':', 1)
                        current_deal['metadata'][key.strip().lower()] = value.strip()
                    elif len(next_line) > 30:
                        current_deal['content'] += '\n' + next_line
                    
                    j += 1
        
        # Don't forget the last deal
        if current_deal:
            deals.append(self._finalize_deal(current_deal))
        
        return deals

    def _finalize_deal(self, deal: Dict) -> Dict[str, Any]:
        """Finalize deal with enhanced analysis"""
        # Enhanced sector classification
        sector, subsector, sector_confidence = self.extract_sector_enhanced(
            deal['title'], deal.get('content', '')
        )
        
        # Use sector header if available and confidence is low
        if sector == 'Other' and deal.get('sector_header') != 'Other':
            sector = deal['sector_header']
            subsector = ''
            sector_confidence = 0.9
        
        # Enhanced geography analysis
        primary_geo, all_geos, geo_confidence = self.extract_geography_enhanced(
            deal['title'], deal.get('content', '')
        )
        
        # Financial analysis
        financial_data = self.extract_financial_data_enhanced(deal['original_text'])
        
        # Confidence scoring
        confidence_grade, confidence_score, confidence_indicators = self.assign_confidence_score(deal)
        
        # Strategic analysis
        strategic_analysis = self.assess_strategic_rationale(deal)
        
        # Deal size classification
        size_category = self.calculate_deal_size_category(financial_data)
        
        # Create finalized deal
        finalized_deal = {
            'id': deal['id'],
            'title': deal['title'],
            'sector': sector,
            'subsector': subsector,
            'sector_confidence': sector_confidence,
            'geography': primary_geo,
            'all_geographies': all_geos,
            'geography_confidence': geo_confidence,
            'details': deal['details'],
            'content': deal.get('content', ''),
            'summary': self._generate_deal_summary(deal),
            'financial_data': financial_data,
            'value_display': self._format_value_display(financial_data),
            'size_category': size_category,
            'confidence_grade': confidence_grade,
            'confidence_score': confidence_score,
            'confidence_indicators': confidence_indicators,
            'strategic_analysis': strategic_analysis,
            'metadata': deal.get('metadata', {}),
            'risk_assessment': self._assess_deal_risks(deal, confidence_score),
            'original_text': deal['original_text'],
            'processed_timestamp': datetime.now().isoformat(),
            'intelligence_id': self._generate_intelligence_id(deal)
        }
        
        return finalized_deal

    def _generate_deal_summary(self, deal: Dict) -> str:
        """Generate professional deal summary"""
        if deal.get('content'):
            # Extract first meaningful sentence
            sentences = deal['content'].split('.')
            first_sentence = sentences[0].strip() if sentences else ''
            return first_sentence[:200] + ('...' if len(first_sentence) > 200 else '')
        elif deal.get('details'):
            return ' | '.join(deal['details'][:2])
        else:
            return f"M&A transaction involving {deal['title'].split(' ')[0] if deal['title'] else 'target company'}"

    def _format_value_display(self, financial_data: Dict) -> str:
        """Format value for display"""
        if financial_data.get('enterprise_value'):
            return f"{financial_data['currency']} {financial_data['enterprise_value']:.0f}M (EV)"
        elif financial_data.get('equity_value'):
            return f"{financial_data['currency']} {financial_data['equity_value']:.0f}M (Equity)"
        elif financial_data.get('transaction_value'):
            return f"{financial_data['currency']} {financial_data['transaction_value']:.0f}M"
        else:
            return 'Value TBD'

    def _assess_deal_risks(self, deal: Dict, confidence_score: float) -> Dict[str, Any]:
        """Assess deal-specific risks"""
        text = (deal['title'] + ' ' + deal.get('content', '')).lower()
        
        risk_factors = {
            'regulatory': ['antitrust', 'regulatory', 'approval', 'competition', 'merger control'],
            'execution': ['complex', 'integration', 'cultural', 'systems', 'operational'],
            'market': ['volatility', 'economic', 'downturn', 'competitive', 'disruption'],
            'financial': ['leverage', 'debt', 'covenant', 'liquidity', 'valuation']
        }
        
        identified_risks = {}
        for risk_type, keywords in risk_factors.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                identified_risks[risk_type] = min(score / len(keywords), 1.0)
        
        # Overall risk score
        base_risk = 1.0 - confidence_score  # Lower confidence = higher risk
        specific_risks = sum(identified_risks.values()) * 0.2  # Additional risk from identified factors
        overall_risk = min(base_risk + specific_risks, 1.0)
        
        risk_level = 'High' if overall_risk > 0.7 else 'Medium' if overall_risk > 0.4 else 'Low'
        
        return {
            'overall_risk_score': overall_risk,
            'risk_level': risk_level,
            'risk_factors': identified_risks,
            'primary_risk': max(identified_risks.items(), key=lambda x: x[1])[0] if identified_risks else 'execution'
        }

    def _generate_intelligence_id(self, deal: Dict) -> str:
        """Generate unique intelligence ID"""
        content_hash = hashlib.md5(deal['title'].encode()).hexdigest()[:6]
        return f"intel-{deal['id']}-{content_hash}"

    def apply_filters_enhanced(self, deals: List[Dict], filters: Dict) -> List[Dict]:
        """Enhanced filtering with multiple criteria"""
        filtered_deals = []
        
        for deal in deals:
            # Sector filter
            if filters.get('sector') != 'All Sectors':
                if deal['sector'] != filters['sector'] and deal['subsector'] != filters['sector']:
                    continue
            
            # Geography filter
            if filters.get('geography') != 'All Regions':
                if (deal['geography'] != filters['geography'].upper() and 
                    filters['geography'].upper() not in deal.get('all_geographies', [])):
                    continue
            
            # Value filter
            if filters.get('min_value'):
                min_value = filters['min_value']
                deal_value = max([
                    deal['financial_data'].get('enterprise_value', 0),
                    deal['financial_data'].get('equity_value', 0),
                    deal['financial_data'].get('transaction_value', 0)
                ])
                if deal_value < min_value:
                    continue
            
            # Confidence filter
            if filters.get('min_confidence'):
                if deal['confidence_score'] < filters['min_confidence']:
                    continue
            
            # Risk filter
            if filters.get('max_risk'):
                if deal['risk_assessment']['overall_risk_score'] > filters['max_risk']:
                    continue
            
            filtered_deals.append(deal)
        
        return filtered_deals

    def generate_market_intelligence_report(self, deals: List[Dict]) -> str:
        """Generate comprehensive market intelligence report"""
        if not deals:
            return "No deals available for analysis."
        
        # Calculate market metrics
        total_deals = len(deals)
        high_confidence_deals = [d for d in deals if d['confidence_score'] > 0.7]
        large_deals = [d for d in deals if any(v and v > 300 for v in [
            d['financial_data'].get('enterprise_value'),
            d['financial_data'].get('equity_value'),
            d['financial_data'].get('transaction_value')
        ])]
        
        # Sector analysis
        sector_distribution = {}
        for deal in deals:
            sector = deal['sector']
            if sector in sector_distribution:
                sector_distribution[sector]['count'] += 1
                sector_distribution[sector]['confidence'] += deal['confidence_score']
            else:
                sector_distribution[sector] = {
                    'count': 1,
                    'confidence': deal['confidence_score'],
                    'deals': []
                }
            sector_distribution[sector]['deals'].append(deal)
        
        # Calculate average confidence by sector
        for sector_data in sector_distribution.values():
            sector_data['avg_confidence'] = sector_data['confidence'] / sector_data['count']
        
        # Top sectors by activity
        top_sectors = sorted(sector_distribution.items(), 
                           key=lambda x: (x[1]['count'], x[1]['avg_confidence']), 
                           reverse=True)[:5]
        
        # Geographic analysis
        geo_distribution = {}
        for deal in deals:
            for geo in deal.get('all_geographies', [deal['geography']]):
                geo_distribution[geo] = geo_distribution.get(geo, 0) + 1
        
        # Strategic themes analysis
        strategic_themes = {}
        for deal in deals:
            primary_rationale = deal['strategic_analysis']['primary_rationale']
            strategic_themes[primary_rationale] = strategic_themes.get(primary_rationale, 0) + 1
        
        # Risk analysis
        risk_distribution = {'Low': 0, 'Medium': 0, 'High': 0}
        for deal in deals:
            risk_level = deal['risk_assessment']['risk_level']
            risk_distribution[risk_level] += 1
        
        # Generate report
        report = f"""# 🎯 ENHANCED M&A INTELLIGENCE REPORT
**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}
**Classification:** CONFIDENTIAL - PROFESSIONAL USE ONLY

## 📊 EXECUTIVE DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Market Activity Metrics
- **Total Transactions Tracked:** {total_deals}
- **High-Confidence Deals:** {len(high_confidence_deals)} ({len(high_confidence_deals)/total_deals*100:.1f}%)
- **Large-Scale Transactions:** {len(large_deals)} (>$300M category)
- **Average Confidence Score:** {sum(d['confidence_score'] for d in deals)/total_deals:.2f}
- **Market Activity Level:** {'Very High' if total_deals > 20 else 'High' if total_deals > 15 else 'Moderate' if total_deals > 10 else 'Standard'}

### Risk Assessment Overview
- **Low Risk Deals:** {risk_distribution['Low']} ({risk_distribution['Low']/total_deals*100:.1f}%)
- **Medium Risk Deals:** {risk_distribution['Medium']} ({risk_distribution['Medium']/total_deals*100:.1f}%)
- **High Risk Deals:** {risk_distribution['High']} ({risk_distribution['High']/total_deals*100:.1f}%)

## 🏭 SECTOR INTELLIGENCE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Top Sectors by Activity
{chr(10).join([f"**{i+1}. {sector}** - {data['count']} deals (Avg Confidence: {data['avg_confidence']:.2f})" 
              for i, (sector, data) in enumerate(top_sectors)])}

### Detailed Sector Analysis
{chr(10).join([f"""
#### {sector.upper()} SECTOR ({data['count']} deals)
- **Market Share:** {data['count']/total_deals*100:.1f}% of total activity
- **Confidence Level:** {data['avg_confidence']:.2f} ({'High' if data['avg_confidence'] > 0.7 else 'Medium' if data['avg_confidence'] > 0.5 else 'Developing'})
- **Key Transactions:**
{chr(10).join([f"  • Deal #{deal['id']}: {deal['title'][:80]}{'...' if len(deal['title']) > 80 else ''} ({deal['confidence_grade']})" 
              for deal in data['deals'][:3]])}
""" for sector, data in top_sectors[:3]])}

## 🌍 GEOGRAPHIC INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Regional Distribution
{chr(10).join([f"- **{geo}:** {count} transactions ({count/total_deals*100:.1f}%)" 
              for geo, count in sorted(geo_distribution.items(), key=lambda x: x[1], reverse=True)])}

### Cross-Border Activity
- **International Transactions:** {len([d for d in deals if len(d.get('all_geographies', [])) > 1])}
- **Geographic Diversification Score:** {len(geo_distribution)}/10 ({'High' if len(geo_distribution) > 6 else 'Medium' if len(geo_distribution) > 3 else 'Concentrated'})

## 🎯 STRATEGIC THEMES ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Dominant Strategic Rationales
{chr(10).join([f"- **{theme}:** {count} deals ({count/total_deals*100:.1f}%)" 
              for theme, count in sorted(strategic_themes.items(), key=lambda x: x[1], reverse=True)])}

## 💼 HIGH-PRIORITY DEAL INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Tier 1 Opportunities (High Confidence, High Value)
{chr(10).join([f"""
**Deal #{deal['id']}:** {deal['title']}
- **Sector:** {deal['sector']} {f"({deal['subsector']})" if deal['subsector'] else ""}
- **Value:** {deal['value_display']}
- **Confidence:** {deal['confidence_grade']} ({deal['confidence_score']:.2f})
- **Strategic Rationale:** {deal['strategic_analysis']['primary_rationale']}
- **Risk Level:** {deal['risk_assessment']['risk_level']}
- **Intelligence ID:** {deal['intelligence_id']}
""" for deal in sorted([d for d in deals if d['confidence_score'] > 0.7], 
                     key=lambda x: x['confidence_score'], reverse=True)[:5]])}

### Emerging Opportunities (Developing Intelligence)
{chr(10).join([f"""
**Deal #{deal['id']}:** {deal['title'][:70]}{'...' if len(deal['title']) > 70 else ''}
- **Status:** {deal['confidence_grade']} | **Sector:** {deal['sector']} | **Risk:** {deal['risk_assessment']['risk_level']}
""" for deal in [d for d in deals if 0.4 <= d['confidence_score'] <= 0.7][:5]])}

## 📈 MARKET DYNAMICS & OUTLOOK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Market Sentiment Indicators
- **Deal Flow Velocity:** {'Accelerating' if len(high_confidence_deals) > total_deals * 0.6 else 'Steady' if len(high_confidence_deals) > total_deals * 0.4 else 'Cautious'}
- **Sector Concentration:** {'High' if top_sectors[0][1]['count'] > total_deals * 0.4 else 'Balanced'}
- **Risk Profile:** {'Conservative' if risk_distribution['Low'] > total_deals * 0.5 else 'Aggressive' if risk_distribution['High'] > total_deals * 0.3 else 'Balanced'}

### Key Market Drivers
1. **{top_sectors[0][0]} Sector Dominance** - {top_sectors[0][1]['count']} deals suggest sector consolidation
2. **Strategic Focus on {max(strategic_themes.items(), key=lambda x: x[1])[0]}** - Primary deal rationale
3. **Geographic Concentration in {max(geo_distribution.items(), key=lambda x: x[1])[0]}** - Regional market focus

## 🚨 ACTIONABLE INTELLIGENCE RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Immediate Actions (24-48 hours)
1. **Priority Monitoring:** Track {len(high_confidence_deals)} high-confidence deals for rapid developments
2. **Sector Deep Dive:** Conduct competitive analysis in {top_sectors[0][0]} sector
3. **Risk Mitigation:** Review {risk_distribution['High']} high-risk deals for red flags

### Strategic Priorities (1-2 weeks)
1. **Market Entry Assessment:** Evaluate opportunities in top-performing sectors
2. **Geographic Strategy:** Capitalize on {max(geo_distribution.items(), key=lambda x: x[1])[0]} market concentration
3. **Competitive Intelligence:** Monitor strategic themes for market positioning

### Long-term Intelligence (1 month+)
1. **Portfolio Optimization:** Align with dominant strategic theme of {max(strategic_themes.items(), key=lambda x: x[1])[0]}
2. **Risk Management:** Develop frameworks for identified risk patterns
3. **Market Timing:** Position for next wave of sector consolidation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**INTELLIGENCE CONFIDENCE:** {sum(d['confidence_score'] for d in deals)/total_deals*100:.0f}% | **NEXT UPDATE:** 24-48 hours | **CONTACT:** M&A Intelligence Team
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return report


def main():
    # Enhanced header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Enhanced M&A Intelligence Processor</h1>
        <p>Professional-grade M&A intelligence with Big 4 analytical standards</p>
        <div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.9;">
            ✨ Advanced Sector Classification | 📊 Financial Analysis | 🎯 Risk Assessment | 📈 Strategic Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize enhanced processor
    if 'enhanced_processor' not in st.session_state:
        st.session_state.enhanced_processor = EnhancedMAProcessor()
    
    # Enhanced sidebar controls
    st.sidebar.header("🔧 Intelligence Controls")
    
    # Advanced filters
    sector_filter = st.sidebar.selectbox(
        "🏭 Sector Focus",
        ['All Sectors', 'Technology', 'Financial', 'Healthcare', 'Industrial', 
         'Energy', 'Consumer', 'Automotive', 'Real Estate', 'Materials']
    )
    
    geography_filter = st.sidebar.selectbox(
        "🌍 Geographic Focus",
        ['All Regions', 'UK', 'Germany', 'France', 'Europe', 'USA', 'China', 'Asia']
    )
    
    min_value_filter = st.sidebar.selectbox(
        "💰 Minimum Deal Value",
        ['Any Value', '10', '60', '300', '1000']
    )
    
    confidence_filter = st.sidebar.slider(
        "🎯 Minimum Confidence Score",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Filter deals by intelligence confidence level"
    )
    
    risk_filter = st.sidebar.slider(
        "⚠️ Maximum Risk Level",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.1,
        help="Filter out deals above risk threshold"
    )
    
    # Enhanced processing section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📧 Intelligence Input")
        
        # Enhanced sample data
        sample_data = """Technology

8. Adarga seeks GBP 6m-GBP 8m in new funding – report

* Previous USD 20m investment round led by BOKA Group
* AI-powered intelligence platform for defense applications
* Series B funding round to accelerate product development

Adarga, a UK-based artificial intelligence company specializing in defense and security applications, is engaged in extensive discussions with potential investors regarding a capital infusion ranging from GBP 6m to GBP 8m, Sky News reported.

The company's AI-powered intelligence platform processes vast amounts of unstructured data to provide actionable insights for defense and security organizations. The expedited fundraising effort follows the recent departure of Sir Donald Brydon as the firm's chairman.

Source: Sky News
Size: 5m-30m (GBP)
Grade: Strong evidence
Intelligence ID: intelcms-k9mrqp

9. Enerim sponsor KLAR Partners preps sale via Macquarie

* Mandate awarded last autumn, launch timing unclear
* Sellside awaits better visibility on 2025 financials
* Finnish SaaS company serving energy utilities sector

KLAR Partners is working with Macquarie on preparations to sell Finnish software company Enerim, three sources familiar with the situation said. The mandate to sell the company, which provides solutions to the energy and utilities industries on a software-as-a-service (SaaS) model, was awarded last autumn.

Enerim recorded EUR 28.6m 2023 revenue, with a negative EBITDA margin of 5%. The company offers cloud-based solutions for energy sector customer management and billing processes.

Source: Proprietary Intelligence
Size: 30m-60m (GBP)
Value: EUR 35-50m estimated
Stake Value: 100%
Grade: Strong evidence
Intelligence ID: intelcms-2c6wxf

Financial

25. Novo Banco suitor CaixaBank hires Morgan Stanley to launch EUR 3bn offer

* Portuguese banking consolidation opportunity
* Cross-border European banking merger
* Regulatory approval process initiated

CaixaBank has mandated Morgan Stanley to launch a EUR 3bn acquisition offer for Novo Banco, marking a significant cross-border banking consolidation in Europe. The Spanish banking giant views the Portuguese market as strategically attractive for geographic expansion.

The transaction would create one of the largest banking groups in the Iberian Peninsula, with significant synergies expected from technology integration and branch network optimization.

Source: Financial Times
Size: > 60m (GBP)
Value: EUR 3bn enterprise value
Grade: Strong evidence
Intelligence ID: intelcms-3bft9k

Materials

1. Stora Enso divests forest assets for EUR 900m

* Soya Group and MEAG-led consortium acquire majority stakes  
* 15-year wood supply and forest management agreements secured
* EUR 790m net debt reduction and EUR 25m EBITDA decrease expected

Stora Enso has entered into an agreement to divest approximately 175,000 hectares of forest land, equivalent to 12.4% of its total forest land holdings in Sweden for an enterprise value of EUR 900 million.

Soya Group will hold a 40.6% share in the newly formed company, and a MEAG led consortium will hold 44.4% of the shares. MEAG is the asset manager of Munich Re, a German insurance company. Stora Enso will retain a 15% ownership in the company.

Source: Company Press Release
Size: > 60m (GBP)
Value: EUR 900m enterprise value
Grade: Confirmed
Intelligence ID: intelcms-n3h2rt"""
        
        email_input = st.text_area(
            "Intelligence Feed Input:",
            value=sample_data,
            height=400,
            help="Input raw M&A intelligence data for enhanced processing and analysis"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            process_button = st.button("🚀 Process Intelligence", type="primary")
        with col_b:
            if st.button("🔄 Reset Analysis"):
                st.session_state.clear()
                st.rerun()
    
    with col2:
        st.subheader("📊 Intelligence Dashboard")
        
        if process_button and email_input:
            with st.spinner("Processing enhanced M&A intelligence..."):
                # Enhanced parsing
                deals = st.session_state.enhanced_processor.parse_email_content_enhanced(email_input)
                
                # Apply enhanced filters
                filters = {
                    'sector': sector_filter,
                    'geography': geography_filter,
                    'min_value': float(min_value_filter) if min_value_filter != 'Any Value' else 0,
                    'min_confidence': confidence_filter,
                    'max_risk': risk_filter
                }
                
                filtered_deals = st.session_state.enhanced_processor.apply_filters_enhanced(deals, filters)
                
                # Store in session state
                st.session_state.enhanced_deals = deals
                st.session_state.filtered_enhanced_deals = filtered_deals
                st.session_state.raw_content = email_input
        
        # Display enhanced results
        if 'filtered_enhanced_deals' in st.session_state:
            deals = st.session_state.enhanced_deals
            filtered_deals = st.session_state.filtered_enhanced_deals
            
            # Enhanced metrics dashboard
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric(
                    "Total Intelligence", 
                    len(deals),
                    help="Total deals processed"
                )
            
            with col_b:
                st.metric(
                    "Filtered Results", 
                    len(filtered_deals),
                    delta=f"{len(filtered_deals)-len(deals)}" if len(filtered_deals) != len(deals) else None
                )
            
            with col_c:
                avg_confidence = sum(d['confidence_score'] for d in filtered_deals) / len(filtered_deals) if filtered_deals else 0
                st.metric(
                    "Avg Confidence", 
                    f"{avg_confidence:.2f}",
                    help="Average intelligence confidence score"
                )
            
            with col_d:
                high_value_deals = len([d for d in filtered_deals if any(v and v > 100 for v in [
                    d['financial_data'].get('enterprise_value'),
                    d['financial_data'].get('equity_value'),
                    d['financial_data'].get('transaction_value')
                ])])
                st.metric(
                    "High-Value Deals", 
                    high_value_deals,
                    help="Deals >$100M"
                )
            
            if filtered_deals:
                # Enhanced deal display
                for deal in filtered_deals:
                    # Professional deal card
                    confidence_class = ('confidence-high' if deal['confidence_score'] > 0.7 
                                      else 'confidence-medium' if deal['confidence_score'] > 0.4 
                                      else 'confidence-low')
                    
                    risk_class = ('risk-low' if deal['risk_assessment']['risk_level'] == 'Low'
                                else 'risk-medium' if deal['risk_assessment']['risk_level'] == 'Medium'
                                else 'risk-high')
                    
                    st.markdown(f"""
                    <div class="deal-card">
                        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 1rem;">
                            <div style="font-size: 1.2rem; font-weight: 700; color: #2c3e50;">
                                Deal #{deal['id']}: {deal['title']}
                            </div>
                        </div>
                        
                        <div style="margin: 1rem 0;">
                            <span class="sector-badge">{deal['sector']}</span>
                            {f'<span class="sector-badge" style="background: linear-gradient(135deg, #16a085 0%, #1abc9c 100%);">{deal["subsector"]}</span>' if deal['subsector'] else ''}
                            <span class="{confidence_class}">{deal['confidence_grade']} ({deal['confidence_score']:.2f})</span>
                            <span class="risk-indicator {risk_class}">{deal['risk_assessment']['risk_level']} Risk</span>
                        </div>
                        
                        <div class="financial-highlight">
                            💰 {deal['value_display']} | 📊 {deal['size_category']} | 🌍 {deal['geography']}
                        </div>
                        
                        {f'<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0; font-size: 0.9rem; line-height: 1.6; color: #2c3e50;">{deal["summary"]}</div>' if deal['summary'] else ''}
                        
                        {f'<div style="margin: 1rem 0;">{"<br>".join([f"<span style=&#34;color: #7f8c8d;&#34;>• {detail}</span>" for detail in deal["details"][:3]])}</div>' if deal['details'] else ''}
                        
                        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #ecf0f1;">
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; font-size: 0.85rem;">
                                <div><span style="color: #7f8c8d; font-weight: 600;">Strategic Rationale:</span> {deal['strategic_analysis']['primary_rationale']}</div>
                                <div><span style="color: #7f8c8d; font-weight: 600;">Primary Risk:</span> {deal['risk_assessment']['primary_risk'].title()}</div>
                                <div><span style="color: #7f8c8d; font-weight: 600;">Geography Confidence:</span> {deal['geography_confidence']:.2f}</div>
                                <div><span style="color: #7f8c8d; font-weight: 600;">Sector Confidence:</span> {deal['sector_confidence']:.2f}</div>
                                <div><span style="color: #7f8c8d; font-weight: 600;">Intelligence ID:</span> {deal['intelligence_id']}</div>
                                <div><span style="color: #7f8c8d; font-weight: 600;">Processed:</span> {deal['processed_timestamp'][:10]}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Expandable detailed analysis
                    with st.expander(f"🔍 Detailed Analysis - Deal {deal['id']}", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Financial Intelligence")
                            st.json(deal['financial_data'])
                            
                            st.markdown("#### Strategic Analysis")
                            st.json(deal['strategic_analysis'])
                        
                        with col2:
                            st.markdown("#### Risk Assessment")
                            st.json(deal['risk_assessment'])
                            
                            st.markdown("#### Confidence Indicators")
                            st.write(deal['confidence_indicators'])
                        
                        st.markdown("#### Raw Intelligence")
                        st.text_area("Source Material", deal['original_text'], height=150, disabled=True)
            else:
                st.info("🔍 No deals match current filter criteria. Adjust filters to see more results.")
        else:
            st.info("🚀 Ready for enhanced M&A intelligence processing. Input data and click 'Process Intelligence'")
    
    # Enhanced analytics and reporting
    if 'filtered_enhanced_deals' in st.session_state and st.session_state.filtered_enhanced_deals:
        st.markdown("---")
        
        # Enhanced tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Advanced Analytics", "🎯 Intelligence Report", "📈 Market Intelligence", "💾 Export & Download"])
        
        with tab1:
            st.subheader("📊 Advanced Market Analytics")
            
            deals = st.session_state.filtered_enhanced_deals
            
            # Enhanced visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                # Sector analysis with subsectors
                sector_data = []
                for deal in deals:
                    sector_data.append({
                        'Sector': deal['sector'],
                        'Subsector': deal['subsector'] if deal['subsector'] else 'General',
                        'Confidence': deal['confidence_score'],
                        'Risk': deal['risk_assessment']['overall_risk_score']
                    })
                
                sector_df = pd.DataFrame(sector_data)
                
                fig_sector = px.sunburst(
                    sector_df,
                    path=['Sector', 'Subsector'],
                    title="🎯 Sector & Subsector Distribution",
                    color='Confidence',
                    color_continuous_scale='RdYlGn'
                )
                fig_sector.update_layout(height=400)
                st.plotly_chart(fig_sector, use_container_width=True)
            
            with col2:
                # Risk vs Confidence scatter plot
                risk_confidence_data = []
                for deal in deals:
                    risk_confidence_data.append({
                        'Deal': f"Deal {deal['id']}",
                        'Confidence': deal['confidence_score'],
                        'Risk': deal['risk_assessment']['overall_risk_score'],
                        'Value': max([
                            deal['financial_data'].get('enterprise_value', 0),
                            deal['financial_data'].get('equity_value', 0),
                            deal['financial_data'].get('transaction_value', 0)
                        ]),
                        'Sector': deal['sector']
                    })
                
                risk_df = pd.DataFrame(risk_confidence_data)
                
                fig_scatter = px.scatter(
                    risk_df,
                    x='Risk',
                    y='Confidence',
                    size='Value',
                    color='Sector',
                    hover_data=['Deal'],
                    title="⚡ Risk vs Confidence Matrix",
                    labels={'Risk': 'Risk Score →', 'Confidence': 'Confidence Score →'}
                )
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Financial analysis
            st.markdown("### 💰 Financial Intelligence Dashboard")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Deal value distribution
                value_data = []
                for deal in deals:
                    max_value = max([
                        deal['financial_data'].get('enterprise_value', 0),
                        deal['financial_data'].get('equity_value', 0),
                        deal['financial_data'].get('transaction_value', 0)
                    ])
                    if max_value > 0:
                        value_data.append({
                            'Deal': f"Deal {deal['id']}",
                            'Value': max_value,
                            'Currency': deal['financial_data'].get('currency', 'USD'),
                            'Type': 'EV' if deal['financial_data'].get('enterprise_value') else 'Equity' if deal['financial_data'].get('equity_value') else 'Transaction'
                        })
                
                if value_data:
                    value_df = pd.DataFrame(value_data)
                    fig_value = px.bar(
                        value_df,
                        x='Deal',
                        y='Value',
                        color='Type',
                        title="💵 Deal Values (Millions)",
                        hover_data=['Currency']
                    )
                    fig_value.update_layout(height=300, xaxis_tickangle=-45)
                    st.plotly_chart(fig_value, use_container_width=True)
                else:
                    st.info("No financial data available for visualization")
            
            with col2:
                # Strategic rationale pie chart
                rationale_counts = {}
                for deal in deals:
                    rationale = deal['strategic_analysis']['primary_rationale']
                    rationale_counts[rationale] = rationale_counts.get(rationale, 0) + 1
                
                fig_rationale = px.pie(
                    values=list(rationale_counts.values()),
                    names=list(rationale_counts.keys()),
                    title="🎯 Strategic Rationales"
                )
                fig_rationale.update_layout(height=300)
                st.plotly_chart(fig_rationale, use_container_width=True)
            
            with col3:
                # Geographic confidence heatmap
                geo_confidence = {}
                for deal in deals:
                    geo = deal['geography']
                    if geo in geo_confidence:
                        geo_confidence[geo]['confidence'] += deal['confidence_score']
                        geo_confidence[geo]['count'] += 1
                    else:
                        geo_confidence[geo] = {'confidence': deal['confidence_score'], 'count': 1}
                
                # Calculate averages
                for geo_data in geo_confidence.values():
                    geo_data['avg_confidence'] = geo_data['confidence'] / geo_data['count']
                
                geo_df = pd.DataFrame([
                    {'Geography': geo, 'Avg_Confidence': data['avg_confidence'], 'Deal_Count': data['count']}
                    for geo, data in geo_confidence.items()
                ])
                
                fig_geo = px.bar(
                    geo_df,
                    x='Geography',
                    y='Avg_Confidence',
                    color='Deal_Count',
                    title="🌍 Geographic Confidence",
                    color_continuous_scale='Blues'
                )
                fig_geo.update_layout(height=300, xaxis_tickangle=-45)
                st.plotly_chart(fig_geo, use_container_width=True)
        
        with tab2:
            st.subheader("🎯 Professional Intelligence Report")
            
            # Generate comprehensive report
            intelligence_report = st.session_state.enhanced_processor.generate_market_intelligence_report(
                st.session_state.filtered_enhanced_deals
            )
            
            # Display report in professional format
            st.markdown("### 📋 Executive Intelligence Brief")
            st.markdown(intelligence_report)
            
            # Key insights summary
            st.markdown("---")
            st.markdown("### 💡 Key Intelligence Insights")
            
            deals = st.session_state.filtered_enhanced_deals
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 🔥 Hot Sectors")
                sector_counts = {}
                for deal in deals:
                    sector = deal['sector']
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
                
                for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                    st.metric(sector, f"{count} deals", f"{count/len(deals)*100:.0f}%")
            
            with col2:
                st.markdown("#### ⚡ High-Confidence Deals")
                high_conf_deals = [d for d in deals if d['confidence_score'] > 0.7]
                for deal in high_conf_deals[:3]:
                    st.markdown(f"**Deal {deal['id']}** - {deal['confidence_score']:.2f}")
                    st.caption(deal['title'][:50] + "...")
            
            with col3:
                st.markdown("#### 💰 Major Transactions")
                large_deals = sorted([d for d in deals if any(v and v > 100 for v in [
                    d['financial_data'].get('enterprise_value'),
                    d['financial_data'].get('equity_value'),
                    d['financial_data'].get('transaction_value')
                ])], key=lambda x: max([
                    x['financial_data'].get('enterprise_value', 0),
                    x['financial_data'].get('equity_value', 0),
                    x['financial_data'].get('transaction_value', 0)
                ]), reverse=True)
                
                for deal in large_deals[:3]:
                    st.markdown(f"**Deal {deal['id']}** - {deal['value_display']}")
                    st.caption(deal['title'][:50] + "...")
        
        with tab3:
            st.subheader("📈 Market Intelligence & Trends")
            
            deals = st.session_state.filtered_enhanced_deals
            
            # Market trend analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Market Activity Heatmap")
                
                # Create sector-geography matrix
                matrix_data = []
                for deal in deals:
                    matrix_data.append({
                        'Sector': deal['sector'],
                        'Geography': deal['geography'],
                        'Confidence': deal['confidence_score'],
                        'Count': 1
                    })
                
                matrix_df = pd.DataFrame(matrix_data)
                if not matrix_df.empty:
                    pivot_table = matrix_df.pivot_table(
                        values='Count',
                        index='Sector',
                        columns='Geography',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    fig_heatmap = px.imshow(
                        pivot_table.values,
                        labels=dict(x="Geography", y="Sector", color="Deal Count"),
                        x=pivot_table.columns,
                        y=pivot_table.index,
                        color_continuous_scale='Blues',
                        title="🔥 Sector-Geography Activity Matrix"
                    )
                    fig_heatmap.update_layout(height=400)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
            
            with col2:
                st.markdown("#### 🎯 Confidence Distribution")
                
                confidence_ranges = {
                    'Very High (0.8-1.0)': len([d for d in deals if d['confidence_score'] >= 0.8]),
                    'High (0.6-0.8)': len([d for d in deals if 0.6 <= d['confidence_score'] < 0.8]),
                    'Medium (0.4-0.6)': len([d for d in deals if 0.4 <= d['confidence_score'] < 0.6]),
                    'Developing (0.2-0.4)': len([d for d in deals if 0.2 <= d['confidence_score'] < 0.4]),
                    'Low (<0.2)': len([d for d in deals if d['confidence_score'] < 0.2])
                }
                
                fig_confidence = px.bar(
                    x=list(confidence_ranges.keys()),
                    y=list(confidence_ranges.values()),
                    title="📊 Intelligence Confidence Distribution",
                    color=list(confidence_ranges.values()),
                    color_continuous_scale='RdYlGn'
                )
                fig_confidence.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig_confidence, use_container_width=True)
            
            # Strategic intelligence summary
            st.markdown("#### 🧠 Strategic Intelligence Summary")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Market Velocity**")
                high_conf_ratio = len([d for d in deals if d['confidence_score'] > 0.7]) / len(deals)
                velocity = "🚀 Fast" if high_conf_ratio > 0.6 else "⚡ Moderate" if high_conf_ratio > 0.4 else "🐌 Slow"
                st.markdown(f"{velocity} ({high_conf_ratio:.1%})")
                
                st.markdown("**Risk Profile**")
                low_risk_ratio = len([d for d in deals if d['risk_assessment']['risk_level'] == 'Low']) / len(deals)
                risk_profile = "🟢 Conservative" if low_risk_ratio > 0.5 else "🟡 Balanced" if low_risk_ratio > 0.3 else "🔴 Aggressive"
                st.markdown(f"{risk_profile} ({low_risk_ratio:.1%})")
            
            with col2:
                st.markdown("**Geographic Spread**")
                unique_geos = len(set(d['geography'] for d in deals))
                geo_spread = "🌍 Global" if unique_geos > 5 else "🌎 Regional" if unique_geos > 3 else "🏠 Local"
                st.markdown(f"{geo_spread} ({unique_geos} regions)")
                
                st.markdown("**Sector Concentration**")
                sector_counts = {}
                for deal in deals:
                    sector = deal['sector']
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
                max_sector_ratio = max(sector_counts.values()) / len(deals) if sector_counts else 0
                concentration = "🎯 High" if max_sector_ratio > 0.4 else "📊 Medium" if max_sector_ratio > 0.25 else "🌈 Diversified"
                st.markdown(f"{concentration} ({max_sector_ratio:.1%})")
            
            with col3:
                st.markdown("**Deal Scale**")
                large_deal_ratio = len([d for d in deals if 'Large Cap' in d['size_category'] or 'Mega' in d['size_category']]) / len(deals)
                scale = "💎 Large-Cap" if large_deal_ratio > 0.4 else "💼 Mid-Market" if large_deal_ratio > 0.2 else "🌱 Growth"
                st.markdown(f"{scale} ({large_deal_ratio:.1%})")
                
                st.markdown("**Strategic Focus**")
                rationale_counts = {}
                for deal in deals:
                    rationale = deal['strategic_analysis']['primary_rationale']
                    rationale_counts[rationale] = rationale_counts.get(rationale, 0) + 1
                top_rationale = max(rationale_counts.items(), key=lambda x: x[1])[0] if rationale_counts else "Unknown"
                st.markdown(f"🎯 {top_rationale}")
        
        with tab4:
            st.subheader("💾 Export & Download Options")
            
            deals = st.session_state.filtered_enhanced_deals
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Data Exports")
                
                # Enhanced CSV export
                enhanced_df = pd.DataFrame([{
                    'Deal_ID': deal['id'],
                    'Title': deal['title'],
                    'Sector': deal['sector'],
                    'Subsector': deal['subsector'],
                    'Geography': deal['geography'],
                    'Value_Display': deal['value_display'],
                    'Size_Category': deal['size_category'],
                    'Confidence_Grade': deal['confidence_grade'],
                    'Confidence_Score': deal['confidence_score'],
                    'Risk_Level': deal['risk_assessment']['risk_level'],
                    'Risk_Score': deal['risk_assessment']['overall_risk_score'],
                    'Strategic_Rationale': deal['strategic_analysis']['primary_rationale'],
                    'Enterprise_Value': deal['financial_data'].get('enterprise_value'),
                    'Currency': deal['financial_data'].get('currency'),
                    'Intelligence_ID': deal['intelligence_id'],
                    'Processed_Date': deal['processed_timestamp'][:10]
                } for deal in deals])
                
                csv_data = enhanced_df.to_csv(index=False)
                st.download_button(
                    label="📈 Download Enhanced CSV",
                    data=csv_data,
                    file_name=f"enhanced_ma_intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Comprehensive deal data with enhanced analytics"
                )
                
                # JSON export for technical users
                json_data = json.dumps([deal for deal in deals], indent=2, default=str)
                st.download_button(
                    label="🔧 Download JSON (Technical)",
                    data=json_data,
                    file_name=f"ma_intelligence_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    help="Complete deal data with all analysis fields"
                )
            
            with col2:
                st.markdown("#### 📋 Reports")
                
                # Enhanced intelligence report
                intelligence_report = st.session_state.enhanced_processor.generate_market_intelligence_report(deals)
                st.download_button(
                    label="📊 Download Intelligence Report",
                    data=intelligence_report,
                    file_name=f"market_intelligence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    help="Professional market intelligence analysis"
                )
                
                # Executive summary for sharing
                exec_summary = f"""# EXECUTIVE M&A INTELLIGENCE BRIEF
**Date:** {datetime.now().strftime('%B %d, %Y')}
**Deals Analyzed:** {len(deals)}
**Average Confidence:** {sum(d['confidence_score'] for d in deals)/len(deals):.2f}

## TOP OPPORTUNITIES
{chr(10).join([f"• Deal #{deal['id']}: {deal['title'][:80]}{'...' if len(deal['title']) > 80 else ''} ({deal['confidence_grade']})" for deal in sorted(deals, key=lambda x: x['confidence_score'], reverse=True)[:5]])}

## MARKET INSIGHTS
• **Dominant Sector:** {max([(sector, len([d for d in deals if d['sector'] == sector])) for sector in set(d['sector'] for d in deals)], key=lambda x: x[1])[0]}
• **Geographic Focus:** {max([(geo, len([d for d in deals if d['geography'] == geo])) for geo in set(d['geography'] for d in deals)], key=lambda x: x[1])[0]}
• **Risk Assessment:** {len([d for d in deals if d['risk_assessment']['risk_level'] == 'Low'])} Low Risk, {len([d for d in deals if d['risk_assessment']['risk_level'] == 'Medium'])} Medium Risk, {len([d for d in deals if d['risk_assessment']['risk_level'] == 'High'])} High Risk

Generated by Enhanced M&A Intelligence Processor
"""
                
                st.download_button(
                    label="📑 Download Executive Brief",
                    data=exec_summary,
                    file_name=f"executive_brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    help="Concise executive summary for leadership"
                )
            
            # Real-time collaboration features
            st.markdown("---")
            st.markdown("#### 🤝 Collaboration Features")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📧 Generate Email Update"):
                    email_update = f"""Subject: M&A Intelligence Update - {len(deals)} Active Deals

Team,

Quick intelligence update from our M&A monitoring:

• {len(deals)} total deals being tracked
• {len([d for d in deals if d['confidence_score'] > 0.7])} high-confidence opportunities
• Top sector: {max([(sector, len([d for d in deals if d['sector'] == sector])) for sector in set(d['sector'] for d in deals)], key=lambda x: x[1])[0]}

Key developments requiring attention:
{chr(10).join([f"• Deal #{deal['id']}: {deal['title'][:60]}... ({deal['confidence_grade']})" for deal in sorted(deals, key=lambda x: x['confidence_score'], reverse=True)[:3]])}

Full intelligence report attached.

Best regards,
M&A Intelligence Team"""
                    
                    st.text_area("Email Update", email_update, height=200)
            
            with col2:
                if st.button("📱 Generate Slack Summary"):
                    slack_summary = f"""🎯 *M&A Intelligence Update*

📊 *Current Pipeline:* {len(deals)} active deals
⚡ *High Confidence:* {len([d for d in deals if d['confidence_score'] > 0.7])} deals
🏭 *Top Sector:* {max([(sector, len([d for d in deals if d['sector'] == sector])) for sector in set(d['sector'] for d in deals)], key=lambda x: x[1])[0]}

🔥 *Hot Deals:*
{chr(10).join([f"• Deal #{deal['id']}: {deal['title'][:50]}... ({deal['confidence_grade']})" for deal in sorted(deals, key=lambda x: x['confidence_score'], reverse=True)[:3]])}

💡 _Full analysis available in M&A Intelligence dashboard_"""
                    
                    st.text_area("Slack Summary", slack_summary, height=200)

if __name__ == "__main__":
    main()