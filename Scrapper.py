import csv
import traceback
import time
import re  # Import regular expressions for flexible matching
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException, 
    StaleElementReferenceException, 
    TimeoutException, 
    WebDriverException,
    NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager

# -------------------------------
# Read Cities from File
# -------------------------------
with open("german_cities.txt", "r", encoding="utf-8") as cities_file:
    cities = [line.strip() for line in cities_file if line.strip()]

for city in cities:
    # -------------------------------
    # Setup Chrome WebDriver for each city
    # -------------------------------
    service = Service(ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--lang=ar")  # Set language to Arabic
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'ar,ar_AE'})
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)
    
    try:
        print("🚀 Opening Google Maps in Arabic...")
        driver.get("https://www.google.com/maps/?hl=ar")  # Force Arabic interface
        wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
        
        # Set cookies for Arabic language
        driver.add_cookie({"name": "PREF", "value": "hl=ar"})
        driver.refresh()
        wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
    
        search_query = f"Restaurants in {city}"
        print(f"🔎 Searching for {search_query}...")
        
        search_box = driver.find_element(By.ID, "searchboxinput")
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.ENTER)
        
        # Wait for results to load
        print("⏳ Waiting for results to load...")
        feed_container = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
        time.sleep(2)  # Allow initial results to fully load

        # Helper functions for the script
        def is_page_loading():
            try:
                return driver.execute_script("return document.readyState") != "complete" or \
                       driver.execute_script("return window.performance.getEntriesByType('resource').some(r => r.initiatorType === 'xmlhttprequest')")
            except Exception:
                return False

        def is_panel_open():
            """Check if the details panel is currently open"""
            try:
                # Check for multiple panel indicators - any of these means panel is open
                title_present = len(driver.find_elements(By.XPATH, "//h1[contains(@class, 'DUwDvf')]")) > 0
                back_button = len(driver.find_elements(By.XPATH, "//button[@aria-label='Back']")) > 0
                phone_elements = len(driver.find_elements(By.XPATH, "//button[contains(@data-item-id, 'phone')]")) > 0
                
                return title_present or back_button or phone_elements
            except:
                return False
        
        def go_back_to_results():
            """Try multiple methods to get back to results list"""
            for attempt in range(3):
                try:
                    # Try regular back button first
                    back_button = driver.find_element(By.XPATH, "//button[@aria-label='Back']")
                    back_button.click()
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                    )
                    print("◀️ Back to results")
                    return True
                except:
                    try:
                        # Try JavaScript history navigation
                        driver.execute_script("window.history.go(-1)")
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                        )
                        print("◀️ Back using history")
                        return True
                    except:
                        pass
                    
                    time.sleep(0.5)  # Short pause before next attempt
            
            # If all attempts failed, try a hard refresh
            try:
                print("⚠️ Failed to go back, refreshing search...")
                driver.get("https://www.google.com/maps/?hl=ar")
                wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
                search_box = driver.find_element(By.ID, "searchboxinput")
                search_box.clear()
                search_box.send_keys(search_query)
                search_box.send_keys(Keys.ENTER)
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
                return True
            except:
                print("❌ Failed to recover search view")
                return False

        # Completely reload to ensure fresh start for extraction
        driver.get("https://www.google.com/maps/?hl=ar")
        wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
        search_box = driver.find_element(By.ID, "searchboxinput")
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.ENTER)
        feed_container = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
        time.sleep(2)  # Allow initial results to fully load
        
        # Scroll continuously to load all results
        print("🔄 Loading all results by scrolling...")
        previous_total_results = 0
        scroll_attempts = 0
        found_end_of_list = False
        no_change_count = 0
        last_clicked_index = -1  # Track the last index we clicked to try to trigger more loading
        
        # Scroll until we explicitly find the end message - NO OTHER TERMINATION
        while not found_end_of_list:
            scroll_attempts += 1
            
            # Get current count
            results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
            current_total_results = len(results)
            
            # Scroll down - vary the scroll amount to prevent getting stuck
            if scroll_attempts % 3 == 0:
                driver.execute_script("arguments[0].scrollTop += 1500;", feed_container)
            elif scroll_attempts % 3 == 1:
                driver.execute_script("arguments[0].scrollTop += 800;", feed_container)
            else:
                driver.execute_script("arguments[0].scrollTop += 1200;", feed_container)
            
            # ALWAYS check for end message after EVERY scroll
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Very thorough check for end messages in multiple languages
            if ("end of the list" in page_text.lower() or 
                "لقد وصلت إلى نهاية القائمة" in page_text or 
                "نهاية القائمة" in page_text.lower() or
                "نهاية النتائج" in page_text.lower() or
                "keine weiteren ergebnisse" in page_text or
                "ende der liste" in page_text.lower() or
                "end of results" in page_text.lower() or
                "no more results" in page_text.lower()):
                print("🏁 FOUND END OF LIST MESSAGE!")
                print(f"🔢 Total restaurants found: {current_total_results}")
                found_end_of_list = True
                break
            
            # Check if we're getting new results
            if current_total_results > previous_total_results:
                previous_total_results = current_total_results
                no_change_count = 0  # Reset counter when we find new results
            else:
                no_change_count += 1
            
            # Report progress every few scrolls
            if scroll_attempts % 5 == 0:
                print(f"📊 Scroll {scroll_attempts}: Found {current_total_results} restaurants so far")
                
                if no_change_count == 0:
                    print(f"  ➕ New restaurants found, continuing to scroll...")
                else:
                    print(f"  🔍 No new restaurants for {no_change_count} scrolls, still searching for end message...")
                
                # If stuck for a long time, try more aggressive scrolling but NEVER terminate prematurely
                if no_change_count >= 20:
                    # Try increasingly aggressive scrolling techniques
                    print("  🔄 Trying aggressive scroll methods...")
                    
                    # Try multiple scroll distances in sequence
                    for jump in [3000, 5000, 10000]:
                        driver.execute_script(f"arguments[0].scrollTop += {jump};", feed_container)
                        time.sleep(0.5)
                        
                        # Re-check for end message after each jump
                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        if ("end of the list" in page_text.lower() or 
                            "لقد وصلت إلى نهاية القائمة" in page_text or
                            "نهاية القائمة" in page_text.lower() or
                            "نهاية النتائج" in page_text.lower() or 
                            "keine weiteren ergebnisse" in page_text):
                            print("🏁 FOUND END OF LIST MESSAGE AFTER AGGRESSIVE SCROLL!")
                            print(f"🔢 Total restaurants found: {current_total_results}")
                            found_end_of_list = True
                            break
                    
                    # Try to click any "View more" buttons if they exist
                    if not found_end_of_list:
                        try:
                            more_buttons = driver.find_elements(By.XPATH, 
                                "//button[contains(text(), 'Show more') or contains(text(), 'View more') or contains(text(), 'Mehr anzeigen')]")
                            if more_buttons:
                                print("  🖱️ Found 'Show more' button, clicking it...")
                                more_buttons[0].click()
                                time.sleep(1)
                        except:
                            pass
                    
                    # Try clicking on results to trigger loading - check 3 different positions
                    if not found_end_of_list and current_total_results > 0:
                        # Determine which results to click based on last attempts
                        click_positions = []
                        
                        # Try last result first
                        if last_clicked_index != current_total_results - 1:
                            click_positions.append(current_total_results - 1)
                        
                        # Try middle result
                        mid_idx = current_total_results // 2
                        if last_clicked_index != mid_idx:
                            click_positions.append(mid_idx)
                        
                        # Try result just before the visible end
                        near_end_idx = max(0, current_total_results - 3)
                        if last_clicked_index != near_end_idx:
                            click_positions.append(near_end_idx)
                        
                        for pos in click_positions:
                            if pos >= len(results):
                                continue
                                
                            try:
                                print(f"  🖱️ Clicking result #{pos+1} to trigger more loading...")
                                target_result = results[pos]
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_result)
                                time.sleep(0.5)
                                
                                # Open and close the result to trigger loading behavior
                                try:
                                    target_result.click()
                                    time.sleep(0.5)
                                    back_btn = driver.find_element(By.XPATH, "//button[@aria-label='Back'] | //button[@aria-label='رجوع']")
                                    back_btn.click()
                                    WebDriverWait(driver, 3).until(
                                        EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                                    )
                                    last_clicked_index = pos  # Update the last clicked index
                                    
                                    # Scroll a bit more
                                    driver.execute_script("arguments[0].scrollTop += 400;", feed_container)
                                    time.sleep(0.5)
                                    
                                    # Check if we got new results
                                    results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                                    if len(results) > current_total_results:
                                        print(f"  ✓ Clicking result #{pos+1} helped! Found {len(results) - current_total_results} new results")
                                        current_total_results = len(results)
                                        previous_total_results = current_total_results
                                        no_change_count = 0
                                        break
                                    
                                except:
                                    # If we can't click back, try to recover
                                    try:
                                        driver.execute_script("window.history.go(-1)")
                                        time.sleep(0.5)
                                    except:
                                        pass
                            except:
                                continue
                        
                        # If nothing worked with clicks, try refreshing the page
                        if no_change_count >= 30:
                            try:
                                print("  🔄 Trying to refresh the page...")
                                current_scroll = driver.execute_script("return arguments[0].scrollTop;", feed_container)
                                
                                driver.refresh()
                                wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
                                feed_container = driver.find_element(By.XPATH, "//div[@role='feed']")
                                
                                # Scroll back to approximately where we were 
                                for _ in range(min(20, scroll_attempts // 5)):
                                    driver.execute_script("arguments[0].scrollTop += 1000;", feed_container)
                                    time.sleep(0.3)
                                
                                # Reset counters to give it some more attempts
                                if no_change_count >= 40:
                                    no_change_count = 15
                            except:
                                pass
            
            # Brief pause for loading, keep it minimal
            time.sleep(0.3)
        
        # Store total for extraction phase
        total_restaurants_available = current_total_results
        print(f"🔢 TOTAL RESTAURANTS IN {city.upper()}: {total_restaurants_available}")
        
        # Scroll back to top for extraction
        print("⏫ Scrolling back to top to begin extraction...")
        driver.execute_script("arguments[0].scrollTop = 0;", feed_container)
        time.sleep(1)  # Wait for scroll to complete

        # -------------------------------
        # PHASE 2: Extract data one by one from the beginning
        # -------------------------------
        print("\n🔍 PHASE 2: Extracting data from all restaurants...")
        processed_restaurants = set()
        failed_attempts = set()
        
        # Set up CSV file
        filename = f"restaurants_{city.replace(' ', '_')}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Name", "Phone", "Website"])
            
            current_index = 0
            MAX_ATTEMPTS_PER_RESTAURANT = 1000000  # Virtually unlimited attempts
            
            def ensure_back_to_results():
                """Ensure we're back at the results view"""
                try:
                    # Check if we're already on results page
                    feed_visible = len(driver.find_elements(By.XPATH, "//div[@role='feed']")) > 0
                    if feed_visible:
                        return True
                        
                    # Try back button first
                    back_buttons = driver.find_elements(By.XPATH, "//button[@aria-label='Back'] | //button[@aria-label='رجوع']")
                    if back_buttons:
                        back_buttons[0].click()
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                        )
                        return True
                except:
                    pass
                    
                # Full reload as last resort
                try:
                    driver.get("https://www.google.com/maps/?hl=ar")
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "searchboxinput")))
                    search_box = driver.find_element(By.ID, "searchboxinput")
                    search_box.clear()
                    search_box.send_keys(search_query)
                    search_box.send_keys(Keys.ENTER)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
                    return True
                except:
                    return False
            
            while current_index < total_restaurants_available:
                # Make sure we're at results view
                if not ensure_back_to_results():
                    print("❌ Critical error: Cannot return to results view")
                    break
                    
                # Get fresh results list
                feed_container = driver.find_element(By.XPATH, "//div[@role='feed']")
                results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                
                # If we need to scroll to see this result
                if current_index >= len(results):
                    print(f"⏬ Scrolling to find result #{current_index+1}...")
                    driver.execute_script(f"arguments[0].scrollTop += 1000;", feed_container)
                    time.sleep(0.5)
                    results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                    
                    # If still not found, try scrolling more
                    if current_index >= len(results):
                        print("⚠️ Result not visible after scrolling, trying again...")
                        driver.execute_script(f"arguments[0].scrollTop += 2000;", feed_container)
                        time.sleep(0.5)
                        results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                        
                        if current_index >= len(results):
                            print(f"❌ Cannot find result #{current_index+1}, skipping")
                            current_index += 1
                            continue
                
                # Progress report
                if current_index % 5 == 0:
                    print(f"👉 Processing restaurant {current_index+1} of {total_restaurants_available}")
                
                # Get the restaurant element
                try:
                    # Get the current restaurant
                    result = results[current_index]
                    
                    # Extract name before clicking
                    try:
                        name_elem = result.find_element(By.XPATH, ".//div[contains(@class, 'qBF1Pd')]")
                        list_name = name_elem.text.strip()
                        if not list_name:
                            raise ValueError("Empty name")
                    except Exception:
                        print("⚠️ Could not get restaurant name, trying next...")
                        current_index += 1
                        continue
                    
                    # Check for duplicates
                    if list_name in processed_restaurants:
                        print(f"⏩ Already processed: {list_name}")
                        current_index += 1
                        continue
                    
                    print(f"\n📍 Processing #{current_index+1}: {list_name}")
                    
                    # Scroll to make sure element is in view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", result)
                    time.sleep(0.2)  # Brief pause to stabilize view
                    
                    # Try to click and extract - with reasonable retries
                    name_verified = False
                    extraction_success = False
                    attempts = 0
                    
                    while not extraction_success and attempts < MAX_ATTEMPTS_PER_RESTAURANT:
                        attempts += 1
                        if attempts % 3 == 0:
                            print(f"🔄 Attempt {attempts} for {list_name}...")
                        
                        try:
                            # Click on result - try both methods
                            try:
                                result.click()
                            except:
                                driver.execute_script("arguments[0].click();", result)
                            
                            # Wait for panel to open
                            details_panel = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'DUwDvf')]"))
                            )
                            
                            # Verify name matches
                            details_name = details_panel.text.strip()
                            
                            # Check if panel name matches list name
                            if details_name.lower() == list_name.lower() or list_name.lower() in details_name.lower() or details_name.lower() in list_name.lower():
                                name_verified = True
                                print(f"✓ Name verified: {details_name}")
                            else:
                                print(f"⚠️ Name mismatch. Expected: {list_name}, Got: {details_name}")
                                # Go back and try again
                                driver.find_element(By.XPATH, "//button[@aria-label='Back'] | //button[@aria-label='رجوع']").click()
                                WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                                )
                                results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                                if current_index < len(results):
                                    result = results[current_index]
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", result)
                                    time.sleep(0.2)
                                continue
                            
                            # Extract data once name is verified
                            phone = "N/A"
                            website = "N/A"
                            
                            # Extract phone - fast check
                            phone_elements = driver.find_elements(By.XPATH, "//button[contains(@data-item-id, 'phone')] | //button[contains(@aria-label, 'Phone')] | //button[contains(@aria-label, 'الهاتف')]")
                            if phone_elements:
                                phone = phone_elements[0].get_attribute("aria-label").replace("Phone: ", "").replace("الهاتف: ", "").strip()
                                print(f"📞 Phone: {phone}")
                            
                            # Extract website - fast check
                            website_elements = driver.find_elements(By.XPATH, "//a[contains(@data-item-id, 'authority')] | //a[contains(@aria-label, 'Website')] | //a[contains(@aria-label, 'الموقع الإلكتروني')]")
                            if website_elements:
                                website = website_elements[0].get_attribute("href")
                                print(f"🌐 Website: {website}")
                            
                            # Save data
                            writer.writerow([list_name, phone, website])
                            processed_restaurants.add(list_name)
                            print(f"✅ Data saved for: {list_name}")
                            extraction_success = True
                            
                            # Go back to results view
                            back_button = driver.find_element(By.XPATH, "//button[@aria-label='Back'] | //button[@aria-label='رجوع']")
                            back_button.click()
                            WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                            )
                        except Exception as e:
                            if attempts % 3 == 0:  # Only log every few attempts to reduce output
                                print(f"⚠️ Attempt {attempts} failed: {str(e)[:50]}...")
                            
                            # Make sure we get back to results
                            ensure_back_to_results()
                            
                            # Refresh our references
                            results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                            if current_index < len(results):
                                result = results[current_index]
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", result)
                                time.sleep(0.2)
                    
                    # If extraction failed after all attempts
                    if not extraction_success:
                        print(f"⚠️ Failed to extract data for {list_name} after {attempts} attempts")
                        failed_attempts.add(list_name)
                    
                    # Move to next restaurant
                    current_index += 1
                    
                except Exception as restaurant_error:
                    print(f"❌ Error at index {current_index}: {str(restaurant_error)[:50]}...")
                    ensure_back_to_results()
                    current_index += 1

            # Final report
            print(f"\n📊 Final Results for {city}:")
            print(f"✅ Successfully extracted {len(processed_restaurants)} restaurants")
            print(f"⚠️ Failed to extract {len(failed_attempts)} restaurants")
            print(f"📋 Total restaurants found: {total_restaurants_available}")
            
            # Check for missing restaurants
            if len(processed_restaurants) + len(failed_attempts) < total_restaurants_available:
                missing_count = total_restaurants_available - (len(processed_restaurants) + len(failed_attempts))
                print(f"⚠️ WARNING: {missing_count} restaurants were skipped! Trying to recover them...")
                
                # Reset to top and try one more pass for missing restaurants
                driver.execute_script("arguments[0].scrollTop = 0;", feed_container)
                time.sleep(1)
                
                # Get a fresh list of all restaurants
                all_results = []
                previous_count = 0
                
                # Pre-load all results
                print("🔄 Pre-loading all results again to find missing restaurants...")
                while True:
                    results = driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")
                    current_count = len(results)
                    
                    if current_count >= total_restaurants_available or current_count == previous_count:
                        all_results = results
                        break
                        
                    driver.execute_script("arguments[0].scrollTop += 2000;", feed_container)
                    time.sleep(0.5)
                    previous_count = current_count
                
                # Extract names of all restaurants
                print("🔍 Checking for missing restaurants...")
                all_restaurant_names = []
                for res in all_results:
                    try:
                        name_elem = res.find_element(By.XPATH, ".//div[contains(@class, 'qBF1Pd')]")
                        name = name_elem.text.strip()
                        if name:
                            all_restaurant_names.append(name)
                    except:
                        pass
                
                # Find missing restaurants
                missing_restaurants = []
                for name in all_restaurant_names:
                    if name not in processed_restaurants and name not in failed_attempts:
                        missing_restaurants.append(name)
                
                print(f"🔍 Found {len(missing_restaurants)} missing restaurants: {', '.join(missing_restaurants[:5])}{'...' if len(missing_restaurants) > 5 else ''}")
                
                # Process missing restaurants
                for missing_name in missing_restaurants:
                    print(f"\n📍 Processing missing restaurant: {missing_name}")
                    
                    # Find the restaurant in the list
                    found = False
                    for res in all_results:
                        try:
                            name_elem = res.find_element(By.XPATH, ".//div[contains(@class, 'qBF1Pd')]")
                            if name_elem.text.strip() == missing_name:
                                # We found it, now try to extract
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", res)
                                time.sleep(0.3)
                                
                                attempts = 0
                                extraction_success = False
                                while not extraction_success and attempts < MAX_ATTEMPTS_PER_RESTAURANT:
                                    attempts += 1
                                    if attempts % 3 == 0:
                                        print(f"🔄 Attempt {attempts} for {missing_name}...")
                                    
                                    try:
                                        # Click on result
                                        try:
                                            res.click()
                                        except:
                                            driver.execute_script("arguments[0].click();", res)
                                        
                                        # Wait for panel to open
                                        details_panel = WebDriverWait(driver, 5).until(
                                            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'DUwDvf')]"))
                                        )
                                        
                                        # Verify name matches
                                        details_name = details_panel.text.strip()
                                        
                                        if details_name.lower() == missing_name.lower() or missing_name.lower() in details_name.lower() or details_name.lower() in missing_name.lower():
                                            print(f"✓ Name verified: {details_name}")
                                            
                                            # Extract data
                                            phone = "N/A"
                                            website = "N/A"
                                            
                                            # Extract phone - fast check
                                            phone_elements = driver.find_elements(By.XPATH, "//button[contains(@data-item-id, 'phone')] | //button[contains(@aria-label, 'Phone')] | //button[contains(@aria-label, 'الهاتف')]")
                                            if phone_elements:
                                                phone = phone_elements[0].get_attribute("aria-label").replace("Phone: ", "").replace("الهاتف: ", "").strip()
                                                print(f"📞 Phone: {phone}")
                                            
                                            # Extract website - fast check
                                            website_elements = driver.find_elements(By.XPATH, "//a[contains(@data-item-id, 'authority')] | //a[contains(@aria-label, 'Website')] | //a[contains(@aria-label, 'الموقع الإلكتروني')]")
                                            if website_elements:
                                                website = website_elements[0].get_attribute("href")
                                                print(f"🌐 Website: {website}")
                                            
                                            # Save data
                                            writer.writerow([missing_name, phone, website])
                                            processed_restaurants.add(missing_name)
                                            print(f"✅ Data saved for: {missing_name}")
                                            extraction_success = True
                                            found = True
                                            
                                            # Go back to results view
                                            back_button = driver.find_element(By.XPATH, "//button[@aria-label='Back'] | //button[@aria-label='رجوع']")
                                            back_button.click()
                                            WebDriverWait(driver, 3).until(
                                                EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                                            )
                                        else:
                                            print(f"⚠️ Name mismatch. Expected: {missing_name}, Got: {details_name}")
                                            # Go back and try again
                                            driver.find_element(By.XPATH, "//button[@aria-label='Back'] | //button[@aria-label='رجوع']").click()
                                            WebDriverWait(driver, 3).until(
                                                EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
                                            )
                                            continue
                                    
                                    except Exception as e:
                                        if attempts % 3 == 0:
                                            print(f"⚠️ Attempt {attempts} failed: {str(e)[:50]}...")
                                        
                                        # Try to recover
                                        ensure_back_to_results()
                                        
                                if not extraction_success:
                                    print(f"⚠️ Failed to extract data for {missing_name}")
                                    failed_attempts.add(missing_name)
                                
                                break  # Stop looking for this restaurant
                        except:
                            continue
                    
                    if not found:
                        print(f"❌ Could not find {missing_name} in the results list")
                        failed_attempts.add(missing_name)
            
            # FINAL final report
            print(f"\n📊 FINAL Results for {city}:")
            print(f"✅ Successfully extracted {len(processed_restaurants)} restaurants")
            print(f"⚠️ Failed to extract {len(failed_attempts)} restaurants")
            print(f"📋 Total restaurants found: {total_restaurants_available}")
            print(f"💾 Data saved to: {filename}")
    
    except Exception as e:
        print(f"❌ Error processing city {city}: {e}")
        traceback.print_exc()
    
    finally:
        driver.quit()
        print(f"✅ Browser closed for {city}.")

print("🔔 Script completed!")
