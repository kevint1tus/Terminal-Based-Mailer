import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Fetch the API key from the environment variables
API_KEY = os.getenv('API_KEY')

# Check if the API key is loaded
if not API_KEY:
    raise ValueError("API Key is not set in .env file.")

CREATE_TASK_URL = 'https://api.2captcha.com/createTask'
GET_RESULT_URL = 'https://api.2captcha.com/getTaskResult'

def solve_captcha(website_key, website_url, retries=3):
    for attempt in range(retries):
        print(f"Attempting to solve CAPTCHA (Attempt {attempt + 1}/{retries})...")
        
        task_data = {
            'clientKey': API_KEY,
            'task': {
                'type': 'HCaptchaTaskProxyless',
                'websiteURL': website_url,
                'websiteKey': website_key
            }
        }
        response = requests.post(CREATE_TASK_URL, json=task_data)
        response_json = response.json()

        if response_json.get('errorId') != 0:
            print(f"Error creating captcha task: {response_json.get('errorCode')}")
            time.sleep(10)  
            continue
        
        task_id = response_json.get('taskId')

        while True:
            time.sleep(5)  
            result_response = requests.post(GET_RESULT_URL, json={
                'clientKey': API_KEY,
                'taskId': task_id
            })
            result_json = result_response.json()

            if result_json.get('errorId') != 0:
                print(f"Error getting captcha result: {result_json.get('errorCode')}")
                break

            if result_json.get('status') == 'ready':
                print("CAPTCHA solved successfully.")
                return result_json.get('solution', {}).get('token')
            elif result_json.get('status') == 'processing':
                print("CAPTCHA not yet solved, waiting...")
                continue
            else:
                print(f"Unexpected result status: {result_json}")
                break

        print(f"Retrying CAPTCHA solving ({attempt + 1}/{retries})...")
    
    raise Exception("Failed to solve CAPTCHA after multiple attempts.")

# Use Firefox Developer Edition
firefox_options = Options()
firefox_options.binary_location = "/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox"  # Ensure this is the correct path
firefox_options.add_argument("--disable-extensions")
firefox_options.add_argument("--disable-popup-blocking")
firefox_options.add_argument("--headless")  
firefox_options.add_argument("--no-sandbox")  
firefox_options.add_argument("--disable-dev-shm-usage")  

service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=firefox_options)
driver.get('https://emkei.cz/')

# Get site key
try:
    site_key_element = driver.find_element(By.CSS_SELECTOR, 'div.h-captcha')
    site_key = site_key_element.get_attribute('data-sitekey')
    if not site_key:
        raise Exception("Site key not found or not set.")
except Exception as e:
    print(f"Error finding site key: {e}")
    driver.quit()
    exit(1)

current_url = driver.current_url

if not current_url.startswith('https://'):
    raise Exception(f"Invalid URL: {current_url}")

formatted_url = current_url.rstrip('/')

print("Solving captcha...")
try:
    captcha_token = solve_captcha(site_key, formatted_url)
except Exception as e:
    print(f"Failed to solve CAPTCHA: {e}")
    driver.quit()
    exit(1)

try:
    driver.execute_script(f'document.querySelector("textarea[name=\'h-captcha-response\']").value="{captcha_token}";')
    print("CAPTCHA token injected successfully.")
except Exception as e:
    print(f"Error injecting captcha solution: {e}")
    driver.quit()
    exit(1)

def collect_form_details():
    fromname = input('Enter your name: ')
    from_email = input('Enter your email: ')
    recipient = input('Enter recipient email: ')
    subject = input('Enter subject: ')
    message = input('Enter message: ')
    
    return {
        'fromname': fromname,
        'from': from_email,
        'rcpt': recipient,
        'subject': subject,
        'text': message  
    }

def fill_form(details):
    driver.execute_script(f'''
        document.querySelector("input[name='fromname']").value = "{details['fromname']}";
        document.querySelector("input[name='from']").value = "{details['from']}";
        document.querySelector("input[name='rcpt']").value = "{details['rcpt']}";
        document.querySelector("input[name='subject']").value = "{details['subject']}";
        document.querySelector("textarea[name='text']").value = `{details['text']}`;
    ''')

form_details = collect_form_details()
fill_form(form_details)

try:
    submit_button = driver.find_element(By.NAME, 'ok')
    submit_button.click()
    print("Form submitted successfully.")
except Exception as e:
    print(f"Error finding or clicking the submit button: {e}")

time.sleep(5)  
print("Script execution complete.")
driver.quit()
