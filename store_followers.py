from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime
from database import FollowerFollowing
from typing import Optional, Set, Tuple


def _align_datetimes(a, b) -> Tuple[Optional[datetime], Optional[datetime]]:
    if a is None or b is None:
        return a, b
    if (a.tzinfo is None) == (b.tzinfo is None):
        return a, b
    if a.tzinfo is None and b.tzinfo is not None:
        return a.replace(tzinfo=b.tzinfo), b
    if a.tzinfo is not None and b.tzinfo is None:
        return a, b.replace(tzinfo=a.tzinfo)
    return a, b


def _midpoint_dt(a, b) -> Optional[datetime]:
    a2, b2 = _align_datetimes(a, b)
    if a2 is None or b2 is None:
        return None
    return a2 + (b2 - a2) / 2

def _find_scroll_container(driver) -> Optional[object]:
    """
    Tries to find the scrollable container inside the Instagram modal dialog.
    Uses JS to look for the deepest element with overflow-y scroll/auto and a
    scrollable height. Falls back to None so the caller can try other methods.
    """
    try:
        scroll_box = driver.execute_script("""
            const dialog = document.querySelector('div[role="dialog"]');
            if (!dialog) return null;
            const candidates = Array.from(dialog.querySelectorAll('*')).map(el => {
                const style = getComputedStyle(el);
                const oy = style.overflowY;
                const scrollable = (oy === 'auto' || oy === 'scroll');
                const delta = el.scrollHeight - el.clientHeight;
                return { el, scrollable, delta };
            }).filter(c => c.scrollable && c.delta > 20);
            if (candidates.length === 0) return null;
            candidates.sort((a, b) => (b.delta - a.delta));
            return candidates[0].el;
        """)
        if scroll_box:
            print("Scroll container found via JS overflow detection")
        return scroll_box
    except Exception as e:
        print(f"JS scroll container detection failed: {e}")
        return None

def store_followers(
    driver,
    db,
    target,
    list_type='followers',
    run_started_at: datetime = None,
    run_id: int = None,
    prev_run_started_at: Optional[datetime] = None,
    expected_total: Optional[int] = None,
) -> Set[str]:
    """Scrape a followers/followings modal and update DB with run-aware timestamps."""
    print(f"Storing {list_type}...")

    try:
        modal_wait_seconds = int(os.getenv("SCRAPE_MODAL_WAIT_SECONDS", "10"))
        stall_timeout = int(os.getenv("SCRAPE_STALL_TIMEOUT_SECONDS", "15"))
        max_iterations = int(os.getenv("SCRAPE_MAX_ITERATIONS", "500"))
        now_utc = run_started_at if run_started_at else datetime.utcnow()
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
        WebDriverWait(driver, modal_wait_seconds).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
        )
        print("Modal is visible, looking for scroll container...")

        # First try JS-based overflow detection (handles changing class names)
        scroll_box = _find_scroll_container(driver)

        # Try multiple selectors for the scroll container if JS failed
        scroll_selectors = [
            # More flexible selectors for the scrollable container
            'div[role="dialog"] div[style*="overflow: hidden auto"]',
            'div[role="dialog"] div[style*="overflow: auto"]',
            'div[role="dialog"] div[style*="overflow"]',
            'div[role="dialog"] div[style*="scroll"]',
            'div[role="dialog"] > div > div > div > div > div > div:last-child',
            # Fallback to the original XPath if others fail
            '/html/body/div[5]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]'
        ]
        
        if scroll_box is None:
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

        # Log the chosen scroll box dimensions
        try:
            ch = driver.execute_script("return arguments[0].clientHeight;", scroll_box)
            sh = driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            print(f"Scroll box dims -> clientHeight: {ch}, scrollHeight: {sh}")
        except Exception:
            pass

        last_height = 0
        stable_iterations = 0
        last_count = 0
        last_change_ts = time.time()
        print("Starting to scroll and collect followers...")

        loop = 0
        while loop < max_iterations:
            loop += 1
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
                # full jump to bottom, then a small nudge to trigger lazy-load
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].clientHeight * 0.2;", scroll_box)
            except Exception as e:
                print(f"Error scrolling: {e}")
                # Try alternative scrolling method
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(1.0 + (time.time() % 0.5))

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

            if new_height == last_height and len(current_items) == last_count:
                stable_iterations += 1
                print(f"No growth detected (iteration {stable_iterations}); height={new_height}, count={len(current_items)}")
            else:
                stable_iterations = 0
                last_change_ts = time.time()
            last_height = new_height
            last_count = len(current_items)

            # Stop after several iterations without growth or after stall timeout
            if stable_iterations >= 5 or (time.time() - last_change_ts) > stall_timeout:
                print("Reached end of scroll, no more content")
                break
        else:
            print("Reached max scroll iterations cap; stopping to avoid infinite loop.")

        print(f"Collected {len(current_items)} {list_type}")

        # Get the existing items from the database for comparison
        existing_items = {
            entry.follower_following_username: entry
            for entry in db.session.query(FollowerFollowing)
            .filter_by(target_id=target_id, is_follower=is_follower)
            .all()
        }
        active_existing_count = sum(1 for entry in existing_items.values() if not entry.is_lost)

        # Add new items or update existing ones
        for username in current_items:
            if username not in existing_items:
                est_added = None
                if prev_run_started_at:
                    est_added = _midpoint_dt(prev_run_started_at, run_started_at)
                ff = FollowerFollowing(
                    target_id=target_id,
                    follower_following_username=username,
                    is_follower=is_follower,
                    added_at=now_utc,
                    first_seen_run_at=run_started_at,
                    last_seen_run_at=run_started_at,
                    estimated_added_at=est_added,
                    is_lost=False,
                )
                db.session.add(ff)
            else:
                ff = existing_items[username]
                if ff.first_seen_run_at is None:
                    ff.first_seen_run_at = ff.added_at or run_started_at
                ff.last_seen_run_at = run_started_at
                ff.is_lost = False
                ff.lost_at = None
                ff.lost_at_run_at = None
        db.session.commit()

        min_coverage_for_lost = float(os.getenv("SCRAPE_MIN_COVERAGE_FOR_LOST", "0.9"))
        min_reference_count = int(os.getenv("SCRAPE_MIN_REFERENCE_COUNT_FOR_LOST", "100"))
        ref_expected = int(expected_total or 0)
        reference_count = max(ref_expected, active_existing_count)
        apply_lost = True

        if reference_count >= min_reference_count:
            if len(current_items) == 0:
                apply_lost = False
                print(
                    f"Safety guard activated for {list_type}: scraped 0 while reference_count={reference_count}. "
                    "Skipping lost marking for this run."
                )
            else:
                coverage = len(current_items) / float(reference_count)
                if coverage < min_coverage_for_lost:
                    apply_lost = False
                    print(
                        f"Safety guard activated for {list_type}: coverage={coverage:.3f} "
                        f"(scraped={len(current_items)}, reference={reference_count}, threshold={min_coverage_for_lost}). "
                        "Skipping lost marking for this run."
                    )

        # Mark items that are no longer present as lost (only when scrape coverage is trusted)
        if apply_lost:
            for username, entry in existing_items.items():
                if username not in current_items and not entry.is_lost:
                    entry.is_lost = True
                    entry.lost_at = run_started_at
                    entry.lost_at_run_at = run_started_at
                    if entry.last_seen_run_at is None:
                        entry.last_seen_run_at = run_started_at
                    if entry.last_seen_run_at:
                        entry.estimated_removed_at = _midpoint_dt(entry.last_seen_run_at, run_started_at)
                    else:
                        entry.estimated_removed_at = run_started_at
            db.session.commit()

        print(f"Successfully stored {len(current_items)} {list_type}")
        return current_items

    except Exception as e:
        print(f"Error in store_followers: {str(e)}")
        import traceback
        traceback.print_exc()
        return set()
