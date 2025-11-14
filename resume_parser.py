import json
import time
import requests
from config import SKYQ_BASE_URL, SKYQ_HEADERS, MODEL_CONFIGS, MAX_TEXT_LENGTHS
from utils import clean_array, extract_email, extract_phone, extract_linkedin, extract_years_experience

def smart_truncate_resume(resume_text, max_length=8000):
    """
    Smart truncation: keeps beginning (contact info) and end (recent experience)
    Returns the most relevant parts of the resume
    """
    if len(resume_text) <= max_length:
        return resume_text, False
    
    header_size = min(2500, max_length // 3)
    footer_size = max_length - header_size - 50  
    
    header = resume_text[:header_size]
    footer = resume_text[-footer_size:]
    
    truncated = header + "\n\n[... middle section omitted ...]\n\n" + footer
    
    print(f"⚠️  Smart truncation applied:")
    print(f"   Original: {len(resume_text)} chars (100%)")
    print(f"   Kept: {len(truncated)} chars ({int(len(truncated)/len(resume_text)*100)}%)")
    print(f"   Missing: {len(resume_text) - header_size - footer_size} chars")
    print(f"   Strategy: First {header_size} + Last {footer_size} chars")
    
    return truncated, True


def extract_section_boundaries(resume_text):
    """
    Find major section boundaries in resume for intelligent chunking
    Returns: dict with section positions
    """
    sections = {
        'contact': (0, 500),
        'summary': None,
        'experience': None,
        'projects': None,
        'education': None,
        'skills': None,
        'certifications': None
    }
    
    lines = resume_text.split('\n')
    
    keywords = {
        'summary': ['summary', 'objective', 'profile', 'about'],
        'experience': ['experience', 'employment', 'work history', 'professional experience'],
        'projects': ['projects', 'project experience', 'erp projects'],
        'education': ['education', 'academic', 'qualification'],
        'skills': ['skills', 'technical skills', 'competencies', 'expertise'],
        'certifications': ['certifications', 'certificates', 'training', 'licenses']
    }
    
    char_count = 0
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        for section, words in keywords.items():
            if any(word in line_lower for word in words):
                if sections[section] is None:
                    sections[section] = (char_count, None)
        
        char_count += len(line) + 1  
    
    section_list = [(k, v[0]) for k, v in sections.items() if v and isinstance(v, tuple)]
    section_list.sort(key=lambda x: x[1])
    
    for i in range(len(section_list) - 1):
        section_name = section_list[i][0]
        start = section_list[i][1]
        end = section_list[i + 1][1]
        sections[section_name] = (start, end)
    
    if section_list:
        last_section = section_list[-1][0]
        sections[last_section] = (section_list[-1][1], len(resume_text))
    
    return sections


def create_focused_chunks(resume_text, max_chunk_size=7000):
    """
    Create focused chunks that prioritize complete sections
    Returns: list of (chunk_text, chunk_description) tuples
    """
    if len(resume_text) <= max_chunk_size:
        return [(resume_text, "complete resume")]
    
    sections = extract_section_boundaries(resume_text)
    chunks = []
    
    chunk1_parts = []
    chunk1_parts.append(resume_text[sections['contact'][0]:sections['contact'][1]])
    
    if sections['summary']:
        start, end = sections['summary']
        chunk1_parts.append(resume_text[start:end] if end else resume_text[start:start+1000])
    
    if sections['skills']:
        start, end = sections['skills']
        chunk1_parts.append(resume_text[start:end] if end else resume_text[start:start+2000])
    
    if sections['certifications']:
        start, end = sections['certifications']
        chunk1_parts.append(resume_text[start:end] if end else resume_text[start:start+1000])
    
    chunk1 = "\n\n".join(chunk1_parts)
    chunks.append((chunk1[:max_chunk_size], "header, summary, skills"))
    
    if sections['experience']:
        start, end = sections['experience']
        exp_text = resume_text[start:end] if end else resume_text[start:]
        
        if len(exp_text) > max_chunk_size:
            chunks.append((exp_text[-max_chunk_size:], "recent work experience"))
            if len(exp_text) > max_chunk_size * 1.5:
                chunks.append((exp_text[:max_chunk_size], "early work experience"))
        else:
            chunks.append((exp_text, "work experience"))
    
    if sections['projects']:
        start, end = sections['projects']
        proj_text = resume_text[start:end] if end else resume_text[start:]
        chunks.append((proj_text[:max_chunk_size], "ERP projects"))
    
    if sections['education']:
        start, end = sections['education']
        edu_text = resume_text[start:end] if end else resume_text[start:start+2000]
        chunks.append((edu_text, "education"))
    
    return chunks


def deduplicate_items(items, key_fields):
    """
    Remove duplicate items based on key fields
    """
    seen = set()
    unique_items = []
    
    for item in items:
        if not isinstance(item, dict):
            if item not in seen:
                seen.add(item)
                unique_items.append(item)
            continue
        
        key_values = tuple(str(item.get(field, '')).lower().strip() for field in key_fields)
        
        if key_values not in seen and any(key_values):  
            seen.add(key_values)
            unique_items.append(item)
    
    return unique_items


def merge_parsed_chunks(chunks_results):
    """
    Merge results from multiple chunks intelligently
    """
    if not chunks_results:
        return {}
    
    if len(chunks_results) == 1:
        return chunks_results[0]
    
    merged = chunks_results[0].copy()
    
    for result in chunks_results[1:]:
        string_fields = ['name', 'email', 'phone', 'location', 'linkedin', 
                        'summary', 'total_years_experience', 'current_role', 'current_company']
        
        for field in string_fields:
            if not merged.get(field) and result.get(field):
                merged[field] = result[field]
            elif result.get(field) and len(str(result[field])) > len(str(merged.get(field, ''))):
                merged[field] = result[field]
        
        simple_arrays = ['erp_systems', 'erp_modules', 'technical_skills', 'certifications']
        for field in simple_arrays:
            if field in result:
                current = merged.get(field, [])
                new_items = result[field]
                merged[field] = list(set(current + new_items))
        
        if 'education' in result:
            current_edu = merged.get('education', [])
            new_edu = result['education']
            merged['education'] = deduplicate_items(
                current_edu + new_edu, 
                ['degree', 'university']
            )
        
        if 'job_experience' in result:
            current_exp = merged.get('job_experience', [])
            new_exp = result['job_experience']
            merged['job_experience'] = deduplicate_items(
                current_exp + new_exp,
                ['company_name', 'position', 'from_date']
            )
        
        if 'erp_projects_experience' in result:
            current_proj = merged.get('erp_projects_experience', [])
            new_proj = result['erp_projects_experience']
            merged['erp_projects_experience'] = deduplicate_items(
                current_proj + new_proj,
                ['project_name', 'company_name']
            )
    
    return merged


def parse_single_chunk(chunk_text, chunk_description, model_config):
    """Parse a single chunk with a specific model"""
    
    prompt = f"""Extract information from this ERP Consultant resume. Return ONLY valid JSON (no markdown, no explanations, no thinking process).
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
      "position": "",
      "country": "",
      "company_name": "",
      "employment_type": "",
      "currently_working_here": false,
      "from_date": "",
      "to_date": "",
      "short_description": ""
    }}
  ],
  "erp_projects_experience": [
    {{
      "company_name": "",
      "project_name": "",
      "project_domain": "",
      "project_type": [],
      "currently_working_on_this_project": false,
      "from_date": "",
      "to_date": "",
      "project_phases_involved": [],
      "work_location_type": [],
      "product": "",
      "track": "",
      "financials_modules": [],
      "hcm_modules": [],
      "scm_modules": [],
      "role": ""
    }}
  ]
}}
EXTRACTION RULES:
1. "name" - Usually at top; extract full name
2. "email" - Look for @ symbol
3. "phone" - Extract with country code if present
4. "location" - Current city, state, country
5. "linkedin" - Full LinkedIn URL if present
6. "summary" - Professional summary/objective (2-3 sentences)
7. "total_years_experience" - Calculate from dates or "X years" phrases
8. "current_role" - Most recent job title
9. "current_company" - Most recent company name
10. "erp_systems" - ALL systems: Oracle Cloud, Oracle Fusion, SAP, Microsoft Dynamics 365, NetSuite, Infor, JD Edwards, Workday, etc.
11. "erp_modules" - ALL modules: GL, AP, AR, FI, CO, MM, SD, PP, HR, HCM, SCM, CRM, etc.
12. "technical_skills" - Programming, databases, tools: SQL, PL/SQL, Python, Java, BODS, ODI, OBIEE, Power BI, Excel, etc.
13. "certifications" - All certifications with issuing org
14. "education" - All degrees with university and year
15. "job_experience" - ALL work history entries
    - position: One of (Consultant, Sr.Developer, Sr Tester, Associate Consultant, Associate Specialist, Principal)
    - employment_type: One of (Full-time, Part-time, Self-employed, Freelance, Internship, Trainee)
    - currently_working_here: true/false
16. "erp_projects_experience" - ALL ERP project details
    - project_domain: Healthcare, Finance, Retail, Telecom, Energy, Transport, Education, Government, Real Estate, Hospitality, Media, Consumer Goods, Agriculture, Automobiles, IT
    - project_type: Implementation, Roll-out, Support, Specialized Assignments
    - project_phases_involved: Requirement Gathering, CRP, Functional Configuration, Technical Configuration, KUT, UAT, Data Migration, SIT, Post-Go Live Support, Custom Report Building, Integration Building, Custom Solution Building
    - work_location_type: Onsite, Offshore, Work from Home
    - product: Oracle Cloud ERP (Fusion), Oracle Fusion, SAP S/4HANA, etc.
    - track: Business Intelligence (BI), Financials (Fin), Human Capital Management (HCM), Supply Chain Management (SCM)
    - financials_modules: GL, AP, AR, CM, FA, Tax, FR, IC, RM, Exp, Lease Management, Subledger Accounting, Collection, Risk Management
    - hcm_modules: Talent, Absence, ORC, Core HR, Payroll, Benefits, OTL, Compensation, Learn, Enterprise Structure, HCM Data Loader, Self Service HR
    - scm_modules: Shipping, Inventory, Cost Management, Manufacturing, Quality, Supply Chain Financial Orchestration, Planning, Pricing, Order Management, Maintenance, Self-Service Procurement, Purchasing
    - role: Trainee, Associate Consultant, Junior Consultant, Principal Consultant, Senior Consultant, Solution Architect, Test
IMPORTANT:
- Extract ALL available information from the resume
- Use empty string "" or empty array [] if data not found
- Do NOT include markdown (```json) or explanations
- Return ONLY the JSON object

Resume:
{chunk_text}
"""
    
    payload = {
        "model": model_config["model"],
        "messages": [
            {"role": "system", "content": "You are a resume parsing assistant. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "temperature": model_config["temperature"],
        "max_tokens": model_config.get("max_tokens", 2000)
    }
    
    response = requests.post(
        f"{SKYQ_BASE_URL}/api/chat/completions",
        headers=SKYQ_HEADERS,
        json=payload,
        timeout=90
    )
    
    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}: {response.text[:200]}")
    
    result = response.json()
    content = result.get('choices', [{}])[0].get('message', {}).get('content') or result.get('response', '')
    
    if not content:
        raise Exception("Empty response from API")
    
    content = content.strip()
    if '<think>' in content and '</think>' in content:
        content = content[content.find('</think>') + 8:].strip()
    
    content = content.replace('```json', '').replace('```', '').strip()
    
    return json.loads(content)


def parse_resume_with_skyq(resume_text, candidate_name="Unknown", retry_count=0):
    """
    Parse resume using multi-strategy approach:
    1. Try single-pass if resume is short
    2. Use smart truncation for medium resumes  
    3. Use multi-chunk parsing for long resumes
    """
    
    print(f"\n{'='*70}")
    print(f"📄 Parsing Resume - Attempt {retry_count + 1}/4")
    print(f"{'='*70}")
    print(f"Candidate: {candidate_name}")
    print(f"Resume length: {len(resume_text):,} characters")
    
    max_lengths = [9000, 7000, 5500, 4500]
    max_length = max_lengths[min(retry_count, len(max_lengths)-1)]
    
    print(f"Max chunk size: {max_length:,} characters")
    print(f"{'='*70}\n")
    
    if len(resume_text) <= max_length:
        print("✅ Strategy: Single-pass parsing (resume fits in one chunk)")
        return parse_with_single_pass(resume_text, max_length, retry_count)
    
    elif len(resume_text) <= max_length * 1.5:
        print("⚠️  Strategy: Smart truncation (medium length resume)")
        print(f"   Keeping: {int(max_length/len(resume_text)*100)}% of content\n")
        truncated_text, was_truncated = smart_truncate_resume(resume_text, max_length)
        return parse_with_single_pass(truncated_text, max_length, retry_count)
    
    else:
        print("🔄 Strategy: Multi-chunk parsing (long resume)")
        print(f"   Resume is {len(resume_text)/max_length:.1f}x the chunk size\n")
        return parse_with_multi_chunk(resume_text, max_length, retry_count)


def parse_with_single_pass(resume_text, max_length, retry_count):
    """Parse resume in a single pass with all models"""
    
    last_error = None
    
    for idx, config in enumerate(MODEL_CONFIGS):
        try:
            print(f"🤖 Model {idx+1}/{len(MODEL_CONFIGS)}: {config['model']}")
            
            result = parse_single_chunk(resume_text[:max_length], "complete", config)
            
            score = score_resume_completeness(result)
            print(f"   ✅ Success! Completeness: {score}/100\n")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}\n")
            last_error = str(e)
            time.sleep(1)
    
    if retry_count < 3:
        print(f"⚠️  All models failed, retrying with smaller chunk...\n")
        time.sleep(2)
        return parse_resume_with_skyq(resume_text, "Retry", retry_count + 1)
    
    raise Exception(f"All attempts failed. Last error: {last_error}")


def parse_with_multi_chunk(resume_text, max_length, retry_count):
    """Parse long resume using multiple focused chunks"""
    
    chunks = create_focused_chunks(resume_text, max_length)
    print(f"   Created {len(chunks)} focused chunks:\n")
    
    for i, (chunk, desc) in enumerate(chunks, 1):
        print(f"   Chunk {i}: {desc} ({len(chunk):,} chars)")
    
    print()
    
    chunk_results = []
    last_error = None
    
    for idx, config in enumerate(MODEL_CONFIGS):
        try:
            print(f"🤖 Parsing with Model: {config['model']}\n")
            
            temp_results = []
            for i, (chunk, desc) in enumerate(chunks, 1):
                try:
                    print(f"   📋 Chunk {i}/{len(chunks)}: {desc}...")
                    result = parse_single_chunk(chunk, desc, config)
                    temp_results.append(result)
                    print(f"      ✅ Parsed successfully")
                    
                except Exception as e:
                    print(f"      ⚠️  Failed: {str(e)[:80]}")
            
            if temp_results:
                chunk_results = temp_results
                break  
            
        except Exception as e:
            print(f"   ❌ Model failed: {str(e)[:100]}\n")
            last_error = str(e)
            time.sleep(1)
    
    if not chunk_results:
        if retry_count < 3:
            print(f"\n⚠️  Retrying with smaller chunks...\n")
            time.sleep(2)
            return parse_resume_with_skyq(resume_text, "Retry", retry_count + 1)
        raise Exception(f"All parsing attempts failed. Last error: {last_error}")
    
    print(f"\n🔄 Merging {len(chunk_results)} chunk results...")
    merged = merge_parsed_chunks(chunk_results)
    
    score = score_resume_completeness(merged)
    print(f"✅ Final completeness: {score}/100\n")
    
    return merged


def enhance_parsed_data(parsed_data, resume_text):
    """Post-process and enhance parsed resume data"""
    
    for field in ['erp_systems', 'erp_modules', 'technical_skills', 'certifications', 'projects']:
        if field in parsed_data:
            parsed_data[field] = clean_array(parsed_data[field])
    
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
        'Ms Dynamics': 'Microsoft Dynamics',
        'Oracle Cloud': 'Oracle Cloud ERP',
        'Fusion': 'Oracle Fusion'
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
    
    for field in ['technical_skills', 'certifications']:
        if not parsed_data.get(field):
            parsed_data[field] = []
    
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
    
    if parsed_data.get('job_experience') and len(parsed_data['job_experience']) > 0: 
        score += 10
    if parsed_data.get('erp_projects_experience') and len(parsed_data['erp_projects_experience']) > 0:
        score += 10
    if parsed_data.get('current_role'): score += 3
    if parsed_data.get('current_company'): score += 2
    
    if parsed_data.get('education'): score += 5
    if parsed_data.get('technical_skills'): score += 5
    if parsed_data.get('certifications'): score += 5
    
    return min(score, 100)