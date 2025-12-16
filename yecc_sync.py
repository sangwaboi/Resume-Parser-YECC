import json
import requests
from config import YECC_BASE_URL, YECC_HEADERS

def _get_lookup_id(endpoint, match_text, key_field="Title"):
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
    try:
        print("\n🔄 Syncing to YECC API...")

        first_name = parsed_data.get("name", "").split()[0] if parsed_data.get("name") else ""
        last_name = " ".join(parsed_data.get("name", "").split()[1:]) if len(parsed_data.get("name", "").split()) > 1 else ""

        user_payload = {
            "RoleID": "Trainee",
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

        response_data = res.json().get("data", {})
        user_id = response_data.get("UserID")
        user_token = response_data.get("token")
        
        if not user_id:
            print("⚠️ No UserID in response.")
            return None
        print(f"✅ User created with UserID: {user_id}")
        
        if user_token:
            print(f"🔑 Using user's token for resume builder calls...")
            user_headers = YECC_HEADERS.copy()
            user_headers["Authorization"] = user_token
        else:
            print("⚠️ No user token returned, using admin token...")
            user_headers = YECC_HEADERS

        print(f"\n📤 Step 2: Generating resume URL for UserID {user_id}...")
        res = requests.post(
            f"{YECC_BASE_URL}/ResumeBuilder/generateResumeUrl/{user_id}",
            headers=user_headers,
            timeout=30
        )
        print(f"Response ({res.status_code}): {res.text}")
        if res.status_code != 200:
            print("⚠️ Resume URL generation failed.")
            return None

        resume_url = res.json().get("data")
        if not resume_url:
            print("⚠️ No resume URL in response.")
            return None
        print(f"✅ Resume URL generated: {resume_url}")

        print(f"\n📡 Initializing resume data for URL: {resume_url}")
        init_res = requests.get(
            f"{YECC_BASE_URL}/ResumeBuilder/{resume_url}",
            headers=user_headers,
            timeout=30
        )
        print(f"Initialization Response: {init_res.status_code} {init_res.text[:200]}")
        if init_res.status_code != 200:
            print("⚠️ Resume initialization failed. PUT calls may not work correctly.")
        else:
            print("✅ Resume context initialized successfully.")

        print("\n📡 Fetching reference IDs...")
        lookups = {
            "country_id": _get_lookup_id("resumeCountry", "India") or 3,
            "state_id": _get_lookup_id("resumeState", "Gujarat") or 1,
            "city_id": _get_lookup_id("resumeCity", "Ahmedabad") or 1,
            "degree_id": _get_lookup_id("resumeDegree", "Bachelor") or 1,
            "university_id": _get_lookup_id("resumeUniversity", "University") or 1,
            "lang_id": _get_lookup_id("resumeLanguages", "English") or 1,
            "company_id": _get_lookup_id("resumeCompany", "Infosys") or 1,
            "position_id": _get_lookup_id("resumePosition", "Consultant") or 1
        }
        print(f"✅ Lookup IDs: {json.dumps(lookups, indent=2)}")

        print("\n📤 Step 5: Updating resume sections...")
        _update_personal_info(parsed_data, resume_url, user_payload, lookups, user_headers)
        _update_skills(parsed_data, resume_url, lookups, user_headers)
        _update_experience(parsed_data, resume_url, lookups, user_headers)
        _update_erp_projects(parsed_data, resume_url, lookups, user_headers)
        _update_education(parsed_data, resume_url, lookups, user_headers)
        _update_certifications(parsed_data, resume_url, user_headers)

        print("✅ YECC sync complete!")
        return {
            "user_id": user_id,
            "resume_url": resume_url,
            "yecc_profile_url": f"https://yecc.tech/Resume/{resume_url}"
        }

    except Exception as e:
        print(f"⚠️ YECC sync error: {e}")
        return None


def _update_personal_info(parsed_data, resume_url, user_payload, lookups, headers):
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
            "Nationality": "Indian",
            "PassportAvailable": "No",
            "Travel": "No",
            "Relocation": "No",
            "NightShift": "No",
            "OpenForWork": "Yes"
        }

        print("   → Updating personal info...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/PersonalInfo/{resume_url}",
                           headers=headers, json=personal_info_payload, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Personal info error: {e}")


def _update_skills(parsed_data, resume_url, lookups, headers):
    try:
        all_skills = []
        
        for s in parsed_data.get("technical_skills", []):
            if s and s.strip():
                all_skills.append(s.strip())
        
        for m in parsed_data.get("erp_modules", []):
            if m and m.strip() and m.strip() not in all_skills:
                all_skills.append(m.strip())
        
        for e in parsed_data.get("erp_systems", []):
            if e and e.strip() and e.strip() not in all_skills:
                all_skills.append(e.strip())
        
        skills = [{"Title": s} for s in all_skills[:25]]
        payload = {"Skills": skills, "Languages": [{"Title": "English", "LanguageID": lookups["lang_id"]}]}

        print(f"   → Updating skills ({len(skills)} skills)...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/ContactInfo/{resume_url}",
                           headers=headers, json=payload, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Skills error: {e}")


def _update_experience(parsed_data, resume_url, lookups, headers):
    try:
        exps = []
        job_experiences = parsed_data.get("job_experience", [])
        erp_projects = parsed_data.get("erp_projects_experience", [])
        
        for exp in job_experiences[:5]:
            position = exp.get("position", "") or exp.get("role", "") or "Consultant"
            company = exp.get("company_name", "") or exp.get("company", "") or "Company"
            description = exp.get("short_description", "") or exp.get("responsibilities", "") or ""
            is_current = exp.get("currently_working_here", False)
            from_date = exp.get("from_date", "")
            to_date = exp.get("to_date", "")
            location = exp.get("country", "") or "India"
            
            from_year = "2020"
            from_month = "01"
            to_year = "2021" 
            to_month = "01"
            
            if from_date:
                parts = from_date.replace(",", "").split()
                if len(parts) >= 2:
                    from_year = parts[-1] if parts[-1].isdigit() else "2020"
                    month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                                "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                    from_month = month_map.get(parts[0][:3].lower(), "01")
                elif len(parts) == 1 and parts[0].isdigit():
                    from_year = parts[0]
            
            if to_date and not is_current:
                parts = to_date.replace(",", "").split()
                if len(parts) >= 2:
                    to_year = parts[-1] if parts[-1].isdigit() else "2021"
                    month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                                "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                    to_month = month_map.get(parts[0][:3].lower(), "01")
                elif len(parts) == 1 and parts[0].isdigit():
                    to_year = parts[0]
            
            exps.append({
                "Position": position,
                "PositionID": lookups["position_id"],
                "EmploymentType": exp.get("employment_type", "Full-time") or "Full-time",
                "CompanyName": company,
                "CompanyID": lookups["company_id"],
                "FromDate": f"{from_year}-{from_month}-01T18:30:00.000Z",
                "ToDate": f"{to_year}-{to_month}-01T18:30:00.000Z" if not is_current else None,
                "isPresent": is_current,
                "Location": location,
                "ShortDescription": description[:500] if description else "",
                "FromDateMonth": from_month,
                "FromDateYear": from_year,
                "ToDateMonth": to_month if not is_current else "",
                "ToDateYear": to_year if not is_current else ""
            })
        
        if not exps and erp_projects:
            print(f"   📊 Converting {len(erp_projects)} ERP projects to experience entries...")
            for proj in erp_projects[:3]:
                position = proj.get("role", "") or "ERP Consultant"
                company = proj.get("company_name", "") or proj.get("project_name", "") or "Client Project"
                description = f"Project: {proj.get('project_name', '')}. Domain: {proj.get('project_domain', '')}. Modules: {', '.join(proj.get('financials_modules', []) + proj.get('hcm_modules', []) + proj.get('scm_modules', []))}"
                is_current = proj.get("currently_working_on_this_project", False)
                
                exps.append({
                    "Position": position,
                    "PositionID": lookups["position_id"],
                    "EmploymentType": "Full-time",
                    "CompanyName": company,
                    "CompanyID": lookups["company_id"],
                    "FromDate": "2022-01-01T18:30:00.000Z",
                    "ToDate": None if is_current else "2023-01-01T18:30:00.000Z",
                    "isPresent": is_current,
                    "Location": "India",
                    "ShortDescription": description[:500],
                    "FromDateMonth": "01",
                    "FromDateYear": "2022",
                    "ToDateMonth": "" if is_current else "01",
                    "ToDateYear": "" if is_current else "2023"
                })
        
        if not exps:
            print("   ⚠️ No experience data to update.")
            return
        print(f"   → Updating experience ({len(exps)} entries)...")
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/Experiences/{resume_url}",
                           headers=headers, json=exps, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Experience error: {e}")


def _update_education(parsed_data, resume_url, lookups, headers):
    try:
        educations = []
        for edu in parsed_data.get("education", [])[:3]:
            educations.append({
                "Degree": edu.get("degree", "") or "Bachelor of Technology",
                "DegreeID": lookups.get("degree_id"),
                "University": edu.get("university", "") or "Gujarat Technological University",
                "UniversityID": lookups.get("university_id"),
                "FromDateMonth": "06",
                "FromDateYear": edu.get("year", "") or "2019",
                "ToDateMonth": "05",
                "ToDateYear": "2023",
                "isPresent": False,
                "Grade": "First Class",
                "ShortDescription": ""
            })

        if not educations:
            print("   ⚠️ No education data to update.")
            return

        payload = {"EducationCertifications": educations}

        print(f"   → Updating education ({len(educations)} entries)...")
        res = requests.put(
            f"{YECC_BASE_URL}/ResumeBuilder/EducationCertifications/{resume_url}",
            headers=headers,
            json=payload,
            timeout=30
        )
        print(f"   Response: {res.status_code} {res.text[:200]}")

        if res.status_code == 200:
            print("   ✅ Education updated successfully")
        else:
            print("   ⚠️ Education update failed")

    except Exception as e:
        print(f"   ⚠️ Education error: {e}")

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
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/EducationCertifications/{resume_url}",
                           headers=headers, json=edus, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Education error: {e}")


def _update_certifications(parsed_data, resume_url, headers):
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
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/Certifications/{resume_url}",
                           headers=headers, json=certs, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Certifications error: {e}")


def _update_erp_projects(parsed_data, resume_url, lookups, headers):
    try:
        erp_projects = parsed_data.get("erp_projects_experience", [])
        
        if not erp_projects:
            print("   ⚠️ No ERP projects to update.")
            return
        
        projects = []
        for proj in erp_projects[:5]:
            project_name = proj.get("project_name", "") or "ERP Project"
            company_name = proj.get("company_name", "") or "Client"
            project_domain = proj.get("project_domain", "") or ""
            role = proj.get("role", "") or "ERP Consultant"
            is_current = proj.get("currently_working_on_this_project", False)
            
            all_modules = []
            all_modules.extend(proj.get("financials_modules", []))
            all_modules.extend(proj.get("hcm_modules", []))
            all_modules.extend(proj.get("scm_modules", []))
            modules_str = ", ".join(all_modules) if all_modules else ""
            
            description = f"Domain: {project_domain}. " if project_domain else ""
            description += f"Modules: {modules_str}" if modules_str else ""
            
            projects.append({
                "ProjectName": project_name,
                "CompanyName": company_name,
                "Role": role,
                "Domain": project_domain,
                "Modules": modules_str,
                "FromDate": "2022-01-01T18:30:00.000Z",
                "ToDate": None if is_current else "2023-01-01T18:30:00.000Z",
                "isPresent": is_current,
                "ShortDescription": description[:500],
                "FromDateMonth": "01",
                "FromDateYear": "2022",
                "ToDateMonth": "" if is_current else "01",
                "ToDateYear": "" if is_current else "2023"
            })
        
        print(f"   → Updating ERP projects ({len(projects)} entries)...")
        
        res = requests.put(f"{YECC_BASE_URL}/ResumeBuilder/ERPProjects/{resume_url}",
                           headers=headers, json=projects, timeout=30)
        print(f"   Response: {res.status_code} {res.text[:200]}")
        
    except Exception as e:
        print(f"   ⚠️ ERP Projects error: {e}")
