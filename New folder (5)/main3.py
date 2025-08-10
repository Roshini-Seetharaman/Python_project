from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from paddleocr import PaddleOCR
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import os
import re
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure UPLOAD_FOLDER exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ocr = PaddleOCR(use_angle_cls=True, lang='en')

def extract_with_first_method(img_path):
    result = ocr.ocr(img_path)
    registration_number = ''
    legal_name = ''
    constitution_of_business = ''
    type_of_registration = ''
    period_of_validity_from = ''

    found_legal_name = False
    found_constitution = False
    found_type_registration = False
    found_period_validity = False
    found_from = False

    for line in result[0]:
        text = line[1][0]

        if "RegistrationNumber" in text or "Registration Number" in text:
            registration_number = text.split(':')[-1].strip()
        elif "Legal Name" in text:
            found_legal_name = True
            legal_name = text.split(':')[-1].strip() if ':' in text else ''
        elif found_legal_name:
            legal_name = text.strip()
            found_legal_name = False
        elif "Constitution of Business" in text:
            found_constitution = True
            constitution_of_business = text.split(':')[-1].strip() if ':' in text else ''
        elif found_constitution:
            constitution_of_business = text.strip()
            found_constitution = False
        elif "Type of Registration" in text:
            found_type_registration = True
            type_of_registration = text.split(':')[-1].strip() if ':' in text else ''
        elif found_type_registration:
            type_of_registration = text.strip()
            found_type_registration = False
        elif "Period of Validity" in text:
            found_period_validity = True
        elif found_period_validity and "From" in text:
            found_from = True
        elif found_from:
            date_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
            if date_match:
                period_of_validity_from = date_match.group(0)
            found_from = False
            found_period_validity = False

    if period_of_validity_from:
        return {
            'Registration Number': registration_number,
            'Legal Name': legal_name,
            'Constitution of Business': constitution_of_business,
            'Type of Registration': type_of_registration,
            'Registration Date': period_of_validity_from
        }
    else:
        return None

def extract_with_second_method(img_path):
    result = ocr.ocr(img_path)
    registration_number = ''
    legal_name = ''
    constitution_of_business = ''
    type_of_registration = ''
    registration_date = ''

    found_legal_name = False
    found_constitution = False
    found_type_registration = False
    found_date_of_validity = False
    found_from = False

    for line in result[0]:
        text = line[1][0]

        if "RegistrationNumber" in text or "Registration Number" in text:
            registration_number = text.split(':')[-1].strip()
        elif "Legal Name" in text:
            found_legal_name = True
            legal_name = text.split(':')[-1].strip() if ':' in text else ''
        elif found_legal_name:
            legal_name = text.strip()
            found_legal_name = False
        elif "Constitution of Business" in text:
            found_constitution = True
            constitution_of_business = text.split(':')[-1].strip() if ':' in text else ''
        elif found_constitution:
            constitution_of_business = text.strip()
            found_constitution = False
        elif "Type of Registration" in text:
            found_type_registration = True
            type_of_registration = text.split(':')[-1].strip() if ':' in text else ''
        elif found_type_registration:
            type_of_registration = text.strip()
            found_type_registration = False
        elif "Date of Validity" in text:
            found_date_of_validity = True
        elif found_date_of_validity and "From" in text:
            found_from = True
        elif found_from:
            date_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
            if date_match:
                registration_date = date_match.group(0)
            found_from = False
            found_date_of_validity = False

    return {
        'Registration Number': registration_number,
        'Legal Name': legal_name,
        'Constitution of Business': constitution_of_business,
        'Type of Registration': type_of_registration,
        'Registration Date': registration_date
    }

def get_gst_details(gstin):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
    chrome_options.add_argument("--window-size=1920x1080")  # Set window size for consistency
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-popup-blocking")  # Ensure no pop-ups are displayed
    chrome_options.add_argument("--disable-infobars")  # Disable infobars

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    url = "https://cleartax.in/gst-number-search/#How%20to%20use%20the%20Clear%20GST%20Search%20Tool%20and%20GSTIN%20Validator?"
    driver.get(url)

    input_field = driver.find_element(By.ID, 'input')
    input_field.send_keys(gstin)
    input_field.send_keys(Keys.RETURN)
    
    time.sleep(5)

    try:
        details = {
            'Legal Name': driver.find_element(By.XPATH, "//span[@id='Business Name']/following-sibling::h4/following-sibling::small").text,
            'Constitution of the Business': driver.find_element(By.XPATH, "//span[@id='Entity Type']/following-sibling::h4/following-sibling::small").text,
            'Registration Date': driver.find_element(By.XPATH, "//span[@id='Registration Date']/following-sibling::h4/following-sibling::small").text,
            'PAN': driver.find_element(By.XPATH, "//span[@id='PAN']/following-sibling::h4/following-sibling::small").text,
            'Type of Registration': driver.find_element(By.XPATH, "//span[@id='Registration Type']/following-sibling::h4/following-sibling::small").text
        }
    except Exception as e:
        print(f"Error extracting details: {e}")
        return None
    finally:
        driver.quit()
    
    return details

@app.get("/next_step", response_class=HTMLResponse)
async def next_step(request: Request):
    return templates.TemplateResponse("upload2.html", {"request": request})

@app.post("/upload/")
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    try:
        ocr_results = extract_with_first_method(file_path)
        if not ocr_results:
            ocr_results = extract_with_second_method(file_path)

        if ocr_results:
            gstin = ocr_results.get('Registration Number')
            web_results = get_gst_details(gstin)

            validation_message = ""
            if web_results:
                if (ocr_results.get('Legal Name') == web_results.get('Legal Name') and
                    ocr_results.get('Registration Date') == web_results.get('Registration Date') and
                    ocr_results.get('Constitution of Business') == web_results.get('Constitution of the Business')):
                    validation_message = "The details are valid."
                else:
                    validation_message = "The details are not valid."
            else:
                validation_message = "No details found from web scraping."

            return templates.TemplateResponse("result.html", {
                "request": request,
                "ocr_results": ocr_results,
                "web_results": web_results,
                "validation_message": validation_message
            })
        else:
            return templates.TemplateResponse("result.html", {
                "request": request,
                "validation_message": "No information extracted from image."
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

@app.get("/result", response_class=HTMLResponse)
async def show_results(request: Request):
    return templates.TemplateResponse("result.html", {"request": request})
