import re
import os
import time
from flask import Flask, render_template, request, redirect
from paddleocr import PaddleOCR
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png'}

# ---------- Utility Functions ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_details_from_image(img_path):
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr(img_path)
    extracted_text = " ".join([line[1][0] for line in result[0]])

    company_name_match = re.search(r"hereby certify that (.+?) is incorporated on", extracted_text, re.IGNORECASE)
    company_name = company_name_match.group(1).upper() if company_name_match else "COMPANY NAME NOT FOUND"

    date_in_words_match = re.search(r"incorporated on (.+?) under the Companies Act", extracted_text, re.IGNORECASE)
    if date_in_words_match:
        date_in_words = date_in_words_match.group(1)
        month_mapping = {
            "January": "January", "February": "February", "March": "March", "April": "April", "May": "May", "June": "June",
            "July": "July", "August": "August", "September": "September", "October": "October", "November": "November", "December": "December"
        }
        day_mapping = {
            "First": "01", "Second": "02", "Third": "03", "Fourth": "04", "Fifth": "05", "Sixth": "06",
            "Seventh": "07", "Eighth": "08", "Ninth": "09", "Tenth": "10", "Eleventh": "11", "Twelfth": "12",
            "Thirteenth": "13", "Fourteenth": "14", "Fifteenth": "15", "Sixteenth": "16", "Seventeenth": "17",
            "Eighteenth": "18", "Nineteenth": "19", "Twentieth": "20", "Twenty-first": "21", "Twenty-second": "22",
            "Twenty-third": "23", "Twenty-fourth": "24", "Twenty-fifth": "25", "Twenty-sixth": "26",
            "Twenty-seventh": "27", "Twenty-eighth": "28", "Twenty-ninth": "29", "Thirtieth": "30", "Thirty-first": "31"
        }
        day_match = re.search(r"(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|Twentieth|Twenty-first|Twenty-second|Twenty-third|Twenty-fourth|Twenty-fifth|Twenty-sixth|Twenty-seventh|Twenty-eighth|Twenty-ninth|Thirtieth|Thirty-first)", date_in_words)
        month_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)", date_in_words)
        year_match = re.search(r"(Two thousand (\w+))", date_in_words)
        if day_match and month_match and year_match:
            day = day_mapping.get(day_match.group(1), "01")
            month = month_mapping.get(month_match.group(1), "January")
            year_text = year_match.group(2).strip().lower()
            if year_text == "nineteen":
                year = "2019"
            elif year_text == "eighteen":
                year = "2018"
            elif year_text == "twenty":
                year = "2020"
            else:
                year = "20" + year_text
            date_of_incorporation = f"{day} {month} {year}"
        else:
            date_of_incorporation = "Date not found"
    else:
        date_of_incorporation = "Date not found"

    llpin_match = re.search(r"Identity Number of the company is\s*([^\s]+)", extracted_text, re.IGNORECASE)
    llpin = llpin_match.group(1).strip() if llpin_match else "LLPIN / CIN not found"

    pan_match = re.search(r"Permanent Account Number\(PAN\) of the company is\s*([^\s]+)", extracted_text, re.IGNORECASE)
    pan_match_2 = re.search(r"\(PAN\) of the company is\s*([^\s]+)", extracted_text, re.IGNORECASE)
    pan_match_3 = re.search(r"Permanent Account Number\(PAN\)of the company is\s*([^\s]+)", extracted_text, re.IGNORECASE)
    if pan_match:
        pan = pan_match.group(1).strip()
    elif pan_match_2:
        pan = pan_match_2.group(1).strip()
    elif pan_match_3:
        pan = pan_match_3.group(1).strip()
    else:
        pan = "PAN not found"

    digital_signature_match = re.search(r"Digital Signature Certificate\s*(.+?)\s*For and on behalf of", extracted_text, re.IGNORECASE)
    digital_signature_name = digital_signature_match.group(1).strip() if digital_signature_match else "Digital Signature Name not found"

    return company_name, date_of_incorporation, llpin, pan, digital_signature_name

def get_gst_details(CIN):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    url = "https://www.zaubacorp.com/company/ALEP-MANAGEMENT-LLP/AAS-9086"
    driver.get(url)

    input_field = driver.find_element(By.ID, 'searchid')
    input_field.send_keys(CIN)
    input_field.send_keys(Keys.RETURN)

    time.sleep(5)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//td[p[text()='Company Name']]/following-sibling::td/p"))
        )
        company_name_2 = driver.find_element(By.XPATH, "//td[p[text()='Company Name']]/following-sibling::td/p").text
        date_of_incorporation_2 = driver.find_element(By.XPATH, "//td[p[text()='Date of Incorporation']]/following-sibling::td/p").text
    except Exception as e:
        print(f"Error extracting details: {e}")
        driver.quit()
        return None

    driver.quit()
    return {
        'Company Name': company_name_2,
        'Date of Incorporation': date_of_incorporation_2
    }

# ---------- Routes ----------
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            company_name, date_of_incorporation, llpin, pan, digital_signature_name = extract_details_from_image(filename)
            gst_details = None
            if llpin != "LLPIN / CIN not found":
                gst_details = get_gst_details(llpin)
                if gst_details:
                    scraped_company_name = gst_details['Company Name']
                    scraped_date_of_incorporation = gst_details['Date of Incorporation']
                    validation_status = "Valid" if company_name == scraped_company_name and date_of_incorporation == scraped_date_of_incorporation else "Not Valid"
                else:
                    validation_status = "Failed to fetch GST details."
            else:
                validation_status = "CIN not found in the OCR process."

            return render_template(
                'result2.html', 
                company_name=company_name,
                date_of_incorporation=date_of_incorporation,
                llpin=llpin,
                pan=pan,
                digital_signature_name=digital_signature_name,
                validation_status=validation_status,
                gst_details=gst_details if gst_details else None
            )
    return render_template('upload2.html')

@app.route('/next_step')
def next_step():
    return "Next step functionality not implemented yet."

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(port=5001, debug=True)
