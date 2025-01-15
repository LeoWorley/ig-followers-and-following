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
    now_utc = datetime.now(pytz.UTC)
    target_username = driver.current_url.split('/')[-2]
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
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
    )

    last_height = 0
    scroll_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div[5]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]'))
    )

    while True:
        item_elements = driver.find_elements(By.CSS_SELECTOR, f'div[role="dialog"] a[role="link"]')
        for element in item_elements:
            try:
                username = element.get_attribute('href').split('/')[-2]
                if username:
                    current_items.add(username)
            except Exception as e:
                print(f"Error processing element: {e}")
                continue

        driver.execute_script("""
            arguments[0].scrollTo(0, arguments[0].scrollHeight);
        """, scroll_box)
        time.sleep(1 + (time.time() % 1))

        new_height = driver.execute_script('return arguments[0].scrollHeight', scroll_box)
        if new_height == last_height:
            break
        last_height = new_height

    print(f" Collected {len(current_items)} {list_type}")

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
