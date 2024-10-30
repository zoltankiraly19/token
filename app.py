from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import json

app = Flask(__name__)
CORS(app)

# IBM Cloud Object Storage konfigurálása az új adatokkal
cos = ibm_boto3.client(
    's3',
    ibm_api_key_id='a2g6_5isBRzu-zm2vGL4ITcXhyL__rUe_RNWjGYVrkWr',
    ibm_service_instance_id='e669d0c8-4f96-478e-86bf-fd49039ff1f8',
    config=Config(signature_version='oauth'),
    endpoint_url='https://s3.us-south.cloud-object-storage.appdomain.cloud'
)

bucket_name = 'servicenow'  # Új bucket név

# Bejelentkezési és user-specifikus adatok (token, caller_id) mentési szakasz
@app.route('/login', methods=['POST'])
def login_and_store_data():
    request_data = request.json
    username = request_data.get('username')
    password = request_data.get('password')

    # Token megszerzése a ServiceNow-tól
    auth_data = {
        'grant_type': 'password',
        'client_id': '45f3f2fb2ead4928ab994c64c664dfdc',
        'client_secret': 'fyHL1.@d&7',
        'username': username,
        'password': password
    }

    response = requests.post('https://dev227667.service-now.com/oauth_token.do', data=auth_data)
    if response.status_code == 200:
        access_token = response.json().get('access_token')
        # Az IBM COS-ba mentjük a tokent user_token néven
        cos.put_object(Bucket=bucket_name, Key=f'{username}_user_token', Body=access_token)

        # Felhasználói sys_id lekérése és mentése COS-ba user_sys_id néven
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        response_user = requests.get(
            f"https://dev227667.service-now.com/api/now/table/sys_user?sysparm_query=user_name={username}",
            headers=headers
        )
        if response_user.status_code == 200:
            caller_id = response_user.json().get('result', [])[0].get("sys_id")
            cos.put_object(Bucket=bucket_name, Key=f'{username}_user_sys_id', Body=caller_id)

            return jsonify({"message": "Bejelentkezés sikeres, adatok tárolva.", "user_token": access_token, "user_sys_id": caller_id}), 200
        else:
            return jsonify({"error": "Felhasználói azonosító lekérése sikertelen."}), 400
    else:
        return jsonify({"error": "Authentication failed", "details": response.text}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)