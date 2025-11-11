import json
import base64
import requests
from config import YECC_BASE_URL, YECC_HEADERS


def sync_to_yecc_api(parsed_data):
    """Sync parsed resume data to YECC API"""
    try:
        print("\n🔄 Syncing to YECC API...")
        
        user_payload = {
            "RoleID": "Candidate",
            "FirstName": parsed_data.get('name', '').split()[0] if parsed_data.get('name') else '',
            "LastName": ' '.join(parsed_data.get('name', '').split()[1:]) if parsed_data.get('name') and len(parsed_data.get('name', '').split()) > 1 else '',
            "Phone": parsed_data.get('phone', '').replace('+', '').replace('-', '').replace(' ', '').replace('91', '')[-10:],
            "Email": parsed_data.get('email', ''),
            "City": parsed_data.get('location', '').split(',')[0].strip() if parsed_data.get('location') else '',
            "CountryCode": "India (+91)",
            "Country": "India"
        }
        
        print(f"Sending user creation payload: {json.dumps(user_payload, indent=2)}")
        
        response = requests.post(
            f"{YECC_BASE_URL}/users",
            headers=YECC_HEADERS,
            json=user_payload,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.text}")
        
        if response.status_code != 200:
            print(f"⚠️  YECC user creation failed: {response.status_code}")
            return None
        
        result = response.json()
        data = result.get('data', {})
        
        if isinstance(data, str):
            if "already registered" in data.lower():
                print(f"⚠️  User already exists: {data}")
                return None
            else:
                print(f"⚠️  Unexpected response: {data}")
                return None
        
        new_token = data.get('token')
        user_id = None
        resume_url = None
        
        if new_token:
            try:
                payload = new_token.split('.')[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                decoded = base64.b64decode(payload)
                token_data = json.loads(decoded)
                user_info = token_data.get('userInfo', {})
                
                encoded_id = user_info.get('ID', '')
                if encoded_id:
                    user_id = base64.b64decode(encoded_id).decode('utf-8')
                
                resume_url = user_info.get('ResumeUrl', '')
                print(f"✅ Decoded from token - UserID: {user_id}, ResumeUrl: {resume_url}")
                
            except Exception as e:
                print(f"⚠️  Could not decode token: {e}")
        
        if not resume_url:
            print("⚠️  No ResumeUrl found in response")
            return None
        
        print(f"✅ YECC User created: UserID={user_id}, ResumeUrl={resume_url}")
        
        _update_personal_info(parsed_data, resume_url, user_payload)
        
        _update_skills(parsed_data, resume_url)
        
        _update_experience(parsed_data, resume_url)
        
        _update_education(parsed_data, resume_url)
        
        _update_certifications(parsed_data, resume_url)
        
        print(f"✅ YECC sync complete!")
        return {
            "user_id": user_id,
            "resume_url": resume_url,
            "yecc_profile_url": f"https://beta.yecc.tech/Resume/{resume_url}"
        }
        
    except Exception as e:
        print(f"⚠️  YECC sync error: {e}")
        return None


def _update_personal_info(parsed_data, resume_url, user_payload):
    """Update personal information in YECC"""
    personal_info_payload = {
        "EmailID": parsed_data.get('email', ''),
        "MobileNumberCountryCode": "India (+91)",
        "MobileNumber": parsed_data.get('phone', '').replace('+', '').replace('-', '').replace(' ', '')[:10],
        "LinkedInProfileLink": parsed_data.get('linkedin', ''),
        "FirstName": user_payload["FirstName"],
        "LastName": user_payload["LastName"],
        "ProfileHeadline": parsed_data.get('current_role', ''),
        "CurrentCity": user_payload["City"],
        "CurrentCountry": "India",
        "AboutMe": parsed_data.get('summary', ''),
        "Gender": "",
        "MaritalStatus": "",
        "Nationality": "Indian",
        "PassportAvailable": "No",
        "Travel": "No",
        "Relocation": "No",
        "NightShift": "No",
        "OpenForWork": "Yes"
    }
    
    response = requests.put(
        f"{YECC_BASE_URL}/ResumeBuilder/PersonalInfo/{resume_url}",
        headers=YECC_HEADERS,
        json=personal_info_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"✅ Personal info updated")


def _update_skills(parsed_data, resume_url):
    """Update skills in YECC"""
    skills_payload = {
        "Skills": [{"Title": skill.strip()} for skill in parsed_data.get('technical_skills', [])[:20]],
        "Languages": [{"Title": "English", "LanguageID": 1}]
    }
    
    response = requests.put(
        f"{YECC_BASE_URL}/ResumeBuilder/ContactInfo/{resume_url}",
        headers=YECC_HEADERS,
        json=skills_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"✅ Skills updated")


def _update_experience(parsed_data, resume_url):
    """Update experience in YECC"""
    if parsed_data.get('experience'):
        experiences = []
        for exp in parsed_data.get('experience', [])[:5]:
            experiences.append({
                "Position": exp.get('role', ''),
                "EmploymentType": "Full-time",
                "CompanyName": exp.get('company', ''),
                "FromDate": None,
                "isPresent": False,
                "ToDate": None,
                "Location": parsed_data.get('location', ''),
                "ShortDescription": exp.get('responsibilities', ''),
                "FromDateMonth": "",
                "FromDateYear": "",
                "ToDateMonth": "",
                "ToDateYear": ""
            })
        
        response = requests.put(
            f"{YECC_BASE_URL}/ResumeBuilder/Experiences/{resume_url}",
            headers=YECC_HEADERS,
            json=experiences,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Experience updated")


def _update_education(parsed_data, resume_url):
    """Update education in YECC"""
    if parsed_data.get('education'):
        education_data = []
        for edu in parsed_data.get('education', [])[:3]:
            education_data.append({
                "Type": "Degree",
                "Degree": edu.get('degree', ''),
                "University": edu.get('university', ''),
                "FromDate": None,
                "isPresent": False,
                "ToDate": None,
                "FromDateMonth": "",
                "FromDateYear": edu.get('year', ''),
                "ToDateMonth": "",
                "ToDateYear": "",
                "Grade": "",
                "ShortDescription": ""
            })
        
        response = requests.put(
            f"{YECC_BASE_URL}/ResumeBuilder/EducationCertifications/{resume_url}",
            headers=YECC_HEADERS,
            json=education_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Education updated")


def _update_certifications(parsed_data, resume_url):
    """Update certifications in YECC"""
    if parsed_data.get('certifications'):
        cert_data = []
        for cert in parsed_data.get('certifications', [])[:5]:
            cert_data.append({
                "Type": "Certification",
                "CertificateName": cert,
                "IssuingOrganization": "",
                "FromDate": None,
                "isPresent": True,
                "ToDate": None,
                "FromDateMonth": "",
                "FromDateYear": "",
                "CredentialURL": "",
                "ShortDescription": ""
            })
        
        response = requests.put(
            f"{YECC_BASE_URL}/ResumeBuilder/Certifications/{resume_url}",
            headers=YECC_HEADERS,
            json=cert_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Certifications updated")