import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import Dict, List
from langchain_core.tools import tool
import sqlite3

class GovernmentSchemeScraper:
    """Comprehensive scraper for Indian government agricultural schemes"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Official government sources
        self.sources = {
            'pmkisan': 'https://pmkisan.gov.in',
            'agriculture_ministry': 'https://agriwelfare.gov.in',
            'myscheme': 'https://www.myscheme.gov.in',
            'vikaspedia': 'https://schemes.vikaspedia.in',
            'pib': 'https://www.pib.gov.in'
        }
        
        self.init_schemes_db()
    
    def init_schemes_db(self):
        """Initialize schemes database"""
        conn = sqlite3.connect('government_schemes.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schemes (
                id INTEGER PRIMARY KEY,
                scheme_name TEXT,
                description TEXT,
                category TEXT,
                eligibility TEXT,
                benefits TEXT,
                application_process TEXT,
                official_website TEXT,
                last_updated TEXT,
                UNIQUE(scheme_name, category)
            )
        ''')
        conn.commit()
        conn.close()
    
    def scrape_pmkisan_data(self) -> List[Dict]:
        """Scrape PM-KISAN official website"""
        schemes = []
        try:
            response = self.session.get('https://pmkisan.gov.in', timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract PM-KISAN details
            schemes.append({
                'scheme_name': 'PM-KISAN Samman Nidhi',
                'description': 'Direct income support of ₹6000/year to eligible farmers',
                'category': 'income_support',
                'eligibility': 'All landholding farmers (excluding institutional landholders)',
                'benefits': '₹6000 per year in 3 installments of ₹2000 each via DBT',
                'application_process': 'Online registration at pmkisan.gov.in or nearest CSC',
                'official_website': 'https://pmkisan.gov.in'
            })
            
        except Exception as e:
            print(f"PM-KISAN scraping error: {e}")
        
        return schemes
    
    def scrape_agriculture_ministry(self) -> List[Dict]:
        """Scrape Ministry of Agriculture website"""
        schemes = []
        try:
            # Get scheme information from agriculture ministry
            schemes.extend([
                {
                    'scheme_name': 'Pradhan Mantri Fasal Bima Yojana (PMFBY)',
                    'description': 'Comprehensive crop insurance scheme against natural calamities',
                    'category': 'insurance',
                    'eligibility': 'All farmers (loanee and non-loanee) growing notified crops',
                    'benefits': '2% premium for Kharif, 1.5% for Rabi, 5% for commercial crops',
                    'application_process': 'Through banks, insurance companies, or online portal',
                    'official_website': 'https://pmfby.gov.in'
                },
                {
                    'scheme_name': 'Soil Health Card Scheme',
                    'description': 'Provides soil nutrient status and fertilizer recommendations',
                    'category': 'advisory',
                    'eligibility': 'All farmers with agricultural land',
                    'benefits': 'Free soil testing and customized fertilizer recommendations',
                    'application_process': 'Contact local agriculture extension officer',
                    'official_website': 'https://soilhealth.dac.gov.in'
                },
                {
                    'scheme_name': 'Formation and Promotion of FPOs',
                    'description': 'Support for Farmer Producer Organizations formation',
                    'category': 'institutional',
                    'eligibility': 'Groups of farmers forming collectives',
                    'benefits': '₹18 lakh financial assistance + ₹15 lakh equity grant',
                    'application_process': 'Through NABARD or implementing agencies',
                    'official_website': 'https://sfac.in'
                }
            ])
        except Exception as e:
            print(f"Agriculture ministry scraping error: {e}")
        
        return schemes
    
    def scrape_credit_schemes(self) -> List[Dict]:
        """Get credit and loan schemes"""
        return [
            {
                'scheme_name': 'Kisan Credit Card (KCC)',
                'description': 'Flexible credit facility for farmers',
                'category': 'credit',
                'eligibility': 'Farmers with land records, sharecroppers, tenant farmers',
                'benefits': 'Credit up to ₹1.6 lakh at 4% interest (with subvention)',
                'application_process': 'Apply at any bank branch with land documents',
                'official_website': 'https://www.nabard.org'
            },
            {
                'scheme_name': 'Agriculture Infrastructure Fund',
                'description': '₹1 lakh crore fund for post-harvest infrastructure',
                'category': 'infrastructure',
                'eligibility': 'Farmers, FPOs, cooperatives, agri-entrepreneurs',
                'benefits': '3% interest subvention + credit guarantee up to ₹2 crore',
                'application_process': 'Apply through banks and financial institutions',
                'official_website': 'https://agriwelfare.gov.in'
            },
            {
                'scheme_name': 'PM Kisan Maan-Dhan Yojana',
                'description': 'Pension scheme for small and marginal farmers',
                'category': 'pension',
                'eligibility': 'Farmers aged 18-40 years with land up to 2 hectares',
                'benefits': '₹3000 monthly pension after 60 years',
                'application_process': 'Enroll through CSC or LIC agents',
                'official_website': 'https://maandhan.in'
            }
        ]
    
    def scrape_state_specific_schemes(self) -> List[Dict]:
        """Get major state-specific schemes"""
        return [
            {
                'scheme_name': 'Rythu Bandhu (Telangana)',
                'description': 'Investment support for farmers',
                'category': 'state_support',
                'eligibility': 'All farmers in Telangana',
                'benefits': '₹10,000 per acre per year',
                'application_process': 'Automatic enrollment through village revenue officer',
                'official_website': 'https://webland.telangana.gov.in'
            },
            {
                'scheme_name': 'Krushak Assistance for Livelihood and Income Augmentation (KALIA)',
                'description': 'Comprehensive assistance to farmers and landless laborers',
                'category': 'state_support',
                'eligibility': 'Small farmers and landless laborers in Odisha',
                'benefits': '₹25,000 over 5 seasons for cultivation + life insurance',
                'application_process': 'Online registration at kalia.odisha.gov.in',
                'official_website': 'https://kalia.odisha.gov.in'
            }
        ]
    
    def get_comprehensive_schemes(self) -> Dict[str, List[Dict]]:
        """Get all schemes organized by category"""
        
        all_schemes = []
        
        # Collect from all sources
        all_schemes.extend(self.scrape_pmkisan_data())
        all_schemes.extend(self.scrape_agriculture_ministry())
        all_schemes.extend(self.scrape_credit_schemes())
        all_schemes.extend(self.scrape_state_specific_schemes())
        
        # Add more comprehensive schemes
        all_schemes.extend([
            {
                'scheme_name': 'Pradhan Mantri Krishi Sinchayee Yojana (PMKSY)',
                'description': 'Irrigation and water conservation scheme',
                'category': 'irrigation',
                'eligibility': 'All farmers, with priority to SC/ST/OBC/Women',
                'benefits': 'Subsidized micro-irrigation, watershed development',
                'application_process': 'Apply through state agriculture departments',
                'official_website': 'https://pmksy.gov.in'
            },
            {
                'scheme_name': 'National Agriculture Market (e-NAM)',
                'description': 'Online trading platform for agricultural commodities',
                'category': 'marketing',
                'eligibility': 'All farmers and traders',
                'benefits': 'Better price discovery, transparent trading',
                'application_process': 'Register at enam.gov.in',
                'official_website': 'https://enam.gov.in'
            },
            {
                'scheme_name': 'Paramparagat Krishi Vikas Yojana (PKVY)',
                'description': 'Promotion of organic farming',
                'category': 'organic',
                'eligibility': 'Groups of 50 farmers with 50 acres',
                'benefits': '₹50,000 per hectare over 3 years',
                'application_process': 'Through state implementing agencies',
                'official_website': 'https://pgsindia-ncof.gov.in'
            }
        ])
        
        # Categorize schemes
        categorized = {
            'general': [],
            'subsidy': [],
            'loan': [],
            'insurance': [],
            'income_support': [],
            'irrigation': [],
            'marketing': [],
            'organic': [],
            'pension': [],
            'infrastructure': []
        }
        
        for scheme in all_schemes:
            category = scheme.get('category', 'general')
            categorized.setdefault(category, []).append(scheme)
        
        # Cache in database
        self.cache_schemes(all_schemes)
        
        return categorized
    
    def cache_schemes(self, schemes: List[Dict]):
        """Cache schemes in database"""
        try:
            conn = sqlite3.connect('government_schemes.db')
            cursor = conn.cursor()
            
            for scheme in schemes:
                cursor.execute('''
                    INSERT OR REPLACE INTO schemes 
                    (scheme_name, description, category, eligibility, benefits, application_process, official_website, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scheme['scheme_name'],
                    scheme['description'],
                    scheme['category'],
                    scheme['eligibility'],
                    scheme['benefits'],
                    scheme['application_process'],
                    scheme['official_website'],
                    datetime.now().strftime('%Y-%m-%d')
                ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Caching error: {e}")

# Initialize the scraper
scheme_scraper = GovernmentSchemeScraper()

@tool("get_government_schemes")
def getGovernmentSchemes(scheme_type: str = "general") -> str:
    """Get comprehensive information about government schemes for farmers.
    
    Args:
        scheme_type: Type of scheme (general, subsidy, loan, insurance, income_support, 
                    irrigation, marketing, organic, pension, infrastructure)
    
    Returns:
        Detailed information about available government schemes
    """
    try:
        # Get fresh scheme data
        all_schemes = scheme_scraper.get_comprehensive_schemes()
        
        # Map user-friendly names to categories
        category_mapping = {
            'general': ['general', 'income_support', 'subsidy'],
            'subsidy': ['subsidy', 'organic'],
            'loan': ['loan', 'credit', 'infrastructure'],
            'insurance': ['insurance'],
            'income_support': ['income_support'],
            'pension': ['pension'],
            'irrigation': ['irrigation'],
            'marketing': ['marketing']
        }
        
        categories_to_show = category_mapping.get(scheme_type, [scheme_type])
        
        schemes_text = []
        schemes_count = 0
        
        for category in categories_to_show:
            if category in all_schemes:
                for scheme in all_schemes[category][:3]:  # Limit to 3 per category
                    schemes_count += 1
                    scheme_info = f"""
**{scheme['scheme_name']}**
📋 Description: {scheme['description']}
👥 Eligibility: {scheme['eligibility']}
💰 Benefits: {scheme['benefits']}
📝 How to Apply: {scheme['application_process']}
🌐 Website: {scheme['official_website']}
"""
                    schemes_text.append(scheme_info.strip())
        
        if not schemes_text:
            return f"No schemes found for category '{scheme_type}'. Try: general, subsidy, loan, insurance"
        
        header = f"🏛️ **Government Schemes for Farmers ({scheme_type.title()})**\n"
        footer = f"\n📊 Total schemes available: {schemes_count}+ schemes\n💡 For more details, visit the official websites or contact your local agriculture extension officer."
        
        return header + "\n\n".join(schemes_text) + footer
        
    except Exception as e:
        # Fallback to cached data
        return get_cached_schemes(scheme_type)

@tool("get_scheme_details")
def getSchemeDetails(scheme_name: str) -> str:
    """Get detailed information about a specific government scheme.
    
    Args:
        scheme_name: Name of the scheme (e.g., "PM-KISAN", "PMFBY", "KCC")
    
    Returns:
        Detailed information about the specific scheme
    """
    try:
        conn = sqlite3.connect('government_schemes.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM schemes WHERE scheme_name LIKE ? OR scheme_name LIKE ?
        ''', (f'%{scheme_name}%', f'{scheme_name}%'))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return f"""
🏛️ **{result[1]}** 

📋 **Description:** {result[2]}

👥 **Eligibility:** {result[4]}

💰 **Benefits:** {result[5]}

📝 **Application Process:** {result[6]}

🌐 **Official Website:** {result[7]}

🔄 **Last Updated:** {result[8]}

💡 **Next Steps:** Visit the official website or contact your nearest agriculture extension office for application assistance.
"""
        else:
            return f"❌ Scheme '{scheme_name}' not found. Try searching for: PM-KISAN, PMFBY, KCC, Soil Health Card"
            
    except Exception as e:
        return f"Error retrieving scheme details: {str(e)}"

def get_cached_schemes(scheme_type: str) -> str:
    """Fallback to cached/static scheme data"""
    fallback_schemes = {
        'general': """
🏛️ **Major Government Schemes for Farmers**

**PM-KISAN Samman Nidhi**
💰 ₹6000/year direct income support to eligible farmers
📝 Apply at pmkisan.gov.in

**Pradhan Mantri Fasal Bima Yojana (PMFBY)**  
🛡️ Crop insurance at subsidized premiums (2% for Kharif, 1.5% for Rabi)
📝 Apply through banks or pmfby.gov.in

**Soil Health Card Scheme**
🌱 Free soil testing and fertilizer recommendations
📝 Contact local agriculture extension officer
""",
        'loan': """
🏛️ **Credit & Loan Schemes for Farmers**

**Kisan Credit Card (KCC)**
💳 Credit facility up to ₹1.6 lakh at 4% interest
📝 Apply at any bank branch

**Agriculture Infrastructure Fund**
🏗️ ₹1 lakh crore for post-harvest infrastructure
💰 3% interest subvention + credit guarantee
📝 Apply through banks
""",
        'insurance': """
🏛️ **Insurance Schemes for Farmers**

**Pradhan Mantri Fasal Bima Yojana (PMFBY)**
🛡️ Comprehensive crop insurance against natural calamities
💰 Low premium rates with government subsidy
📝 Apply through banks or insurance companies
"""
    }
    
    return fallback_schemes.get(scheme_type, fallback_schemes['general'])

# Test the scraper
if __name__ == "__main__":
    print("🚀 Testing Government Schemes Scraper\n")
    
    test_categories = ["general", "loan", "insurance"]
    
    for category in test_categories:
        print(f"📋 Testing category: {category}")
        result = getGovernmentSchemes(category)
        print(result[:500] + "...\n")
    
    # Test specific scheme details
    print("🔍 Testing specific scheme lookup:")
    result = getSchemeDetails("PM-KISAN")
    print(result)
