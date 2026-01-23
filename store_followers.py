from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import time
from datetime import datetime
from database import Database, FollowerFollowing
import pytz

def store_followers(driver, list_type='followers'):
    db = Database()
    print(f"Storing {list_type}...")
    
    try:
        now_utc = datetime.now(pytz.UTC)
        target_username = driver.current_url.split('/')[-2]
        print(f"Target username: {target_username}")
        
        target = db.get_target(target_username)
        if not target:
            target = db.add_target(target_username)
        target_id = target.id
        is_follower = list_type == 'followers'
        current_items = set()

        # Determine selectors based on list_type
        if list_type == 'followers':
            modal_selector = 'div[role="dialog"] a[role="link"]'
        elif list_type == 'followings':
            modal_selector = 'div[role="dialog"] a[role="link"]'
        else:
            raise ValueError("Invalid list_type provided")

        # Wait for the modal to be visible
        print("Waiting for modal to be visible...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
        )
        print("Modal is visible, looking for scroll container...")

        # Try multiple selectors for the scroll container
        scroll_box = None
        scroll_selectors = [
            # More flexible selectors for the scrollable container
            'div[role="dialog"] div[style*="overflow"]',
            'div[role="dialog"] div[style*="scroll"]',
            'div[role="dialog"] > div > div > div > div > div > div:last-child',
            # Fallback to the original XPath if others fail
            '/html/body/div[5]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]'
        ]
        
        for i, selector in enumerate(scroll_selectors):
            try:
                print(f"Trying scroll selector {i+1}: {selector}")
                if selector.startswith('/'):
                    # XPath selector
                    scroll_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    # CSS selector
                    scroll_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                print(f"Found scroll container with selector {i+1}")
                break
            except Exception as e:
                print(f"Selector {i+1} failed: {e}")
                continue
        
        if scroll_box is None:
            print("Could not find scroll container, trying to scroll the modal dialog itself")
            scroll_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
            )

        last_height = 0
        print("Starting to scroll and collect followers...")

        while True:
            item_elements = driver.find_elements(By.CSS_SELECTOR, f'div[role="dialog"] a[role="link"]')
            print(f"Found {len(item_elements)} elements in current view")
            
            for element in item_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/' in href:
                        username = href.split('/')[-2]
                        if username and username != '':
                            current_items.add(username)
                except Exception as e:
                    print(f"Error processing element: {e}")
                    continue

            print(f"Current total collected: {len(current_items)} {list_type}")

            # Scroll down
            try:
                driver.execute_script("""
                    arguments[0].scrollTo(0, arguments[0].scrollHeight);
                """, scroll_box)
            except Exception as e:
                print(f"Error scrolling: {e}")
                # Try alternative scrolling method
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(1 + (time.time() % 1))

            try:
                new_height = driver.execute_script('return arguments[0].scrollHeight', scroll_box)
            except Exception as e:
                print(f"Error getting scroll height: {e}")
                # If we can't get scroll height, check if we have new elements
                new_elements = driver.find_elements(By.CSS_SELECTOR, f'div[role="dialog"] a[role="link"]')
                if len(new_elements) == len(item_elements):
                    print("No new elements found, stopping scroll")
                    break
                continue
                
            if new_height == last_height:
                print("Reached end of scroll, no more content")
                break
            last_height = new_height

        print(f"Collected {len(current_items)} {list_type}")

        # Get the existing items from the database for comparison
        existing_items = {
            entry.follower_following_username: entry
            for entry in db.session.query(FollowerFollowing)
            .filter_by(target_id=target_id, is_follower=is_follower)
            .all()
        }

        # Add new items or update existing ones
        for username in current_items:
            if username not in existing_items:
                db.add_follower_following(target_id=target_id, username=username, is_follower=is_follower, added_at=now_utc)
            elif existing_items[username].lost_at is not None:
                existing_items[username].lost_at = None
                db.session.commit()

        # Mark items that are no longer present as lost
        for username, entry in existing_items.items():
            if username not in current_items and entry.lost_at is None:
                entry.lost_at = now_utc
                entry.is_lost = True
                db.session.commit()

        print(f"Successfully stored {len(current_items)} {list_type}")
        return list(current_items)
        
    except Exception as e:
        print(f"Error in store_followers: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
