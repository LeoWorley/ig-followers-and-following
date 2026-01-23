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
        
    def close_modal(self):
        """Attempt to close any open Instagram modal dialog."""
        try:
            close_btn = self.driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"] button[aria-label="Close"]')
            close_btn.click()
            WebDriverWait(self.driver, 5).until(EC.invisibility_of_element(close_btn))
            return True
        except Exception:
            pass
        try:
            close_svg = self.driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"] svg[aria-label="Close"]')
            close_svg.click()
            WebDriverWait(self.driver, 5).until(EC.invisibility_of_element(close_svg))
            return True
        except Exception as e:
            print(f"Modal close failed: {e}")
        # Final fallback: ESC key
        try:
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            WebDriverWait(self.driver, 3).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role=\"dialog\"]'))
            )
            return True
        except Exception as e:
            print(f"ESC close failed: {e}")
            return False
        
    def setup_driver(self, headless_override=None):
        chrome_options = Options()
        
        # Check if headless mode should be disabled (for debugging)
        if headless_override is None:
            headless_mode = os.getenv("HEADLESS_MODE", "true").lower() == "true"
        else:
            headless_mode = headless_override
        if headless_mode:
            chrome_options.add_argument("--headless")
            
        # Add arguments needed for running in Docker and general stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        # Set Chrome binary location if specified (for Docker environments)
        chrome_bin = os.getenv("CHROME_BIN")
        if chrome_bin and os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
            
        # Use a realistic user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Use ChromeDriverManager to automatically handle driver installation
        # Check if a custom driver path is specified (for Docker environments)
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
        else:
            # Use ChromeDriverManager to automatically download and manage the driver
            service = Service(ChromeDriverManager().install())
            
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        # Set window size to look more natural
        self.driver.set_window_size(1280, 800)
    
    def login(self, skip_cookie_login=False):
        try:
            print("Attempting to log in to Instagram...")
            
            # First try to use saved cookies
            if (not skip_cookie_login) and self.load_cookies():
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
                try:
                    followers_list = store_followers(self.driver, list_type='followers', target_username=self.target_account)
                    if followers_list is not None and len(followers_list) > 0:
                        print(f"Successfully scraped {len(followers_list)} followers")
                    else:
                        print("Warning: No followers were scraped")
                except Exception as e:
                    print(f"Error during followers scraping: {str(e)}")
                    # Continue anyway, don't fail the entire process

                # Close the modal
                if not self.close_modal():
                    print("Warning: Could not close followers modal via primary methods")

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
            try:
                WebDriverWait(self.driver, 5).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
                )
            except Exception:
                pass
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", followings_link)
                followings_link.click()
            except Exception as e:
                print(f"Standard click on followings link failed: {e}, trying JS click")
                self.driver.execute_script("arguments[0].click();", followings_link)

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
                try:
                    current_followings_list = store_followers(self.driver, list_type='followings', target_username=self.target_account)
                    if current_followings_list is not None and len(current_followings_list) > 0:
                        print(f"Successfully scraped {len(current_followings_list)} followings")
                    else:
                        print("Warning: No followings were scraped")
                except Exception as e:
                    print(f"Error during followings scraping: {str(e)}")
                    # Continue anyway, don't fail the entire process

                # Close the modal
                if not self.close_modal():
                    print("Warning: Could not close followings modal via primary methods")

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
                print("Failed to get followers information, but continuing...")
            else:
                print(f"Successfully processed {followers_count} followers")
                
            followings_count = self.get_followings_info()
            if followings_count is None:
                print("Failed to get followings information, but continuing...")
            else:
                print(f"Successfully processed {followings_count} followings")
        except Exception as e:
            print(f"Error in run: {str(e)}")
        finally:
            #if self.driver:
            #    self.driver.quit()
            self.db.close()
            print("Script finished")

def main():
    login_only_mode = os.getenv("LOGIN_ONLY_MODE", "false").lower() == "true"
    tracker = InstagramTracker()

    if login_only_mode:
        print("LOGIN_ONLY_MODE is enabled; opening a visible browser for manual login/2FA.")
        tracker.setup_driver(headless_override=False)
        success = tracker.login(skip_cookie_login=True)
        if success:
            print("Login-only mode succeeded. Cookies saved to instagram_cookies.json. Exiting.")
        else:
            print("Login-only mode failed. Please retry with HEADLESS_MODE=false and correct credentials.")
        tracker.db.close()
        return

    # Schedule the job to run once every 12 hours instead of every day
    # This reduces the chance of detection

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
