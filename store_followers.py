from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

def store_followers(driver, list_type='followers'):
    try:
        print(f"Storing {list_type}...")
        
        # Determine selectors and filename based on list_type
        if list_type == 'followers':
            modal_selector = 'div[role="dialog"] a[role="link"]'
            filename = 'data/followers.json'
        elif list_type == 'followings':
            modal_selector = 'div[role="dialog"] a[role="link"]'
            filename = 'data/followings.json'
        else:
            raise ValueError("Invalid list_type provided")

        # Wait for the modal to be visible
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
        )

        items_list = []
        last_height = 0

        # Wait for and find the scrollable container
        scroll_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[5]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]'))
        )

        while True:
            # Get all current item elements
            item_elements = driver.find_elements(By.CSS_SELECTOR, f'div[role="dialog"] a[role="link"]')

            # Process visible elements
            for element in item_elements:
                try:
                    username = element.get_attribute('href').split('/')[-2]
                    profile_url = element.get_attribute('href').split('/?')[0]

                    if username and not any(f['username'] == username for f in items_list):
                        items_list.append({
                            'username': username,
                            'profile_url': profile_url
                        })
                except Exception as e:
                    print(f"Error processing element: {str(e)}")
                    continue

            # Scroll down
            try:
                driver.execute_script("""
                    arguments[0].scrollTo(0, arguments[0].scrollHeight);
                """, scroll_box)
                time.sleep(1.5 + (time.time() % 1))
            except Exception as e:
                print(f"Error during scrolling: {str(e)}")
                time.sleep(2)

            # Check if we've reached the bottom
            new_height = driver.execute_script('return arguments[0].scrollHeight', scroll_box)
            if new_height == last_height:
                time.sleep(2)
                new_height = driver.execute_script('return arguments[0].scrollHeight', scroll_box)
                if new_height == last_height:
                    break
            last_height = new_height

            print(f"Collected {len(items_list)} {list_type} so far...")

        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')

        # Store items in a JSON file
        with open(filename, 'w') as f:
            json.dump(items_list, f, indent=4)

        print(f"Successfully stored {len(items_list)} {list_type}")
        return items_list

    except Exception as e:
        print(f"Error storing {list_type}: {str(e)}")
        return []
