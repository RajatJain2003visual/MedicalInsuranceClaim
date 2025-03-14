from flask import Flask, render_template, request, url_for, redirect, session
import time
import jinja2
from flask_pymongo import PyMongo
import pickle
import joblib
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import pytesseract as pt
import re
from types import NotImplementedType
import pandas as pd
import os

# Set the path for Tesseract OCR executable
pt.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management
app.config["MONGO_URI"] = os.getenv("MONGO_URI")   # MongoDB connection URI
mongo = PyMongo(app)  # Initialize PyMongo with the Flask app

@app.route('/', methods=['GET', 'POST'])
def login_registration():
    # Handle user login and registration
    if request.method == 'POST':
        username = request.form.get('username')  # Get username from form
        password = request.form.get('password')  # Get password from form
        print(f"Username: {username}, Password: {password}")  # Debug print
        user = mongo.db.User.find_one({'username': username, 'password': password})  # Check user credentials
        if user:
            full_name = user['full_name']  # Get full name from user document
            session['username'] = username  # Store username in session
            session['full_name'] = full_name  # Store full name in session
            return redirect(url_for('home'))  # Redirect to home page
        else:
            return "Account doesn't exist"  # Return error if user not found

    return render_template('index.html')  # Render the login/registration page

def predict(s):
    # Prepare data for prediction
    X = pd.DataFrame(
        [
            {
                'Age': s['patient_age'],
                'Gender': s['patient_gender'],
                'Diagnosis': s['diagnosis'],
                'Payment Mode': s['payment_mode'],
                'Services Count': s['services_count'],
                'Service Cost (Pre-Discount)': s['services_cost_prediscount'],
                'Discount Applied': s['discount_applied'],
                'Discount Amount': s['discount_amount'],
                'Final Claim Amount': s['final_claim_amount'],
            }
        ]
    )

    # Encode categorical variables
    categorial_columns = ['Gender', 'Diagnosis', 'Payment Mode']
    encoder = joblib.load('encoder.joblib')  # Load the encoder
    encoded_data = encoder.transform(X[categorial_columns])  # Transform categorical data
    encoded_df = pd.DataFrame(encoded_data, columns=encoder.get_feature_names_out(categorial_columns))  # Create DataFrame for encoded data
    X = pd.concat([X.drop(columns=categorial_columns), encoded_df], axis=1)  # Combine encoded data with original DataFrame

    # Standardize numerical features
    scaler = joblib.load('scaler.joblib')  # Load the scaler
    standardized_data = scaler.transform(X[['Age', 'Services Count', 'Service Cost (Pre-Discount)', 'Discount Amount', 'Final Claim Amount']])  # Standardize data
    standardized_df = pd.DataFrame(standardized_data, columns=['Age', 'Services Count', 'Service Cost (Pre-Discount)', 'Discount Amount', 'Final Claim Amount'])  # Create DataFrame for standardized data

    X = pd.concat([X.drop(columns=['Age', 'Services Count', 'Service Cost (Pre-Discount)', 'Discount Amount', 'Final Claim Amount']), standardized_df], axis=1)  # Combine standardized data with original DataFrame

    # Load the trained model and make a prediction
    with open('model.pkl', 'rb') as file:
        model = pickle.load(file)  # Load the model
        fraud = model.predict(X)  # Predict fraud

    print(f'Fraud : {fraud[0]}')  # Debug print of the prediction result

    return fraud  # Return the prediction result

def extract_text_from_scanned_pdf(file_path):
    # Convert PDF to images and extract text using OCR
    images = convert_from_path(file_path, poppler_path="/usr/bin")  # Convert PDF to images
    text = ""
    for img in images:
        text += pt.image_to_string(img)  # Extract text from each image
    return text  # Return the extracted text

def extract_info_from_pdf(file_path):
    # Extract relevant information from the PDF
    s = extract_text_from_scanned_pdf(file_path)  # Extract text from the PDF

    # Initialize variables for extracted information
    patient_name, patient_age, patient_gender, policy_number, doctor_name, diagnosis, discount_applied, discount_amount, final_claim_amount, payment_mode, insurance_provider, services_count, services_cost_prediscount = [None] * 13

    # Extract patient name and age
    match = re.search(r"Patient Name:\s*(.+?)\s+Age:\s*(\d+)", s)
    if match:
        patient_name = match.group(1)
        patient_age = match.group(2)
        print(f"Patient Name: {patient_name}")
        print(f"Patient Age: {patient_age}")
    else:
        print("Patient name and age can't be found")

    # Extract gender and policy number
    match = re.search(r"Gender:\s*(.+?)\s+Policy Number:\s*(.+?)\s*[\n]", s)
    if match:
        patient_gender = match.group(1)
        policy_number = match.group(2)
        print(f"Patient Gender: {patient_gender}")
        print(f"Policy Number: {policy_number}")
    else:
        print("Patient gender can't be found")

    # Extract doctor's name and diagnosis
    match = re.search(r'Doctor\s*:\s*(.*?)\s+Diagnosis\s*:\s*(.*)', s)
    if match:
        doctor_name = match.group(1)
        diagnosis = match.group(2)
        print("Doctor:", doctor_name)
        print("Diagnosis:", diagnosis)

    # Extract payment details
    match = re.search(
        r'Discount Applied:\s*(Yes|No)\s*'
        r'Discount Amount:\s*INR\s*(\d+)\s*'
        r'Final Claim Amount:\s*INR\s*(\d+)\s*'
        r'Payment Mode:\s*(\w+)\s*'
        r'Insurance Provider:\s*([^\n\r]*)',
        s
    )

    if match:
        discount_applied = 1 if match.group(1) == 'Yes' else 0
        discount_amount = match.group(2)
        final_claim_amount = match.group(3)
        payment_mode = match.group(4)
        insurance_provider = match.group(5)

        print("Discount Applied:", discount_applied)
        print("Discount Amount:", discount_amount)
        print("Final Claim Amount:", final_claim_amount)
        print("Payment Mode:", payment_mode)
        print("Insurance Provider:", insurance_provider)
    else:
        print("Payment details not found")

    # Extract service lines
    service_lines = re.findall(r'Service Cost \(INR\)\s*(.*?)Service Cost \(Pre-Discount\)', s, re.DOTALL)
    if service_lines:
        services = re.findall(r'(.*?)\s+\d+', service_lines[0])  # Extract service names
        services_count = len(services)  # Count the number of services

        total_pre_discount = re.search(r'Service Cost \(Pre-Discount\)\s*(\d+)', s)
        services_cost_prediscount = int(total_pre_discount.group(1)) if total_pre_discount else 0  # Get pre-discount service cost

        print("Services Count:", services_count)
        print("Service Cost (Pre-Discount):", services_cost_prediscount)

        return {
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
        }

@app.route('/home', methods=['GET', 'POST'])
def home():
    # Get user information from session
    full_name = session.get('full_name')
    username = session.get('username')
    
    # Fetch the last two submissions for the user
    previous_submissions = list(mongo.db.Invoices_info.find({'username': username}).sort('_id', -1).limit(2))

    if request.method == 'GET':
        return render_template('home.html', full_name=full_name, user_id=username, info={}, previous_submissions=previous_submissions)
    
    if request.method == 'POST':
        request.files.get('invoice').save('invoice.pdf')  # Save the uploaded PDF
        s = extract_info_from_pdf('invoice.pdf')  # Extract information from the PDF
        result = ""
        fraud = None

        print("Printing Extracted info ")
        print(s)

        if s is None or None in s:
            result = "Info for prediction can't be extracted"  # Handle case where info extraction fails
            return render_template('home.html', full_name=full_name, user_id=username, predict=result, previous_submissions=previous_submissions)

        else:
            fraud = predict(s)  # Make a prediction based on extracted info
            result = "Claim is valid" if fraud == 0 else "Claim is invalid"  # Determine claim validity
            mongo.db.Invoices_info.insert_one(
                {
                    'info': s,  # Store extracted info in the database
                    'date': time.strftime("%Y-%m-%d %H:%M:%S"),  # Store current date and time
                    'username': username,  # Store username
                    'valid': 0 if fraud == 1 else 1  # Store validity of the claim
                }
            )
        
        return render_template('home.html', full_name=full_name, user_id=username, info=s, predict=result, previous_submissions=previous_submissions)

@app.route('/register', methods=['POST'])
def add_data():
    # Handle user registration
    if request.method == 'POST':
        username = request.form.get('username')  # Get username from form
        password = request.form.get('password')  # Get password from form
        full_name = request.form.get('full_name')  # Get full name from form
        mongo.db.User.insert_one(
            {
                'username': username,  # Store username
                'password': password,  # Store password
                'full_name': full_name  # Store full name
            }
        )

        session['username'] = username  # Store username in session
        session['full_name'] = full_name  # Store full name in session

        return render_template('registration_successful.html')  # Render success page
    
    return 'No path exist'  # Return error if no path exists

@app.route('/redirect_home')
def redirect_home():
    time.sleep(5)  # Simulate delay
    return redirect(url_for('home'))  # Redirect to home page

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('login_registration'))  # Redirect to login/registration page

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Run the Flask application on Render platform
