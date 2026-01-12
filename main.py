from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import requests
import uuid
import random
import string
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ==========================================
#  FACEBOOK API LOGIC CLASS
# ==========================================

class FacebookAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016) [FBAN/FB4A;FBAV/407.0.0.30.85;FBLC/en_US;FBBV/457696233;FBCR/T-Mobile;FBMF/samsung;FBBD/samsung;FBDV/SM-G998B;FBSV/12;FBCA/armeabi-v7a:armeabi;FBDM/{density=2.75,width=1080,height=2220};FB_FW/1;]",
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*'
        }
        self.login_url = "https://b-api.facebook.com/method/auth.login"
        self.exchange_url = "https://api.facebook.com/method/auth.getSessionforApp"
        
        # Constants
        self.app_id = "350685531728" 
        self.client_token = "62f8ce9f74b12f84c123cc23437a4a32"
        self.exchange_app_id = "275254692598279" 

    def generate_ids(self):
        """Generates random device identifiers"""
        return {
            "adid": str(uuid.uuid4()),
            "device_id": str(uuid.uuid4()),
            "family_device_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "advertiser_id": str(uuid.uuid4()),
            "reg_instance": str(uuid.uuid4()),
            "machine_id": ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        }

    def exchange_to_eaad(self, access_token):
        """Exchanges Android Token for EAAD6V7"""
        payload = {
            "access_token": access_token,
            "format": "json",
            "new_app_id": self.exchange_app_id,
            "generate_session_cookies": "1"
        }
        try:
            response = requests.post(self.exchange_url, data=payload, headers=self.headers)
            data = response.json()
            return data.get("access_token")
        except:
            return None

    def perform_login(self, email, password):
        """Handles Login Process"""
        ids = self.generate_ids()
        
        payload = {
            "email": email,
            "password": password,
            "adid": ids["adid"],
            "device_id": ids["device_id"],
            "family_device_id": ids["family_device_id"],
            "session_id": ids["session_id"],
            "advertiser_id": ids["advertiser_id"],
            "reg_instance": ids["reg_instance"],
            "machine_id": ids["machine_id"],
            "locale": "en_US",
            "country_code": "US",
            "client_country_code": "US",
            "cpl": "true",
            "source": "login",
            "format": "json",
            "credentials_type": "password",
            "error_detail_type": "button_with_disabled",
            "generate_session_cookies": "1",
            "generate_analytics_claim": "1",
            "generate_machine_id": "1",
            "tier": "regular",
            "device": "SM-G998B",
            "os_ver": "12",
            "app_id": self.app_id,
            "app_ver": "407.0.0.30.85",
            "access_token": f"{self.app_id}|{self.client_token}",
            "api_key": "882a8490361da98702bf97a021ddc14d",
            "sig": self.client_token 
        }

        try:
            response = requests.post(self.login_url, data=payload, headers=self.headers)
            data = response.json()

            # Case 1: Success
            if "access_token" in data:
                eaad_token = self.exchange_to_eaad(data["access_token"])
                final_token = eaad_token if eaad_token else data["access_token"]
                return {"status": "success", "token": final_token}
            
            # Case 2: 2FA Required (Error 406)
            if data.get("error_code") == 406:
                error_data = json.loads(data.get("error_data", "{}"))
                return {
                    "status": "2fa_required",
                    "data": {
                        "uid": error_data.get("uid"),
                        "machine_id": error_data.get("machine_id"),
                        "first_factor": error_data.get("login_first_factor"),
                        "auth_token": error_data.get("auth_token"),
                        "ids": ids
                    }
                }
            
            # Case 3: Error
            return {"status": "error", "message": data.get("error_msg", "Unknown Error")}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def submit_2fa(self, email, password, code, two_fa_data):
        """Handles OTP Submission"""
        if not two_fa_data:
            return {"status": "error", "message": "Missing 2FA Data"}

        ids = two_fa_data.get("ids", self.generate_ids()) # Fallback if IDs missing

        payload = {
            "email": email,
            "password": password,
            "adid": ids["adid"],
            "device_id": ids["device_id"],
            "family_device_id": ids["family_device_id"],
            "session_id": ids["session_id"],
            "locale": "en_US",
            "country_code": "US",
            "client_country_code": "US",
            "format": "json",
            "credentials_type": "two_factor",
            "generate_session_cookies": "1",
            "generate_analytics_claim": "1",
            "generate_machine_id": "1",
            "source": "login",
            "device": "SM-G998B",
            "os_ver": "12",
            "app_id": self.app_id,
            "app_ver": "407.0.0.30.85",
            "access_token": f"{self.app_id}|{self.client_token}",
            "api_key": "882a8490361da98702bf97a021ddc14d",
            "sig": self.client_token,
            "twofactor_code": code,
            "encrypted_msisdn": "",
            "userid": two_fa_data.get("uid"),
            "machine_id": two_fa_data.get("machine_id"),
            "first_factor": two_fa_data.get("first_factor"),
            "auth_token": two_fa_data.get("auth_token")
        }

        try:
            response = requests.post(self.login_url, data=payload, headers=self.headers)
            data = response.json()

            if "access_token" in data:
                eaad_token = self.exchange_to_eaad(data["access_token"])
                final_token = eaad_token if eaad_token else data["access_token"]
                return {"status": "success", "token": final_token}
            
            return {"status": "error", "message": data.get("error_msg", "Invalid Code")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# ==========================================
#  FLASK ROUTING (THE API ENDPOINTS)
# ==========================================

fb_api = FacebookAPI()

@app.route('/login', methods=['POST'])
def api_login():
    """
    Endpoint: /login
    Body: {"email": "...", "password": "..."}
    """
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"status": "error", "message": "Email and Password required"}), 400
        
    result = fb_api.perform_login(data['email'], data['password'])
    return jsonify(result)

@app.route('/submit_2fa', methods=['POST'])
def api_submit_2fa():
    """
    Endpoint: /submit_2fa
    Body: {"email": "...", "password": "...", "code": "123456", "two_fa_data": {...}}
    """
    data = request.json
    if not data or 'code' not in data:
        return jsonify({"status": "error", "message": "OTP Code required"}), 400
        
    result = fb_api.submit_2fa(
        data.get('email'),
        data.get('password'),
        data.get('code'),
        data.get('two_fa_data')
    )
    return jsonify(result)

if __name__ == '__main__':
    # Running on 0.0.0.0 to make it accessible from other devices if needed
    print("API Running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
        
