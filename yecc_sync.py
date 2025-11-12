import json
import requests
from config import YECC_BASE_URL, YECC_HEADERS

def _get_lookup_id(endpoint, match_text, key_field="Title"):
    """Fetch ID by partial text match from YECC dropdown endpoint"""
    try:
        res = requests.get(f"{YECC_BASE_URL}/{endpoint}", headers=YECC_HEADERS, timeout=30)
        if res.status_code != 200:
            return None
        items = res.json().get("data", [])
        for item in items:
            if match_text.lower() in item.get(key_field, "").lower():
                return item.get("ID")
        return items[0].get("ID") if items else None
    except Exception:
        return None

def sync_to_yecc_api(parsed_data):
    """Sync parsed resume data to YECC API"""
    try:
        print("\n🔄 Syncing to YECC API...")

        first_name = parsed_data.get("name", "").split()[0] if parsed_data.get("name") else ""
        last_name = " ".join(parsed_data.get("name", "").split()[1:]) if len(parsed_data.get("name", "").split()) > 1 else ""

        user_payload = {
            "RoleID": "Candidate",
            "FirstName": first_name,
            "LastName": last_name,
            "Phone": parsed_data.get("phone", "").replace("+", "").replace("-", "").replace(" ", "")[-10:],
            "Email": parsed_data.get("email", ""),
            "City": parsed_data.get("location", "").split(",")[0].strip() if parsed_data.get("location") else "",
            "CountryCode": "India (+91)",
            "Country": "India",
            "isGetUSERID": True
        }

        print("📤 Step 1: Creating user...")
        res = requests.post(f"{YECC_BASE_URL}/users", headers=YECC_HEADERS, json=user_payload, timeout=30)
        print(f"Response ({res.status_code}): {res.text}")

        if res.status_code != 200:
            print("⚠️ User creation failed.")
            return None

        user_id = res.json().get("data", {}).get("UserID")
        if not user_id:
            print("⚠️ No UserID in response.")
            return None
        print(f"✅ User created with UserID: {user_id}")

        print(f"\n📤 Step 2: Generating resume URL for UserID {user_id}...")
        res = requests.post(
            f"{YECC_BASE_URL}/ResumeBuilder/generateResumeUrl/{user_id}",
            headers=YECC_HEADERS,
            timeout=30
        )
        print(f"Response ({res.status_code}): {res.text}")
        resume_url = res.json().get("data")
        if not resume_url:
            print("⚠️ Resume URL generation failed.")
            return None
        print(f"✅ Resume URL generated: {resume_url}")

        print(f"\n📡 Initializing resume data for URL: {resume_url}")
        init_res = requests.get(f"{YECC_BASE_URL}/ResumeBuilder/{resume_url}", headers=YECC_HEADERS, timeout=30)
        print(f"Initialization Response: {init_res.status_code} {init_res.text[:200]}")

        print("\n📡 Fetching reference IDs...")
        country_id = _get_lookup_id("resumeCountry", "India") or 3
        state_id = _get_lookup_id("resumeState", "Gujarat") or 1
        city_id = _get_lookup_id("resumeCity", "Ahmedabad") or 1
        degree_id = _get_lookup_id("resumeDegree", "Bachelor") or 1
        university_id = _get_lookup_id("resumeUniversity", "University") or 1
        lang_id = _get_lookup_id("resumeLanguages", "English") or 1
        company_id = _get_lookup_id("resumeCompany", "Infosys") or 1
        position_id = _get_lookup_id("resumePosition", "Consultant") or 1

        lookups = {
            "country_id": country_id,
            "state_id": state_id,
            "city_id": city_id,
            "degree_id": degree_id,
            "university_id": university_id,
            "lang_id": lang_id,
            "company_id": company_id,
            "position_id": position_id
        }
        print(f"✅ Lookup IDs: {json.dumps(lookups, indent=2)}")

        print("\n📤 Step 4: Updating resume sections...")
        _update_personal_info(parsed_data, resume_url, user_payload, lookups)
        _update_skills(parsed_data, resume_url, lookups)
        _update_experience(parsed_data, resume_url, lookups)
        _update_education(parsed_data, resume_url, lookups)
        _update_certifications(parsed_data, resume_url)

        print("✅ YECC sync complete!")
        return {
            "user_id": user_id,
            "resume_url": resume_url,
            "yecc_profile_url": f"https://beta.yecc.tech/Resume/{resume_url}"
        }

    except Exception as e:
        print(f"⚠️ YECC sync error: {e}")
        return None

def _update_personal_info(parsed_data, resume_url, user_payload, lookups):
    try:
        personal_info_payload = {
            "EmailID": parsed_data.get("email", ""),
            "MobileNumberCountryCode": "India (+91)",
            "MobileNumber": parsed_data.get("phone", "").replace("+", "").replace("-", "").replace(" ", "")[-10:],
            "LinkedInProfileLink": parsed_data.get("linkedin", ""),
            "FirstName": user_payload["FirstName"],
            "LastName": user_payload["LastName"],
            "ProfileHeadline": parsed_data.get("current_role", "") or "ERP Consultant",
            "CurrentCityID": lookups["city_id"],
            "CurrentCity": user_payload["City"] or "Ahmedabad",
            "CurrentStateID": lookups["state_id"],
            "CurrentState": "Gujarat",
            "CurrentCountryID": lookups["country_id"],
            "CurrentCountry": "India",
            "AboutMe": parsed_data.get("summary", ""),
            "Gender": "",
            "MaritalStatus": "",
            "Nationality": "Indian",
            "PassportAvailable": "No",
            "Travel": "No",
            "Relocation": "No",
            "NightShift": "No",
            "OpenForWork": "Yes"
        }

        print("   → Updating personal info...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/PersonalInfo/{resume_url}", headers=YECC_HEADERS, json=personal_info_payload, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Personal info error: {e}")


def _update_skills(parsed_data, resume_url, lookups):
    try:
        skills = [{"Title": s.strip()} for s in parsed_data.get("technical_skills", [])[:20]]
        payload = {"Skills": skills, "Languages": [{"Title": "English", "LanguageID": lookups["lang_id"]}]}

        print(f"   → Updating skills ({len(skills)} skills)...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/ContactInfo/{resume_url}", headers=YECC_HEADERS, json=payload, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Skills error: {e}")


def _update_experience(parsed_data, resume_url, lookups):
    try:
        exps = []
        for exp in parsed_data.get("experience", [])[:3]:
            exps.append({
                "Position": exp.get("role", "") or "Consultant",
                "PositionID": lookups["position_id"],
                "EmploymentType": "Full-time",
                "CompanyName": exp.get("company", "") or "Infosys",
                "CompanyID": lookups["company_id"],
                "FromDate": "2020-01-01T18:30:00.000Z",
                "ToDate": "2021-01-01T18:30:00.000Z",
                "isPresent": False,
                "Location": "India",
                "ShortDescription": exp.get("responsibilities", ""),
                "FromDateMonth": "01",
                "FromDateYear": "2020",
                "ToDateMonth": "01",
                "ToDateYear": "2021"
            })
        if not exps:
            print("   ⚠️ No experience data to update.")
            return
        print(f"   → Updating experience ({len(exps)} entries)...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/Experiences/{resume_url}", headers=YECC_HEADERS, json=exps, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Experience error: {e}")


def _update_education(parsed_data, resume_url, lookups):
    try:
        edus = []
        for edu in parsed_data.get("education", [])[:3]:
            edus.append({
                "Type": "Degree",
                "Grade": "",
                "Degree": edu.get("degree", ""),
                "DegreeID": lookups["degree_id"],
                "University": edu.get("university", ""),
                "UniversityID": lookups["university_id"],
                "FromDate": "2019-06-01T18:30:00.000Z",
                "ToDate": "2022-06-01T18:30:00.000Z",
                "isPresent": False,
                "FromDateMonth": "06",
                "FromDateYear": "2019",
                "ToDateMonth": "06",
                "ToDateYear": "2022",
                "ShortDescription": ""
            })
        if not edus:
            print("   ⚠️ No education data to update.")
            return
        print(f"   → Updating education ({len(edus)} entries)...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/EducationCertifications/{resume_url}", headers=YECC_HEADERS, json=edus, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Education error: {e}")


def _update_certifications(parsed_data, resume_url):
    try:
        certs = []
        for cert in parsed_data.get("certifications", [])[:5]:
            certs.append({
                "Type": "Certification",
                "FromDate": "2023-12-31T18:30:00.000Z",
                "isPresent": True,
                "ToDate": None,
                "CertificateName": cert,
                "IssuingOrganization": "Oracle University",
                "CredentialURL": "",
                "ShortDescription": "",
                "FromDateMonth": "01",
                "FromDateYear": "2024"
            })
        if not certs:
            print("   ⚠️ No certifications to update.")
            return
        print(f"   → Updating certifications ({len(certs)} entries)...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/Certifications/{resume_url}", headers=YECC_HEADERS, json=certs, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Certifications error: {e}")
