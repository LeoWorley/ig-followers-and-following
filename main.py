import os
import time
import json
import random
import schedule
from datetime import datetime
import pytz
from dotenv import load_dotenv
from database import Database, FollowerFollowing, Counts
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from store_followers import store_followers
from sqlalchemy.orm.attributes import flag_modified

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

    def get_followers_info(self):
        try:
            print("Getting followers information...")
            
            # Wait for the followers link to be present
            followers_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/followers/"]'))
            )
            
            # Get the followers count from the span with title attribute
            followers_count_elem = followers_link.find_element(By.CSS_SELECTOR, 'span[class*="x5n08af"] span')
            followers_count = int(followers_count_elem.text.replace(',', ''))
            print(f"Found {followers_count} followers")

            # Get the target object
            target = self.db.get_target(self.target_account)
            if target:
                # Store the followers count in the database
                timestamp = datetime.now(pytz.UTC)
                count_entry = Counts(target_id=target.id, count_type='followers', count=followers_count, timestamp=timestamp)
                self.db.session.add(count_entry)
                self.db.session.commit()
            

            # Click on the followers link to open the list
            random_sleep(1, 2)
            followers_link.click()

            # Wait for the followers modal to appear and load content
            try:
                # First wait for modal
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
                )

                # Then wait for actual content to load (non-loading placeholder elements)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"] a[role="link"]'))
                )
                print("Followers list opened successfully")

                # Store current followers
                store_followers(self.driver, list_type='followers')

                # Close the modal
                close_button = self.driver.find_element(By.XPATH, '/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[1]/div/div[3]/div/button')
                close_button.click()

                random_sleep(2, 3)
                return followers_count
            except TimeoutException:
                print("Failed to open followers list")
                return None
        except Exception as e:
            print(f"Error getting followers info: {str(e)}")
            return None

    def get_followings_info(self):
        try:
            print("Getting followings information...")

            # Wait for the followings link to be present
            followings_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/following/"]'))
            )

            # Get the followings count from the span
            followings_count_elem = followings_link.find_element(By.CSS_SELECTOR, 'span span')
            followings_count = int(followings_count_elem.text.replace(',', ''))
            print(f"Found {followings_count} followings")

            # Get the target object
            target = self.db.get_target(self.target_account)
            if target:
                # Store the followings count in the database
                timestamp = datetime.now(pytz.UTC)
                count_entry = Counts(target_id=target.id, count_type='followings', count=followings_count, timestamp=timestamp)
                self.db.session.add(count_entry)
                self.db.session.commit()

            # Click on the followings link to open the list
            random_sleep(1, 2)
            followings_link.click()

            # Wait for the followings modal to appear and load content
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
                )
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"] a[role="link"]'))
                )
                print("Followings list opened successfully")

                # Get current followings
                current_followings_list = store_followers(self.driver, list_type='followings')
                print(f"Fetched {len(current_followings_list)} followings")

                # Close the modal
                close_button = self.driver.find_element(By.XPATH, '/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[1]/div/div[3]/div/button')
                close_button.click()

                random_sleep(2, 3)
                return followings_count
            except TimeoutException:
                print("Failed to open followings list")
                return None
        except Exception as e:
            print(f"Error getting followings info: {str(e)}")
            return None

    def run(self):
        try:
            self.setup_driver()
            if not self.login():
                print("Failed to login, aborting...")
                return
            if not self.navigate_to_profile():
                print("Failed to load target profile, aborting...")
                return
            followers_count = self.get_followers_info()
            if followers_count is None:
                print("Failed to get followers information, aborting...")
                return
            followings_count = self.get_followings_info()
            if followings_count is None:
                print("Failed to get followings information, aborting...")
                return
        except Exception as e:
            print(f"Error in run: {str(e)}")
        finally:
            #if self.driver:
            #    self.driver.quit()
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

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
