import os
import time
import json
import random
import schedule
from datetime import datetime
import pytz
from dotenv import load_dotenv
from database import Database
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

def random_sleep(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def random_scroll():
    return random.uniform(0.3, 0.7)

class InstagramTracker:
    def __init__(self):
        self.db = Database()
        self.username = os.getenv('IG_USERNAME')
        self.password = os.getenv('IG_PASSWORD')
        self.target_account = os.getenv('TARGET_ACCOUNT')
        self.driver = None
        
    def setup_driver(self):
        chrome_options = Options()
        # Don't run in headless mode to look more human-like
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        # Use a realistic user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        # Set window size to look more natural
        self.driver.set_window_size(1280, 800)
    
    def login(self):
        try:
            print("Logging in to Instagram...")
            self.driver.get('https://www.instagram.com/')
            random_sleep(3, 6)
            
            # Wait for and find username input
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#loginForm > div > div:nth-child(1) > div > label > input'))
            )
            username_input.send_keys(self.username)
            random_sleep()
            
            # Find and fill password input
            password_input = self.driver.find_element(By.CSS_SELECTOR, '#loginForm > div > div:nth-child(2) > div > label > input')
            password_input.send_keys(self.password)
            random_sleep()
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()
            
            # Wait for login to complete
            random_sleep(5, 8)
            
            # Check if login was successful by waiting for the Instagram logo or profile icon
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]'))
                )
                print("Successfully logged in!")
                return True
            except TimeoutException:
                print("Failed to verify login success")
                return False
                
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
    def open_search(self):
        try:
            print("Opening search...")
            # Using a more robust selector based on the SVG aria-label and link role
            search_selector = 'a[role="link"] svg[aria-label="Search"]'
            
            # Wait for and click the search link (parent of the SVG)
            search_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, search_selector))
            )
            # Click the parent 'a' element since it's the clickable link
            search_link = search_element.find_element(By.XPATH, "./ancestor::a[@role='link']")
            random_sleep(1, 2)
            search_link.click()
            
            # Wait a moment for the search interface to load
            random_sleep(2, 4)
            print("Search opened successfully")
            return True
            
        except Exception as e:
            print(f"Failed to open search: {str(e)}")
            return False
    
    def run(self):
        try:
            self.setup_driver()
            self.login()
            self.open_search()
        except Exception as e:
            print(f"Error in run: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
            self.db.close()
            print("Script finished")

def main():
    # Schedule the job to run once every 12 hours instead of every day
    # This reduces the chance of detection
    tracker = InstagramTracker()
    
    # Run at 8 AM and 8 PM
    schedule.every().day.at("08:00").do(tracker.run)
    schedule.every().day.at("20:00").do(tracker.run)
    
    # Run immediately for the first time
    tracker.run()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
