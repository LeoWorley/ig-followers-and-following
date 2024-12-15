from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os

def store_followers(driver):
    try:
        # Wait for the followers modal to be visible
        followers_modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
        )
        
        # Get all follower elements
        followers_list = []
        follower_elements = followers_modal.find_elements(By.CSS_SELECTOR, 'div._aacl._aaco._aacw._aacx._aad7._aade')
        
        for element in follower_elements:
            username = element.text
            if username:  # Only add non-empty usernames
                followers_list.append({
                    'username': username
                })
        
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            
        # Store followers in a JSON file
        with open('data/followers.json', 'w') as f:
            json.dump(followers_list, f, indent=4)
            
        print(f"Successfully stored {len(followers_list)} followers")
        return followers_list
        
    except Exception as e:
        print(f"Error storing followers: {str(e)}")
        return []
