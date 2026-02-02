import os
import time
import json
import random
import sys
import threading
import logging
import signal
import subprocess
import atexit
from logging.handlers import RotatingFileHandler
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
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from store_followers import store_followers
from alerting import send_alert

# Load environment variables
load_dotenv()


def setup_logging():
    if getattr(setup_logging, "_configured", False):
        return
    setup_logging._configured = True

    log_file = os.getenv("LOG_FILE", "tracker.log")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "5242880"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3"))

    logger = logging.getLogger()
    logger.setLevel(log_level)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if log_console and sys.__stdout__:
        console_handler = logging.StreamHandler(sys.__stdout__)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    class StreamToLogger:
        def __init__(self, target_logger, level):
            self.logger = target_logger
            self.level = level

        def write(self, message):
            if not message:
                return
            for line in message.rstrip().splitlines():
                self.logger.log(self.level, line)

        def flush(self):
            pass

    sys.stdout = StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger("stderr"), logging.ERROR)
    logging.captureWarnings(True)

def random_sleep(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def random_scroll():
    return random.uniform(0.3, 0.7)


class SingleInstanceLock:
    def __init__(self, lock_path):
        self.lock_path = lock_path
        self.acquired = False

    def _is_pid_alive(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def acquire(self):
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(str(os.getpid()))
                self.acquired = True
                return True
            except FileExistsError:
                try:
                    with open(self.lock_path, "r", encoding="utf-8") as handle:
                        pid_text = handle.read().strip()
                    pid = int(pid_text) if pid_text else None
                except Exception:
                    pid = None
                if pid and self._is_pid_alive(pid):
                    return False
                try:
                    os.remove(self.lock_path)
                    continue
                except OSError:
                    return False

    def release(self):
        if not self.acquired:
            return
        try:
            os.remove(self.lock_path)
        except OSError:
            pass
        self.acquired = False

class InstagramTracker:
    def __init__(self):
        self.db = Database()
        self.username = os.getenv('IG_USERNAME')
        self.password = os.getenv('IG_PASSWORD')
        self.target_account = os.getenv('TARGET_ACCOUNT')
        self.driver = None
        self.driver_service = None
        self.driver_service_pid = None
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
        self.driver_service = service
        try:
            self.driver_service_pid = self.driver_service.process.pid
        except Exception:
            self.driver_service_pid = None
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
                    lambda d: self.is_logged_in()
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

    def has_session_cookie(self):
        try:
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                if cookie.get("name") == "sessionid" and cookie.get("value"):
                    return True
            return False
        except Exception:
            return False

    def is_logged_in(self):
        if self.has_session_cookie():
            return True
        try:
            if self.driver.find_elements(By.CSS_SELECTOR, "#loginForm"):
                return False
        except Exception:
            pass
        try:
            self.driver.find_element(By.CSS_SELECTOR, "nav")
            return True
        except Exception:
            return False

    def wait_for_login(self, timeout_seconds=None, poll_interval=2, allow_manual_confirm=True):
        print("Waiting for login to complete. Finish login/2FA in the browser.")
        manual_event = threading.Event()
        manual_checked = False

        if allow_manual_confirm and sys.stdin and sys.stdin.isatty():
            def wait_input():
                try:
                    input("Press Enter here after you finish login/2FA to save cookies...")
                    manual_event.set()
                except EOFError:
                    pass

            input_thread = threading.Thread(target=wait_input, daemon=True)
            input_thread.start()

        start_time = time.time()
        while True:
            if self.is_logged_in():
                return True
            if manual_event.is_set() and not manual_checked:
                manual_checked = True
                if self.has_session_cookie():
                    print("Manual confirmation received and session cookie detected.")
                    return True
                print("Manual confirmation received but login not detected yet; continuing to wait...")

            if timeout_seconds is not None and (time.time() - start_time) > timeout_seconds:
                return False
            time.sleep(poll_interval)
    
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

    def get_followers_info(self, target, run_started_at, run_id, prev_run_started_at):
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
            # Store the followers count in the database
            if target:
                self.db.add_count(
                    target_id=target.id,
                    count_type='followers',
                    count=followers_count,
                    timestamp=run_started_at,
                    run_id=run_id
                )
            

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
                followers_list = set()
                try:
                    followers_list = store_followers(
                        self.driver,
                        db=self.db,
                        target=target,
                        list_type='followers',
                        run_started_at=run_started_at,
                        run_id=run_id,
                        prev_run_started_at=prev_run_started_at
                    )
                    if followers_list is not None and len(followers_list) > 0:
                        print(f"Successfully scraped {len(followers_list)} followers")
                    else:
                        print("Warning: No followers were scraped")
                        if followers_count > 0:
                            print("Retrying followers scrape once...")
                            followers_list = store_followers(
                                self.driver,
                                db=self.db,
                                target=target,
                                list_type='followers',
                                run_started_at=run_started_at,
                                run_id=run_id,
                                prev_run_started_at=prev_run_started_at
                            )
                            print(f"Retry followers scraped: {len(followers_list)}")
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

    def get_followings_info(self, target, run_started_at, run_id, prev_run_started_at):
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
            if target:
                self.db.add_count(
                    target_id=target.id,
                    count_type='followings',
                    count=followings_count,
                    timestamp=run_started_at,
                    run_id=run_id
                )

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
                current_followings_list = set()
                try:
                    current_followings_list = store_followers(
                        self.driver,
                        db=self.db,
                        target=target,
                        list_type='followings',
                        run_started_at=run_started_at,
                        run_id=run_id,
                        prev_run_started_at=prev_run_started_at
                    )
                    if current_followings_list is not None and len(current_followings_list) > 0:
                        print(f"Successfully scraped {len(current_followings_list)} followings")
                    else:
                        print("Warning: No followings were scraped")
                        if followings_count > 0:
                            print("Retrying followings scrape once...")
                            current_followings_list = store_followers(
                                self.driver,
                                db=self.db,
                                target=target,
                                list_type='followings',
                                run_started_at=run_started_at,
                                run_id=run_id,
                                prev_run_started_at=prev_run_started_at
                            )
                            print(f"Retry followings scraped: {len(current_followings_list)}")
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
        run_started_at = datetime.now(pytz.UTC)
        run_record = None
        followers_collected = 0
        followings_collected = 0
        result = {"status": "failed", "error": None}
        try:
            self.setup_driver()
            if not self.login():
                print("Failed to login, aborting...")
                result["error"] = "login_failed"
                return result
            if not self.navigate_to_profile():
                print("Failed to load target profile, aborting...")
                result["error"] = "profile_load_failed"
                return result

            target = self.db.get_or_create_target(self.target_account)
            prev_run = self.db.get_last_run(target.id)
            prev_run_started_at = prev_run.run_started_at if prev_run else None
            run_record = self.db.start_run(target.id, run_started_at)
            run_id = run_record.id

            followers_count = self.get_followers_info(target, run_started_at, run_id, prev_run_started_at)
            if followers_count is None:
                print("Failed to get followers information, but continuing...")
            else:
                print(f"Successfully processed {followers_count} followers")
                followers_collected = followers_count

            followings_count = self.get_followings_info(target, run_started_at, run_id, prev_run_started_at)
            if followings_count is None:
                print("Failed to get followings information, but continuing...")
            else:
                print(f"Successfully processed {followings_count} followings")
                followings_collected = followings_count

            if run_record:
                self.db.finish_run(run_record.id, status="success",
                                   followers_collected=followers_collected,
                                   followings_collected=followings_collected,
                                   finished_at=datetime.now(pytz.UTC))
            result["status"] = "success"
            result["followers_collected"] = followers_collected
            result["followings_collected"] = followings_collected
        except Exception as e:
            print(f"Error in run: {str(e)}")
            result["error"] = str(e)
            if run_record:
                self.db.finish_run(run_record.id, status="failed",
                                   followers_collected=followers_collected,
                                   followings_collected=followings_collected,
                                   finished_at=datetime.now(pytz.UTC))
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logging.exception("Driver quit failed: %s", e)
            self._force_kill_driver()
            self.db.close()
            print("Script finished")
        return result

    def _force_kill_driver(self):
        default_force = "true" if os.name == "nt" else "false"
        force_kill = os.getenv("FORCE_KILL_CHROME", default_force).lower() == "true"
        if not force_kill:
            return
        pid = self.driver_service_pid
        if not pid:
            return
        try:
            logging.info("Force-killing ChromeDriver process tree (pid=%s)", pid)
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            logging.exception("Force-kill failed: %s", e)


def main():
    setup_logging()
    disable_run_lock = os.getenv("DISABLE_RUN_LOCK", "false").lower() == "true"
    lock = None
    if not disable_run_lock:
        lock_file = os.getenv("LOCK_FILE", "tracker.lock")
        lock = SingleInstanceLock(lock_file)
        if not lock.acquire():
            print(f"Another tracker instance is already running (lock: {lock_file}). Exiting.")
            return
        atexit.register(lock.release)

    login_only_mode = os.getenv("LOGIN_ONLY_MODE", "false").lower() == "true"
    interval_minutes = int(os.getenv("RUN_INTERVAL_MINUTES", "60"))
    jitter_seconds = int(os.getenv("RUN_JITTER_SECONDS", "120"))
    login_only_timeout = os.getenv("LOGIN_ONLY_TIMEOUT_SECONDS")
    login_only_timeout_seconds = None
    if login_only_timeout:
        try:
            login_only_timeout_seconds = int(login_only_timeout)
        except ValueError:
            print("Invalid LOGIN_ONLY_TIMEOUT_SECONDS; ignoring and waiting indefinitely.")

    if login_only_mode:
        tracker = InstagramTracker()
        print("LOGIN_ONLY_MODE is enabled; opening a visible browser for manual login/2FA.")
        tracker.setup_driver(headless_override=False)
        try:
            # Use the normal login flow to submit credentials, then wait for manual completion
            success = tracker.login(skip_cookie_login=True)
            if not success:
                print("Login not confirmed yet. Waiting for manual completion...")
                success = tracker.wait_for_login(timeout_seconds=login_only_timeout_seconds)
                if success:
                    tracker.save_cookies()
            if success:
                print("Login-only mode succeeded. Cookies saved to instagram_cookies.json. Exiting.")
            else:
                print("Login-only mode timed out. Please retry with HEADLESS_MODE=false and correct credentials.")
                send_alert(
                    "login_only_failed",
                    "Instagram tracker login-only failed",
                    "Login-only mode timed out or did not detect a valid session cookie.",
                    level="warning",
                )
        finally:
            if tracker.driver:
                try:
                    tracker.driver.quit()
                except Exception:
                    pass
            tracker.db.close()
        return

    while True:
        tracker = InstagramTracker()
        run_result = tracker.run()
        if run_result.get("status") != "success":
            send_alert(
                "tracker_run_failed",
                "Instagram tracker run failed",
                f"Run failed. Reason: {run_result.get('error', 'unknown')}",
                level="error",
            )
        elif os.getenv("ALERT_ON_SUCCESS", "false").lower() == "true":
            send_alert(
                "tracker_run_success",
                "Instagram tracker run succeeded",
                (
                    f"Followers processed: {run_result.get('followers_collected', 0)}, "
                    f"followings processed: {run_result.get('followings_collected', 0)}"
                ),
                level="info",
            )
        sleep_seconds = interval_minutes * 60 + random.randint(0, jitter_seconds)
        print(f"Sleeping for {sleep_seconds} seconds until next run...")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
