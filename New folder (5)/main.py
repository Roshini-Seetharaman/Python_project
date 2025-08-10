import os
import re
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


# -------------------- File Validation --------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# -------------------- OCR Extraction --------------------
def extract_details_from_image(img_path):
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr(img_path)
    extracted_text = " ".join([line[1][0] for line in result[0]])

    # Extract company name
    company_name_match = re.search(r"hereby certify that (.+?) is incorporated on", extracted_text, re.IGNORECASE)
    company_name = company_name_match.group(1).upper() if company_name_match else "COMPANY NAME NOT FOUND"

    # Extract incorporation date
    date_in_words_match = re.search(r"incorporated on (.+?) under the Companies Act", extracted_text, re.IGNORECASE)
    if date_in_words_match:
        date_in_words = date_in_words_match.group(1)
        day_map = {
            "First": "01", "Second": "02", "Third": "03", "Fourth": "04", "Fifth": "05", "Sixth": "06",
            "Seventh": "07", "Eighth": "08", "Ninth": "09", "Tenth": "10", "Eleventh": "11", "Twelfth": "12",
            "Thirteenth": "13", "Fourteenth": "14", "Fifteenth": "15", "Sixteenth": "16", "Seventeenth": "17",
            "Eighteenth": "18", "Nineteenth": "19", "Twentieth": "20", "Twenty-first": "21", "Twenty-second": "22",
            "Twenty-third": "23", "Twenty-fourth": "24", "Twenty-fifth": "25", "Twenty-sixth": "26",
            "Twenty-seventh": "27", "Twenty-eighth": "28", "Twenty-ninth": "29", "Thirtieth": "30", "Thirty-first": "31"
        }
        month_map = {
            "January": "January", "February": "February", "March": "March", "April": "April", "May": "May", "June": "June",
            "July": "July", "August": "August", "September": "September", "October": "October", "November": "November", "December": "December"
        }
        day_match = re.search(r"(" + "|".join(day_map.keys()) + ")", date_in_words)
        month_match = re.search(r"(" + "|".join(month_map.keys()) + ")", date_in_words)
        year_match = re.search(r"Two thousand (\w+)", date_in_words, re.IGNORECASE)
        if day_match and month_match and year_match:
            day = day_map[day_match.group(1)]
            month = month_map[month_match.group(1)]
            year_word = year_match.group(1).lower()
            year_lookup = {"nineteen": "2019", "eighteen": "2018", "twenty": "2020"}
            year = year_lookup.get(year_word, "20" + year_word)
            date_of_incorporation = f"{day} {month} {year}"
        else:
            date_of_incorporation = "Date not found"
    else:
        date_of_incorporation = "Date not found"

    # LLPIN / CIN
    llpin_match = re.search(r"Identity Number of the company is\s*([^\s]+)", extracted_text, re.IGNORECASE)
    llpin = llpin_match.group(1) if llpin_match else "LLPIN / CIN not found"

    # PAN
    pan_match = re.search(r"PAN\) of the company is\s*([^\s]+)", extracted_text, re.IGNORECASE)
    pan = pan_match.group(1) if pan_match else "PAN not found"

    # Digital Signature Name
    ds_match = re.search(r"Digital Signature Certificate\s*(.+?)\s*For and on behalf of", extracted_text, re.IGNORECASE)
    digital_signature_name = ds_match.group(1).strip() if ds_match else "Digital Signature Name not found"

    return company_name, date_of_incorporation, llpin, pan, digital_signature_name


# -------------------- Selenium Scraper --------------------
def get_gst_details(CIN):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.zaubacorp.com")

    try:
        input_field = driver.find_element(By.ID, 'searchid')
        input_field.send_keys(CIN)
        input_field.send_keys(Keys.RETURN)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//td[p[text()='Company Name']]/following-sibling::td/p"))
        )

        company_name = driver.find_element(By.XPATH, "//td[p[text()='Company Name']]/following-sibling::td/p").text
        date_of_incorp = driver.find_element(By.XPATH, "//td[p[text()='Date of Incorporation']]/following-sibling::td/p").text

    except Exception as e:
        print("Error fetching GST details:", e)
        driver.quit()
        return None

    driver.quit()
    return {"Company Name": company_name, "Date of Incorporation": date_of_incorp}


# -------------------- Flask Routes --------------------
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            company_name, date_of_incorp, llpin, pan, ds_name = extract_details_from_image(filepath)

            validation_status = "CIN not found in OCR"
            gst_details = None

            if llpin != "LLPIN / CIN not found":
                gst_details = get_gst_details(llpin)
                if gst_details:
                    if company_name == gst_details["Company Name"] and date_of_incorp == gst_details["Date of Incorporation"]:
                        validation_status = "Valid"
                    else:
                        validation_status = "Not Valid"
                else:
                    validation_status = "Failed to fetch GST details."

            return render_template("result2.html",
                                   company_name=company_name,
                                   date_of_incorporation=date_of_incorp,
                                   llpin=llpin,
                                   pan=pan,
                                   digital_signature_name=ds_name,
                                   validation_status=validation_status,
                                   gst_details=gst_details)
    return render_template("upload2.html")


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(port=5001, debug=True)

