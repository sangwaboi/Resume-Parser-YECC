from flask import Flask, render_template, request, jsonify, send_file
import requests
import PyPDF2
import docx
import json
import pandas as pd
import os
import time
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc'}

SKYQ_BASE_URL = "https://ai.skyq.tech"
SKYQ_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQ5NTIzM2VhLTYxY2ItNDY1NC05MGI4LTFkNjRhZGI0ZjE0YiJ9.bBlFzDMgLkNNim-8jGBXBeIkBNYC9HBqEvPPkgjRv3Q"
SKYQ_HEADERS = {
    "Authorization": f"Bearer {SKYQ_JWT_TOKEN}",
    "Content-Type": "application/json"
}

EXCEL_FILE = 'resumes_database.xlsx'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file_path):
    """Extract text from Word document"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        raise Exception(f"Failed to extract text from Word document: {str(e)}")

def enhance_parsed_data(parsed_data, resume_text):
    """Post-process and enhance parsed resume data"""
    import re
    
    if not parsed_data.get('email'):
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, resume_text)
        if emails:
            parsed_data['email'] = emails[0]
    
    if not parsed_data.get('phone'):
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        phones = re.findall(phone_pattern, resume_text)
        if phones:
            parsed_data['phone'] = phones[0].strip()
    
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
    
    expanded_modules = set(parsed_data.get('erp_modules', []))
    for module in list(expanded_modules):
        if module in module_mappings:
            expanded_modules.update(module_mappings[module])
    parsed_data['erp_modules'] = list(expanded_modules)
    
    if not parsed_data.get('total_years_experience'):
        years_pattern = r'(\d+)[\+]?\s*(?:years?|yrs?)'
        years_matches = re.findall(years_pattern, resume_text.lower())
        if years_matches:
            parsed_data['total_years_experience'] = max(map(int, years_matches))
        elif parsed_data.get('experience'):
            total_years = 0
            for exp in parsed_data['experience']:
                duration = exp.get('duration', '')
                year_ranges = re.findall(r'(\d{4})', duration)
                if len(year_ranges) >= 2:
                    try:
                        years = int(year_ranges[-1]) - int(year_ranges[0])
                        total_years += max(0, years)
                    except:
                        pass
            if total_years > 0:
                parsed_data['total_years_experience'] = str(total_years)
    
    if not parsed_data.get('linkedin'):
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+'
        linkedin = re.findall(linkedin_pattern, resume_text, re.IGNORECASE)
        if linkedin:
            parsed_data['linkedin'] = linkedin[0]
    
    if not parsed_data.get('technical_skills'):
        parsed_data['technical_skills'] = []
    
    if not parsed_data.get('certifications'):
        parsed_data['certifications'] = []
    
    return parsed_data

def score_resume_completeness(parsed_data):
    """Score how complete the parsed resume is (0-100)"""
    score = 0
    max_score = 100
    
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
    
    max_lengths = [5000, 4000, 3000, 2500]  
    max_length = max_lengths[min(retry_count, len(max_lengths)-1)]
    truncated_text = resume_text[:max_length]
    
    prompt = f"""Extract information from this ERP Consultant resume. Return ONLY valid JSON (no markdown, no explanations):
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
  "experience": [{{"company": "", "role": "", "duration": "", "responsibilities": ""}}],
  "education": [{{"degree": "", "university": "", "year": ""}}],
  "technical_skills": [],
  "certifications": [],
  "projects": []
}}

IMPORTANT:
- Extract ALL ERP systems (SAP, Oracle, Microsoft Dynamics, NetSuite, etc.) and modules (FI, CO, MM, SD, HR, etc.)
- Calculate total_years_experience from dates or "X years" phrases
- Include variations: D365=Dynamics 365, EBS=Oracle E-Business Suite, FICO=FI+CO
- Use "" or [] if info not found

Resume:
{truncated_text}
"""
    
    model_configs = [
        {"model": "llama3:8b", "temperature": 0.1, "max_tokens": 1500},  
        {"model": "llama3.2:3b", "temperature": 0.1, "max_tokens": 1500}, 
        {"model": "deepseek-r1:8b", "temperature": 0.1, "max_tokens": 1500},
        {"model": "gpt-oss:20b", "temperature": 0.1, "max_tokens": 1500},
    ]
    
    last_error = None
    
    for idx, config in enumerate(model_configs):
        try:
            print(f"Attempt {retry_count+1}, Model {idx+1}/{len(model_configs)}: {config['model']} (text: {len(truncated_text)} chars)")
            
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

def upload_resume_to_docs(resume_text, filename, parsed_data):
    """Upload resume to Open WebUI for RAG capabilities - Improved"""
    try:
        doc_content = f"""CANDIDATE PROFILE
==================
Name: {parsed_data.get('name', 'Unknown')}
Email: {parsed_data.get('email', 'N/A')}
Phone: {parsed_data.get('phone', 'N/A')}
Location: {parsed_data.get('location', 'N/A')}
LinkedIn: {parsed_data.get('linkedin', 'N/A')}

CURRENT POSITION
================
Role: {parsed_data.get('current_role', 'N/A')}
Company: {parsed_data.get('current_company', 'N/A')}
Total Experience: {parsed_data.get('total_years_experience', 'N/A')} years

ERP EXPERTISE
=============
Systems: {', '.join(parsed_data.get('erp_systems', ['None specified']))}
Modules: {', '.join(parsed_data.get('erp_modules', ['None specified']))}

TECHNICAL SKILLS
================
{', '.join(parsed_data.get('technical_skills', ['None specified']))}

CERTIFICATIONS
==============
{', '.join(parsed_data.get('certifications', ['None specified']))}

PROFESSIONAL SUMMARY
====================
{parsed_data.get('summary', 'No summary available')}

WORK EXPERIENCE
===============
"""
        for exp in parsed_data.get('experience', []):
            doc_content += f"\n{exp.get('role', 'Role')} at {exp.get('company', 'Company')}\n"
            doc_content += f"Duration: {exp.get('duration', 'N/A')}\n"
            doc_content += f"{exp.get('responsibilities', 'No details')}\n"
        
        doc_content += f"\n\nFULL RESUME TEXT\n{'='*50}\n{resume_text[:4000]}\n"
        
        local_docs_dir = 'docs_for_rag'
        os.makedirs(local_docs_dir, exist_ok=True)
        
        safe_name = parsed_data.get('name', 'unknown').replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        local_filename = f"resume_{safe_name}_{timestamp}.txt"
        local_path = os.path.join(local_docs_dir, local_filename)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✅ Document saved locally: {local_path}")
        
        try:
            with open(local_path, 'rb') as f:
                files = {'file': (local_filename, f, 'text/plain')}
                headers = {
                    'Authorization': f"Bearer {SKYQ_JWT_TOKEN}",
                    'Accept': 'application/json'
                }
                
                response = requests.post(
                    f"{SKYQ_BASE_URL}/api/v1/files/",
                    headers=headers,
                    files=files,
                    timeout=30
                )
                
                print(f"Upload response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"Upload response: {json.dumps(result, indent=2)}")
                    
                    file_id = (result.get('id') or 
                              result.get('file_id') or 
                              result.get('data', {}).get('id') or
                              result.get('data', {}).get('file_id'))
                    
                    if file_id:
                        print(f"✅ Uploaded to Open WebUI RAG: file_id={file_id}")
                        parsed_data['_rag_file_id'] = file_id
                        return True
                    else:
                        print(f"⚠️  No file_id in response: {result}")
                        print(f"💡 File saved locally at {local_path} for manual upload")
                else:
                    error_text = response.text[:500]
                    print(f"⚠️  Upload failed ({response.status_code}): {error_text}")
                    print(f"💡 File saved locally at {local_path} for manual upload")
                    
        except requests.exceptions.Timeout:
            print(f"⚠️  Upload timeout - file saved locally at {local_path}")
        except Exception as upload_error:
            print(f"⚠️  RAG upload error: {upload_error}")
            print(f"💡 File saved locally at {local_path} for manual upload")
        
        return True
        
    except Exception as e:
        print(f"❌ Document save error: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_to_excel(parsed_data):
    """Save parsed resume data to Excel"""
    try:
        flat_data = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Name': parsed_data.get('name', ''),
            'Email': parsed_data.get('email', ''),
            'Phone': parsed_data.get('phone', ''),
            'Location': parsed_data.get('location', ''),
            'LinkedIn': parsed_data.get('linkedin', ''),
            'Summary': parsed_data.get('summary', ''),
            'Total_Years_Experience': parsed_data.get('total_years_experience', ''),
            'Current_Role': parsed_data.get('current_role', ''),
            'Current_Company': parsed_data.get('current_company', ''),
            'ERP_Systems': ', '.join(parsed_data.get('erp_systems', [])),
            'ERP_Modules': ', '.join(parsed_data.get('erp_modules', [])),
            'Technical_Skills': ', '.join(parsed_data.get('technical_skills', [])),
            'Certifications': ', '.join(parsed_data.get('certifications', [])),
            'Education': json.dumps(parsed_data.get('education', [])),
            'Experience': json.dumps(parsed_data.get('experience', [])),
            'Projects': json.dumps(parsed_data.get('projects', [])),
            'RAG_File_ID': parsed_data.get('_rag_file_id', ''),  # Store RAG file ID
            'Completeness_Score': parsed_data.get('_completeness_score', 0)
        }
        
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            df = pd.concat([df, pd.DataFrame([flat_data])], ignore_index=True)
        else:
            df = pd.DataFrame([flat_data])
        
        df.to_excel(EXCEL_FILE, index=False)
        print(f"✅ Data saved to {EXCEL_FILE}")
        return True
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        raise Exception(f"Failed to save data to Excel: {str(e)}")

def fuzzy_match_name(candidate_name, df):
    """
    Flexible name matching with multiple strategies
    Returns: (matched, row_dict) or (False, None)
    """
    candidate_name = candidate_name.strip().lower()
    
    if not candidate_name:
        return False, None
    
    for idx, row in df.iterrows():
        excel_name = str(row.get('Name', '')).strip().lower()
        
        if not excel_name:
            continue
        
        if candidate_name == excel_name:
            return True, row.to_dict()
        
        if candidate_name in excel_name or excel_name in candidate_name:
            return True, row.to_dict()
        
        candidate_parts = candidate_name.split()
        excel_parts = excel_name.split()
        
        if len(candidate_parts) >= 2 and len(excel_parts) >= 2:
            if (candidate_parts[0] in excel_parts or excel_parts[0] in candidate_parts) and \
               (candidate_parts[-1] in excel_parts or excel_parts[-1] in candidate_parts):
                return True, row.to_dict()
        
        if len(candidate_parts) >= 2 and len(excel_parts) >= 2:
            matching_parts = sum(1 for part in candidate_parts if any(part in ep for ep in excel_parts))
            if matching_parts >= len(candidate_parts) * 0.6: 
                return True, row.to_dict()
    
    return False, None

def search_with_rag(search_query):
    """Search using RAG with uploaded files - Improved error handling"""
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        file_references = []
        for idx, row in df.iterrows():
            file_id = row.get('RAG_File_ID', '')
            if file_id and file_id != '':
                file_references.append({'type': 'file', 'id': file_id})
        
        if not file_references:
            print("⚠️  No RAG files available, using AI search")
            return search_with_ai(search_query)
        
        print(f"🔍 RAG search with {len(file_references)} resume files")
        
        system_prompt = """You are a resume matching assistant. Analyze the provided resume documents and return matching candidates.
You MUST respond with ONLY a valid JSON array. No explanations, no markdown, no thinking process.
Format: [{"candidate_name": "Full Name", "score": 0-100, "reason": "brief reason"}]"""
        
        candidate_references = []
        for idx, row in df.iterrows():
            name = str(row.get('Name', 'Unknown')).strip()
            role = str(row.get('Current_Role', 'N/A')).strip()
            erp = str(row.get('ERP_Systems', 'N/A')).strip()
            modules = str(row.get('ERP_Modules', 'N/A')).strip()
            
            candidate_references.append(
                f"Candidate #{idx}: {name} | {role} | ERP: {erp} | Modules: {modules}"
            )
        
        candidates_list = "\n".join(candidate_references[:20])
        
        user_prompt = f"""Search Query: "{search_query}"

CANDIDATES IN DATABASE:
{candidates_list}

Analyze the resume documents and match candidates from the list above.
Return candidate numbers (indices) that match the search criteria.

Return format (ONLY this JSON):
[
  {{"candidate_index": 0, "score": 95, "reason": "10 years SAP FICO experience"}},
  {{"candidate_index": 1, "score": 85, "reason": "Oracle EBS expertise"}}
]

CRITICAL: Use candidate_index (the number after #) not names.
Return [] if no matches.
Return ONLY the JSON array."""
        
        models_to_try = [
            "llama3.2:3b",    
            "llama3:8b",     
            "deepseek-r1:8b",
        ]
        
        for model_name in models_to_try:
            try:
                print(f"  Trying model: {model_name}")
                
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "files": file_references[:15], 
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
                
                response = requests.post(
                    f"{SKYQ_BASE_URL}/api/chat/completions",
                    headers=SKYQ_HEADERS,
                    json=payload,
                    timeout=90
                )
                
                print(f"  Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"  Error response: {response.text[:200]}")
                    continue
                
                result = response.json()
                
                content = None
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0].get('message', {}).get('content', '')
                elif 'response' in result:
                    content = result.get('response', '')
                
                if not content or content.strip() == '':
                    print(f"  Empty content from {model_name}")
                    continue
                
                print(f"  Response preview: {content[:100]}...")
                
                content = content.strip()
                
                if '<think>' in content and '</think>' in content:
                    think_end = content.find('</think>')
                    if think_end != -1:
                        content = content[think_end + 8:].strip()
                        print("  Removed reasoning tags")
                
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                if '[' in content:
                    json_start = content.find('[')
                    content = content[json_start:]
                if ']' in content:
                    json_end = content.rfind(']') + 1
                    content = content[:json_end]
                
                try:
                    matches = json.loads(content)
                    
                    if not isinstance(matches, list):
                        print(f"  Response is not a list: {type(matches)}")
                        continue
                    
                    print(f"  ✅ Successfully parsed {len(matches)} matches from {model_name}")
                    
                    results = []
                    for match in matches:
                        idx = match.get('candidate_index', match.get('candidate_number', -1))
                        
                        if idx < 0:
                            candidate_name = match.get('candidate_name', '').strip()
                            if candidate_name:
                                matched, resume_data = fuzzy_match_name(candidate_name, df)
                                if matched and resume_data:
                                    for key, value in resume_data.items():
                                        if pd.isna(value):
                                            resume_data[key] = ''
                                    resume_data['relevance_score'] = match.get('score', 80)
                                    resume_data['match_reason'] = match.get('reason', 'RAG matched')
                                    results.append(resume_data)
                                    print(f"  ✓ Matched by name: {candidate_name}")
                            continue
                        
                        if 0 <= idx < len(df):
                            resume_data = df.iloc[idx].to_dict()
                            
                            for key, value in resume_data.items():
                                if pd.isna(value):
                                    resume_data[key] = ''
                            
                            resume_data['relevance_score'] = match.get('score', 80)
                            resume_data['match_reason'] = match.get('reason', 'RAG matched')
                            results.append(resume_data)
                            print(f"  ✓ Matched by index: {idx} ({resume_data.get('Name', 'Unknown')})")
                        else:
                            print(f"  ✗ Invalid index: {idx}")
                    
                    if results:
                        print(f"✅ RAG search found {len(results)} matches")
                        return results
                    else:
                        print(f"  No matching records found in database")
                        
                except json.JSONDecodeError as je:
                    print(f"  JSON parse error with {model_name}: {je}")
                    print(f"  Attempted to parse: {content[:200]}")
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"  Timeout with {model_name}")
                continue
            except Exception as e:
                print(f"  Error with {model_name}: {e}")
                continue
        
        print("⚠️  All RAG models failed, using AI search fallback")
        return search_with_ai(search_query)
        
    except Exception as e:
        print(f"❌ RAG search critical error: {e}")
        import traceback
        traceback.print_exc()
        return search_with_ai(search_query)

def search_with_ai(search_query):
    """Search using AI when RAG is not available - Improved"""
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        if len(df) == 0:
            print("Database is empty")
            return []
        
        candidates_summary = []
        for idx, row in df.head(20).iterrows():
            summary = f"""Candidate #{idx+1}:
Name: {row.get('Name', 'Unknown')}
Role: {row.get('Current_Role', 'N/A')} at {row.get('Current_Company', 'N/A')}
Experience: {row.get('Total_Years_Experience', 'N/A')} years
ERP Systems: {row.get('ERP_Systems', 'None')}
Modules: {row.get('ERP_Modules', 'None')}
Skills: {str(row.get('Technical_Skills', ''))[:100]}
Location: {row.get('Location', 'N/A')}
---"""
            candidates_summary.append(summary)
        
        system_prompt = """You are a technical recruiter analyzing candidate profiles.
Return ONLY a valid JSON array of matching candidates.
No explanations, no markdown, no thinking tags."""
        
        user_prompt = f"""Search Query: "{search_query}"

Analyze these candidates and return matches as a JSON array.
Score each match from 0-100 based on relevance.

CANDIDATES:
{chr(10).join(candidates_summary)}

Return format (ONLY this JSON, nothing else):
[
  {{"candidate_number": 1, "score": 95, "reason": "Strong match explanation"}},
  {{"candidate_number": 3, "score": 80, "reason": "Partial match explanation"}}
]

Return [] if no good matches.
CRITICAL: Return ONLY the JSON array."""
        
        models = ["llama3.2:3b", "llama3:8b", "deepseek-r1:8b"]
        
        for model_name in models:
            try:
                print(f"AI search trying: {model_name}")
                
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 1500
                }
                
                response = requests.post(
                    f"{SKYQ_BASE_URL}/api/chat/completions",
                    headers=SKYQ_HEADERS,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code != 200:
                    print(f"  Status {response.status_code}: {response.text[:100]}")
                    continue
                
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                
                if not content:
                    continue
                
                if '<think>' in content and '</think>' in content:
                    content = content[content.find('</think>') + 8:].strip()
                
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                if '[' in content:
                    json_start = content.find('[')
                    json_end = content.rfind(']') + 1
                    content = content[json_start:json_end]
                
                matches = json.loads(content)
                
                if not isinstance(matches, list):
                    continue
                
                results = []
                for match in matches:
                    idx = match.get('candidate_number', 0) - 1
                    if 0 <= idx < len(df):
                        resume_data = df.iloc[idx].to_dict()
                        
                        for key, value in resume_data.items():
                            if pd.isna(value):
                                resume_data[key] = ''
                        
                        resume_data['relevance_score'] = match.get('score', 75)
                        resume_data['match_reason'] = match.get('reason', 'AI matched')
                        results.append(resume_data)
                
                if results:
                    print(f"✅ AI search found {len(results)} matches with {model_name}")
                    return results
                    
            except json.JSONDecodeError as e:
                print(f"  JSON error: {e}")
                continue
            except Exception as e:
                print(f"  Error with {model_name}: {e}")
                continue
        
        print("All AI models failed, using keyword search")
        return fallback_excel_search(search_query)
        
    except Exception as e:
        print(f"❌ AI search critical error: {e}")
        import traceback
        traceback.print_exc()
        return fallback_excel_search(search_query)

def fallback_excel_search(search_query):
    """Simple keyword search in Excel"""
    if not os.path.exists(EXCEL_FILE):
        return []
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        
        df = df.fillna('')
        
        search_lower = search_query.lower()
        
        matched_candidates = []
        for idx, row in df.iterrows():
            searchable_text = ' '.join([
                str(row.get('Name', '')),
                str(row.get('Current_Role', '')),
                str(row.get('ERP_Systems', '')),
                str(row.get('ERP_Modules', '')),
                str(row.get('Technical_Skills', '')),
                str(row.get('Location', ''))
            ]).lower()
            
            if search_lower in searchable_text:
                candidate_data = row.to_dict()
                
                for key, value in candidate_data.items():
                    if pd.isna(value):
                        candidate_data[key] = ''
                
                candidate_data['relevance_score'] = 70
                candidate_data['match_reason'] = f"Keyword match: {search_query}"
                matched_candidates.append(candidate_data)
        
        print(f"Keyword search found {len(matched_candidates)} matches")
        return matched_candidates
    except Exception as e:
        print(f"Fallback search error: {e}")
        return []

# Routes
@app.route('/')
def home():
    return render_template('Home.html')

@app.route('/resume')
def resume():
    return render_template('Resume.html')

@app.route('/search')
def search_page():
    return render_template('Search.html')

@app.route('/upload', methods=['POST'])
def upload_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"\n📄 File saved: {filepath}")
        
        try:
            if filename.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(filepath)
            else:
                resume_text = extract_text_from_docx(filepath)
            
            print(f"📝 Extracted {len(resume_text)} characters")
            
            if len(resume_text) < 50:
                raise Exception("File appears empty or corrupted")
            
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'Text extraction failed: {str(e)}'}), 500
        
        try:
            parsed_data = parse_resume_with_skyq(resume_text, filename)
            
            if not parsed_data:
                raise Exception('No data returned from AI')
            
            parsed_data = enhance_parsed_data(parsed_data, resume_text)
            print("✅ Data enhanced with post-processing")
            
            completeness_score = score_resume_completeness(parsed_data)
            print(f"📊 Resume completeness: {completeness_score}%")
            parsed_data['_completeness_score'] = completeness_score
            
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'AI parsing failed: {str(e)}'}), 500
        
        upload_resume_to_docs(resume_text, filename, parsed_data)
        
        try:
            save_to_excel(parsed_data)
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'error': f'Database save failed: {str(e)}'}), 500
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': 'Resume parsed and saved successfully',
            'data': parsed_data
        })
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        print(f"\n🔍 Searching for: {query}")
        
        results = search_with_rag(query)
        
        if not results:
            print("RAG returned no results, using AI search...")
            results = search_with_ai(query)
        
        if not results:
            print("AI search failed, using keyword search...")
            results = fallback_excel_search(query)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-database')
def download_database():
    if os.path.exists(EXCEL_FILE):
        return send_file(EXCEL_FILE, as_attachment=True)
    return jsonify({'error': 'No database found'}), 404

@app.route('/api/stats')
def get_stats():
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            return jsonify({'success': True, 'count': len(df)})
        return jsonify({'success': True, 'count': 0})
    except Exception as e:
        return jsonify({'success': False, 'count': 0, 'error': str(e)})

@app.route('/api/clean-database', methods=['POST'])
def clean_database():
    """Clean NaN values from existing database"""
    try:
        if not os.path.exists(EXCEL_FILE):
            return jsonify({'success': False, 'error': 'No database found'}), 404
        
        df = pd.read_excel(EXCEL_FILE)
        original_count = len(df)
        
        df = df.fillna('')
        
        df.to_excel(EXCEL_FILE, index=False)
        
        return jsonify({
            'success': True,
            'message': f'Database cleaned successfully',
            'records': original_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug-database', methods=['GET'])
def debug_database():
    """Debug endpoint to see what's in the database"""
    try:
        if not os.path.exists(EXCEL_FILE):
            return jsonify({'success': False, 'error': 'No database found'}), 404
        
        df = pd.read_excel(EXCEL_FILE)
        df = df.fillna('')
        
        candidates_info = []
        for idx, row in df.iterrows():
            candidates_info.append({
                'index': idx + 1,
                'name': row.get('Name', 'N/A'),
                'role': row.get('Current_Role', 'N/A'),
                'company': row.get('Current_Company', 'N/A'),
                'erp_systems': row.get('ERP_Systems', 'N/A'),
                'rag_file_id': row.get('RAG_File_ID', 'N/A'),
                'has_rag_file': bool(row.get('RAG_File_ID', ''))
            })
        
        return jsonify({
            'success': True,
            'total_records': len(df),
            'records_with_rag': sum(1 for c in candidates_info if c['has_rag_file']),
            'candidates': candidates_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 YourERPCoach Resume Parser - SkyQ AI Edition")
    print("="*60)
    print("✅ SkyQ AI token configured")
    print("📊 Using models: llama3.2:3b, llama3:8b, deepseek-r1:8b")
    print("🔍 RAG-enabled search with fallback mechanisms")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)