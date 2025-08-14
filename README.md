# SME Compliance Document Verification

This project helps small and medium businesses quickly verify their compliance documents like Business Registration Certificates, GST certificates, and Bank Statements.  
It scans the uploaded file, reads the details using OCR, and checks them with public datasets (like MCA or GSTN) to confirm if they are valid and up to date.

## What it does
- Lets you upload documents in PDF or image format.
- Reads the text from the document using OCR.
- Compares the details with official data sources to verify authenticity.
- Shows whether the verification is successful or failed.
- Has a simple web interface built with Flask.

## How to install
1. Clone this repository:
   ```bash
   git clone https://github.com/Roshini-Seetharaman/Python_project.git
   cd Python_project

Install all required packages:

pip install -r requirements.txt

How to run

Run the Flask app:

python main.py


Then open this link in your browser:

http://127.0.0.1:5000/
