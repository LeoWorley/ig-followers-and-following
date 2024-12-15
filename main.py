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
        self.cookies_file = 'instagram_cookies.json'
        
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
            print("Attempting to log in to Instagram...")
            
            # First try to use saved cookies
            if self.load_cookies():
                return True
                
            print("Performing fresh login...")
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
            
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]'))
                )
                print("Successfully logged in!")
                # Save cookies after successful login
                self.save_cookies()
                return True
            except TimeoutException:
                print("Failed to verify login success")
                return False
                
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
    def save_cookies(self):
        """Save the current session cookies to a file"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            print("Session cookies saved successfully")
        except Exception as e:
            print(f"Failed to save cookies: {str(e)}")

    def load_cookies(self):
        """Load and set saved cookies if they exist"""
        try:
            if os.path.exists(self.cookies_file):
                self.driver.get('https://www.instagram.com/')
                random_sleep(2, 4)
                
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                
                # Refresh page to apply cookies
                self.driver.refresh()
                random_sleep(3, 5)
                
                # Verify if we're logged in
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]'))
                    )
                    print("Successfully logged in using saved cookies!")
                    return True
                except TimeoutException:
                    print("Saved cookies are invalid or expired")
                    return False
            return False
        except Exception as e:
            print(f"Error loading cookies: {str(e)}")
            return False
    
    def navigate_to_profile(self):
        try:
            print(f"Navigating to profile: {self.target_account}")
            self.driver.get(f'https://www.instagram.com/{self.target_account}/')
            
            # Wait for profile to load by checking for profile elements
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'header section'))
                )
                print(f"Successfully loaded {self.target_account}'s profile")
                random_sleep(2, 3)
                return True
            except TimeoutException:
                print(f"Could not load profile for: {self.target_account}")
                return False
                
        except Exception as e:
            print(f"Error navigating to profile: {str(e)}")
            return False

    def run(self):
        try:
            self.setup_driver()
            if not self.login():
                print("Failed to login, aborting...")
                return
            if not self.navigate_to_profile():
                print("Failed to load target profile, aborting...")
                return
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
