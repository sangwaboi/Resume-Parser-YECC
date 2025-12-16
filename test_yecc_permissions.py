import requests
import json
import random
from config import YECC_BASE_URL, YECC_HEADERS


def test_endpoint(method, endpoint, description, body=None):
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")
    print(f"Method: {method}")
    print(f"URL: {YECC_BASE_URL}{endpoint}")

    try:
        if method == "GET":
            response = requests.get(f"{YECC_BASE_URL}{endpoint}", headers=YECC_HEADERS, timeout=15)
        elif method == "POST":
            response = requests.post(f"{YECC_BASE_URL}{endpoint}", headers=YECC_HEADERS, json=body, timeout=15)
        elif method == "PUT":
            response = requests.put(f"{YECC_BASE_URL}{endpoint}", headers=YECC_HEADERS, json=body, timeout=15)

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS - Endpoint accessible")
            try:
                data = response.json()
                print(f"Response preview: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(response.text[:200])
        elif response.status_code == 401:
            print("❌ UNAUTHORIZED - Token lacks permission")
            print(response.text)
        else:
            print(f"⚠️ Error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    return response if 'response' in locals() else None


def main():
    print("\n" + "="*60)
    print("🔍 YECC API Permission Tester (Updated Flow)")
    print("="*60)
    print(f"Base URL: {YECC_BASE_URL}")
    print(f"Token (first 20 chars): {YECC_HEADERS.get('Authorization', '')[:20]}...")

    test_endpoint("GET", "/resumeCountry", "Get Country List (public)")
    test_endpoint("GET", "/resumeLanguages", "Get Languages List (public)")

    test_email = f"permission{random.randint(1000,9999)}@example.com"
    test_user_payload = {
        "RoleID": "Candidate",
        "FirstName": "PermTest",
        "LastName": "User",
        "Phone": f"99999{random.randint(10000,99999)}",
        "Email": test_email,
        "City": "Mumbai",
        "CountryCode": "India (+91)",
        "Country": "India",
        "isGetUSERID": True
    }

    res_user = test_endpoint("POST", "/users", "Create User (auth required)", test_user_payload)
    if not res_user or res_user.status_code != 200:
        print("❌ Stopping: User creation failed.")
        return

    user_id = res_user.json().get("data", {}).get("UserID")
    print(f"✅ Created user ID: {user_id}")

    res_url = test_endpoint("POST", f"/ResumeBuilder/generateResumeUrl/{user_id}", "Generate Resume URL")
    if not res_url or res_url.status_code != 200:
        print("❌ Stopping: Resume URL generation failed.")
        return

    resume_slug = res_url.json().get("data")
    print(f"✅ Generated resume slug: {resume_slug}")

    test_endpoint("GET", f"/ResumeBuilder/{resume_slug}", "Initialize Resume (GET required before PUT)")

    test_personal_info = {
        "FirstName": "PermTest",
        "LastName": "User",
        "EmailID": test_email,
        "MobileNumberCountryCode": "India (+91)",
        "MobileNumber": "9999999999",
        "CurrentCity": "Mumbai",
        "CurrentCountry": "India",
        "Nationality": "Indian"
    }
    test_endpoint("PUT", f"/ResumeBuilder/PersonalInfo/{resume_slug}", "Update Personal Info", test_personal_info)

    print("\n" + "="*60)
    print("📊 PERMISSION TEST SUMMARY")
    print("="*60)
    print(f"""
✅ Token works with: /users, /ResumeBuilder/generateResumeUrl, /ResumeBuilder/{resume_slug}
✅ Resume slug created successfully: {resume_slug}

⚠️ If PUT requests still fail with 401 after GET /ResumeBuilder/{resume_slug},
   double-check Authorization header formatting or token role permissions.

🎯 Next: Try your full sync_to_yecc_api() function with this same token.
""")


if __name__ == "__main__":
    main()
