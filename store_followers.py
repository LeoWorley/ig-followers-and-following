from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import time

def store_followers(driver):
    try:
        # Wait for the followers modal to be visible
        followers_modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"] a[role="link"]'))
        )
        
        # Initialize variables for scrolling
        followers_list = []
        last_height = 0
        
        # Wait for and find the scrollable container
        scroll_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[5]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]'))
        )
        
        while True:
            # Get all current follower elements
            follower_elements = driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] a[role="link"]')
            
            # Process visible elements
            for element in follower_elements:
                try:
                    # Find username using a more reliable selector
                    username = element.get_attribute('href').split('/')[-2]  # Get username from URL
                    profile_url = element.get_attribute('href').split('/?')[0]
                    
                    # Only add if not already in list and valid username
                    if username and not any(f['username'] == username for f in followers_list):
                        followers_list.append({
                            'username': username,
                            'profile_url': profile_url
                        })
                except Exception as e:
                    print(f"Error processing follower element: {str(e)}")
                    continue
            
            # Scroll down
            try:
                driver.execute_script("""
                    arguments[0].scrollTo(0, arguments[0].scrollHeight);
                """, scroll_box)
                
                # Add a small random delay between 1.5 and 2.5 seconds to mimic human behavior
                time.sleep(1.5 + (time.time() % 1))
            except Exception as e:
                print(f"Error during scrolling: {str(e)}")
                time.sleep(2)
            
            # Check if we've reached the bottom
            new_height = driver.execute_script('return arguments[0].scrollHeight', scroll_box)
            if new_height == last_height:
                # Try one more time to ensure we're really at the bottom
                time.sleep(2)
                new_height = driver.execute_script('return arguments[0].scrollHeight', scroll_box)
                if new_height == last_height:
                    break
            last_height = new_height
            
            print(f"Collected {len(followers_list)} followers so far...")
            
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
