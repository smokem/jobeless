import requests
import json

BASE_URL = "http://localhost:8000/api/generation"
COMPANY_ID = "tgt_1777922092_0_mock" # Using the one found in logs

def test_json_endpoints():
    print(f"Testing JSON endpoints for {COMPANY_ID}...")
    
    # 1. Test GET
    resp = requests.get(f"{BASE_URL}/cv/json/{COMPANY_ID}")
    if resp.status_code == 200:
        cv_json = resp.json()
        print("GET CV JSON: Success")
        
        # 2. Modify and PATCH
        cv_json["header"]["name"] = "Zied Cherif (Modified)"
        patch_resp = requests.patch(f"{BASE_URL}/cv/{COMPANY_ID}", json=cv_json)
        
        if patch_resp.status_code == 200:
            print("PATCH CV JSON: Success")
            
            # 3. Verify PDF was re-rendered (check file size or just trust the 200)
            print("PDF should be re-rendered now.")
        else:
            print(f"PATCH CV JSON: Failed {patch_resp.status_code} {patch_resp.text}")
    else:
        print(f"GET CV JSON: Failed {resp.status_code} {resp.text}")

if __name__ == "__main__":
    # Ensure server is running beforehand or skip if not possible. 
    # Since I'm in a background task, I assume the server is running on 8000.
    try:
        test_json_endpoints()
    except Exception as e:
        print(f"Error: {e}")
