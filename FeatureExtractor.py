import requests
import re
import ast
from dotenv import load_dotenv
import os

# load_dotenv()

def extract_info_from_text(extracted_text, API_key):
    GROQ_API_KEY = API_key

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        # "model": "llama-3.3-70b-versatile",
        "model" : "deepseek-r1-distill-llama-70b",
        "messages": [
            {"role": "system", "content": "You are an expert at extracting structured information from medical invoices."},
            {"role": "user", "content": f'''
Extract the following fields from this medical invoice. 
If a value is not present, return:
- "Not Found" for strings
- 0 for integers
- 0.0 for floats
Also, predict gender from name if not mentioned.
Also, make sure that diagnosis should fall in this list ['Diabetes', 'Allergy', 'Hypertension', 'Mismatch Diagnosis','Migraine', 'Fracture Arm', 'Viral Fever', 'Acute Bronchitis','Food Poisoning']
if diagnosis does not present in this list then set it to "Not Found"

        
return python dictionary like this
             {{
            'patient_name': patient_name,
            'patient_age': patient_age,
            'patient_gender': patient_gender,
            'doctor_name': doctor_name,
            'diagnosis': diagnosis,
            'payment_mode': payment_mode,
            'insurance_provider': insurance_provider,
            'policy_number': policy_number,
            'services_count': services_count,
            'services_cost_prediscount': services_cost_prediscount,
            'discount_applied': discount_applied,
            'discount_amount': discount_amount,
            'final_claim_amount': final_claim_amount
        }}
Invoice Text:
"""{extracted_text}"""
            '''}
        ],
        "temperature": 0.2
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']


def fill_missing(dict):
    patient_age = dict['patient_age']
    payment_mode = dict['payment_mode']
    discount_applied = dict['discount_applied']

    patient_age = patient_age if patient_age != 0 else 56
    payment_mode = payment_mode if payment_mode in ['Credit Card', 'Online Payment', 'Cash', 'Insurance'] else 'Cash'
    discount_applied = 1 if discount_applied == True else 0

    dict['patient_age'] = patient_age
    dict['payment_mode'] = payment_mode
    dict['discount_applied'] = discount_applied

    return dict

def check_insufficient_info(dict):
    return (dict.get('patient_name') == 'Not Found' or
            dict.get('final_claim_amount') == 0.0 or
            dict.get('services_count') == 0)


def extractFeatures(txt, api_key):
    extracted_text = extract_info_from_text(txt, os.getenv("API_KEY"))

    x = re.search(r"```python(.*?)```", extracted_text, re.DOTALL)
    if x:
        code_block = x.group(1)
        with open("temp.txt",'w') as file:
            file.write(code_block)
        
        try:
            dict_match = re.search(r"\{.*?\}", code_block, re.DOTALL)
            if dict_match:
                result_dict = ast.literal_eval(dict_match.group(0))
                result_dict = fill_missing(result_dict)
                print(result_dict)
                msg = "information insufficient | Check your pdf again" if check_insufficient_info(result_dict) else ""
                return result_dict,msg
            else:
                x = {
                        'patient_name': 'JANE DOE',
                        'patient_age': 0,
                        'patient_gender': 'Female',
                        'doctor_name': 'Not Found',
                        'diagnosis': 'Not Found',
                        'payment_mode': 'Cash',
                        'insurance_provider': 'Not Found',
                        'policy_number': 'Not Found',
                        'services_count': 0,
                        'services_cost_prediscount': 0,
                        'discount_applied': 0,
                        'discount_amount': 0,
                        'final_claim_amount': 0
                    }
                print("⚠ Dictionary not found in code block.")
                return x,"⚠ Something goes wrong"
        except Exception as e:
            print("❌ Error while parsing dict:", e)

        
