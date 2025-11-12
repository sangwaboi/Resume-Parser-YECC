import json
import time
import requests
from config import SKYQ_BASE_URL, SKYQ_HEADERS, MODEL_CONFIGS, MAX_TEXT_LENGTHS
from utils import clean_array, extract_email, extract_phone, extract_linkedin, extract_years_experience


def enhance_parsed_data(parsed_data, resume_text):
    """Post-process and enhance parsed resume data"""
    if 'erp_systems' in parsed_data:
        parsed_data['erp_systems'] = clean_array(parsed_data['erp_systems'])
    
    if 'erp_modules' in parsed_data:
        parsed_data['erp_modules'] = clean_array(parsed_data['erp_modules'])
    
    if 'technical_skills' in parsed_data:
        parsed_data['technical_skills'] = clean_array(parsed_data['technical_skills'])
    
    if 'certifications' in parsed_data:
        parsed_data['certifications'] = clean_array(parsed_data['certifications'])
    
    if 'projects' in parsed_data:
        parsed_data['projects'] = clean_array(parsed_data['projects'])
    
    if not parsed_data.get('email'):
        email = extract_email(resume_text)
        if email:
            parsed_data['email'] = email
    
    if not parsed_data.get('phone'):
        phone = extract_phone(resume_text)
        if phone:
            parsed_data['phone'] = phone
    
    if not parsed_data.get('linkedin'):
        linkedin = extract_linkedin(resume_text)
        if linkedin:
            parsed_data['linkedin'] = linkedin
    
    erp_mappings = {
        'D365': 'Microsoft Dynamics 365',
        'EBS': 'Oracle E-Business Suite',
        'JDE': 'JD Edwards',
        'PS': 'PeopleSoft',
        'Netsuite': 'NetSuite',
        'Ms Dynamics': 'Microsoft Dynamics'
    }
    
    normalized_erp = []
    for erp in parsed_data.get('erp_systems', []):
        normalized = erp_mappings.get(erp, erp)
        if normalized not in normalized_erp:
            normalized_erp.append(normalized)
    parsed_data['erp_systems'] = normalized_erp
    
    module_mappings = {
        'FICO': ['FI', 'CO', 'Financial Accounting', 'Controlling'],
        'SCM': ['MM', 'SD', 'Supply Chain Management'],
        'HCM': ['HR', 'Human Capital Management']
    }
    
    expanded_modules = list(parsed_data.get('erp_modules', []))
    modules_to_add = []
    
    for module in expanded_modules:
        if isinstance(module, str) and module in module_mappings:
            modules_to_add.extend(module_mappings[module])
    
    for new_module in modules_to_add:
        if new_module not in expanded_modules:
            expanded_modules.append(new_module)
    
    parsed_data['erp_modules'] = expanded_modules
    
    if not parsed_data.get('total_years_experience'):
        years = extract_years_experience(resume_text)
        if years:
            parsed_data['total_years_experience'] = str(years)
    
    if not parsed_data.get('technical_skills'):
        parsed_data['technical_skills'] = []
    
    if not parsed_data.get('certifications'):
        parsed_data['certifications'] = []
    
    return parsed_data


def score_resume_completeness(parsed_data):
    """Score how complete the parsed resume is (0-100)"""
    score = 0
    
    if parsed_data.get('name'): score += 5
    if parsed_data.get('email'): score += 5
    if parsed_data.get('phone'): score += 5
    if parsed_data.get('location'): score += 5
    if parsed_data.get('summary'): score += 5
    if parsed_data.get('total_years_experience'): score += 5
    
    if parsed_data.get('erp_systems'): score += 15
    if parsed_data.get('erp_modules'): score += 15
    
    if parsed_data.get('experience') and len(parsed_data['experience']) > 0: score += 10
    if parsed_data.get('current_role'): score += 5
    if parsed_data.get('current_company'): score += 5
    
    if parsed_data.get('education'): score += 5
    if parsed_data.get('technical_skills'): score += 5
    if parsed_data.get('certifications'): score += 5
    if parsed_data.get('projects'): score += 5
    
    return score


def parse_resume_with_skyq(resume_text, candidate_name="Unknown", retry_count=0):
    """Parse resume using SkyQ AI with automatic retry and model fallback"""
    
    max_length = MAX_TEXT_LENGTHS[min(retry_count, len(MAX_TEXT_LENGTHS)-1)]
    truncated_text = resume_text[:max_length]
    
    prompt = f"""
Extract information from this ERP Consultant resume and return ONLY valid JSON (no markdown, no explanations).

Use the following JSON structure, accurately filling each field using resume details or leaving empty ("") / [] if unavailable.

{{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "summary": "",
  "total_years_experience": "",
  "current_role": "",
  "current_company": "",
  "erp_systems": [],
  "erp_modules": [],
  "technical_skills": [],
  "certifications": [],
  "education": [
    {{
      "degree": "",
      "university": "",
      "year": ""
    }}
  ],
  "job_experience": [
    {{
      "position": "",  // One of: Consultant, Sr.Developer, Sr Tester, Associate Consultant, Associate Specialist, Principal
      "country": "",
      "company_name": "",
      "employment_type": "", // One of: Full-time, Part-time, Self-employed, Freelance, Internship, Trainee
      "currently_working_here": "",
      "from_date": "",
      "to_date": "",
      "short_description": ""
    }}
  ],
  "erp_projects_experience": [
    {{
      "company_name": "",
      "project_name": "",
      "project_domain": "", // Choose the most appropriate: Healthcare, Finance, Retail, Telecommunications, Energy, Transportation, Education, Government, Real Estate, Hospitality, Media and Entertainment, Consumer Goods, Agriculture, Automobiles, Oracle Cloud Financials, Information Technology
      "project_type": [], // Multiple choices from: Implementation, Roll-out, Support, Specialized Assignments
      "currently_working_on_this_project": "",
      "from_date": "",
      "to_date": "",
      "project_phases_involved": [], // Multiple choices: Requirement Gathering (HLA), CRP, Functional Configuration, Technical Configuration, KUT, UAT, Data Migration, SIT, Post-Go Live Support, Custom Report Building, Integration Building, Custom Solution Building
      "work_location_type": [], // Multiple choices: Onsite, Offshore, Work from Home
      "product": "", // One from: Oracle Cloud ERP (Fusion), Oracle Fusion
      "track": "", // One from: Business Intelligence (BI), Financials (Fin), Human Capital Management (HCM), Supply Chain Management (SCM)
      "financials_modules": [], // Multiple: GL, AP, AR, CM, FA, Tax, FR, IC, RM, Exp, Lease Management, Subledger Accounting, Collection, Risk Management, Template Design
      "hcm_modules": [], // Multiple: Talent, Absence, ORC, Core HR, Payroll, Benefits, OTL, Compensation, Learn, Enterprise and Legal Structure, HCM Data Loader, Self Service HR
      "scm_modules": [], // Multiple: Shipping, Inventory Management, Cost Management, Manufacturing, Quality Management, Supply Chain Financial Orchestration, Supply Chain Planning and Collaboration, Pricing, Order Management, Maintenance, Data Migration, Self-Service Procurement, Purchasing
      "role": "" // One of: Trainee, Associate Consultant, NEWYECC, Junior Consultant, Principal Consultant, Senior Consultant, Solution Architect, Test
    }}
  ]
}}

IMPORTANT:
- "name" usually appears at the very top of the resume; infer it if unlabeled.
- Infer missing data logically from context (e.g., project roles, ERP modules, company details).
- Include ALL ERP systems (SAP, Oracle, Dynamics 365, NetSuite, etc.) and map module abbreviations (e.g., FICO = FI + CO).
- Calculate total_years_experience from durations or phrases like "X years".
- Use "" or [] where data cannot be confidently inferred.

Resume:
{truncated_text}
"""


    
    last_error = None
    
    for idx, config in enumerate(MODEL_CONFIGS):
        try:
            print(f"Attempt {retry_count+1}, Model {idx+1}/{len(MODEL_CONFIGS)}: {config['model']} (text: {len(truncated_text)} chars)")
            
            payload = {
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": "You are a resume parsing assistant. Extract structured information and return ONLY valid JSON. No markdown, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": config["temperature"],
                "max_tokens": config.get("max_tokens", 2000)
            }
            
            response = requests.post(
                f"{SKYQ_BASE_URL}/api/chat/completions",
                headers=SKYQ_HEADERS,
                json=payload,
                timeout=90
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                content = None
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0].get('message', {}).get('content')
                elif 'response' in result:
                    content = result['response']
                
                if not content:
                    print("No content in response")
                    continue
                
                print(f"Response preview: {content[:150]}...")
                
                content = content.strip()
                
                if '<think>' in content and '</think>' in content:
                    start = content.find('</think>') + 8
                    content = content[start:].strip()
                    print("Removed reasoning tags")
                
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                parsed_data = json.loads(content)
                print(f"✅ Resume parsed successfully with {config['model']}")
                return parsed_data
                
            elif response.status_code == 500:
                error_detail = response.text
                print(f"Model {config['model']} returned 500: {error_detail[:100]}")
                last_error = f"500 error with {config['model']}"
                
                if "Ollama: 500" in error_detail:
                    print("Ollama internal error, trying next model...")
                    time.sleep(1)
                    continue
            else:
                last_error = f"Status {response.status_code}"
                print(f"Model {config['model']} failed: {last_error}")
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            if 'content' in locals():
                print(f"Failed content: {content[:300]}")
            last_error = f"JSON error: {str(e)}"
            
        except requests.exceptions.Timeout:
            print(f"Model {config['model']} timed out")
            last_error = "Request timeout"
            
        except Exception as e:
            print(f"Model {config['model']} error: {e}")
            last_error = str(e)
    
    if retry_count < 3:
        print(f"\n⚠️ All models failed, retrying with shorter text (attempt {retry_count + 2}/4)...\n")
        time.sleep(2)
        return parse_resume_with_skyq(resume_text, candidate_name, retry_count + 1)
    
    raise Exception(f"All retry attempts exhausted. Last error: {last_error}")