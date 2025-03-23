from flask import Flask, render_template, request, url_for, redirect, session, flash, get_flashed_messages
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
from dotenv import load_dotenv
from FeatureExtractor import extractFeatures


# load_dotenv()

# Set the path for Tesseract OCR executable
# pt.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
if(os.name == 'nt'):
    pt.pytesseract.tesseract_cmd = r"Tesseract-OCR\tesseract.exe"

# Initialize the Flask application
app = Flask(__name__)
# run_with_ngrok(app)

app.secret_key = 'your_secret_key'  # Secret key for session management
app.config["MONGO_URI"] = os.getenv("MONGO_URI")   # MongoDB connection URI
mongo = PyMongo(app)  # Initialize PyMongo with the Flask app

message_for_login_registration = False

@app.route('/', methods=['GET', 'POST'])
def login_registration():
    messages = get_flashed_messages()
    if messages:
        return render_template('index.html', response=messages[0])  # Render with the flash message
    
    
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
            return render_template('index.html',response="Account doesn't exist") # Return error if user not found

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
    
    poppler_path = "/usr/bin"
    if(os.name == 'nt'):
        poppler_path = r'bin'
    print(f"Operating System = {os.name}")
    images = convert_from_path(file_path)  # Convert PDF to images
    text = ""
    for img in images:
        text += pt.image_to_string(img)  # Extract text from each image
    return text  # Return the extracted text

def extract_info_from_pdf(file_path):
    # Extract relevant information from the PDF
    s = extract_text_from_scanned_pdf(file_path)  # Extract text from the PDF
    return extractFeatures(s)

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
        s = None
        msg = None
        if(os.path.isfile("invoice.pdf")):
            print("invoice.pdf does exist")
            s,msg = extract_info_from_pdf('invoice.pdf')  # Extract information from the PDF
        else:
            print("invoice.pdf does not exists")
        

        result = ""
        fraud = None

        print("Printing Extracted info ")
        print(s)

        if s is None or None in s:
            result = "Info for prediction can't be extracted"  # Handle case where info extraction fails
            return render_template('home.html', full_name=full_name, user_id=username, predict=result, previous_submissions=previous_submissions)

        if msg != "":
            result = msg  # Handle case where info extraction fails
            return render_template('home.html', full_name=full_name, user_id=username, predict=result, previous_submissions=previous_submissions)

        elif s['diagnosis'] == 'Not Found':
            result = "Critical information Missing : Diagnosis not found"  # Handle case where info extraction fails
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
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()

        # Validate input
        if not username or not password or not full_name:
            flash("All fields must contain non-empty values")
            return redirect(url_for('login_registration'))

        # Validate minimum lengths
        if len(full_name) < 2:
            flash("Full name must be at least 2 characters long")
            return redirect(url_for('login_registration'))

        if len(username) < 3:
            flash("Username must be at least 3 characters long")
            return redirect(url_for('login_registration'))

        if len(password) < 6:
            flash("Password must be at least 6 characters long")
            return redirect(url_for('login_registration'))

        if mongo.db.User.find_one({'username': username}):
            flash("Username not available")
            return redirect(url_for('login_registration'))

        mongo.db.User.insert_one({
            'username': username,
            'password': password,
            'full_name': full_name
        })

        session['username'] = username
        session['full_name'] = full_name

        return render_template('registration_successful.html')
    
    return 'No path exists'

@app.route('/redirect_home')
def redirect_home():
    time.sleep(5)  # Simulate delay
    return redirect(url_for('home'))  # Redirect to home page

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('login_registration'))  # Redirect to login/registration page

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Run the Flask application on Render platform
    # app.run(debug=True)
