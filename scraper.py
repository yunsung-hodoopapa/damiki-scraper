import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Initializes the Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment to run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def get_product_links(driver, category_url):
    """Extracts all product links from the category page."""
    print(f"Navigating to category page: {category_url}")
    driver.get(category_url)
    
    # Wait for product links to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.cattable-wrap-cell-imgwrap-inner"))
    )
    
    elements = driver.find_elements(By.CSS_SELECTOR, "a.cattable-wrap-cell-imgwrap-inner")
    links = [elem.get_attribute('href') for elem in elements]
    print(f"Found {len(links)} products.")
    return links

def clean_filename(text):
    """Cleans text to be safe for filenames."""
    return "".join([c for c in text if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()

def download_image(url, folder, filename):
    """Downloads an image from a URL."""
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        print(f"  Skipping (already exists): {filename}")
        return

    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"  Downloaded: {filename}")
        else:
            print(f"  Failed to download {url}: Status {response.status_code}")
    except Exception as e:
        print(f"  Error downloading {url}: {e}")

def scrape_product(driver, product_url):
    """Scrapes a single product page for images."""
    print(f"Scraping product: {product_url}")
    driver.get(product_url)
    
    try:
        # Get Product Title
        try:
            title_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            product_title = clean_filename(title_elem.text)
        except:
            # Fallback for title
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, ".desc_top-head-brand")
                product_title = clean_filename(title_elem.text)
            except:
                print("  Could not find product title.")
                return

        print(f"Product: {product_title}")
        
        # Create directory for product
        product_dir = os.path.join("damiki_images", product_title)
        if not os.path.exists(product_dir):
            os.makedirs(product_dir)

        # Determine Layout and Open Color Section
        thumb_selector = ""
        layout_type = ""
        
        try:
            # Method 1: Drawer Button (e.g. Mega Miki II)
            color_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.style_ordering-box-modal_btn"))
            )
            color_btn.click()
            time.sleep(1)
            thumb_selector = "button.color-drawer__item-button"
            layout_type = "drawer"
        except:
            try:
                # Method 2: All Colors Tab (e.g. Hydra Evolution)
                tab_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#prod_colors")) # ID for "All Colors" tab
                )
                # Scroll to it
                driver.execute_script("arguments[0].scrollIntoView(true);", tab_btn)
                tab_btn.click()
                time.sleep(1)
                thumb_selector = ".color-drawer__item" # Items in the list
                layout_type = "tab"
            except:
                print("  Could not find color selection mechanism.")
                # Fallback: just download main image
                try:
                    img_elem = driver.find_element(By.CSS_SELECTOR, "img.prod_view-img-main")
                    img_url = img_elem.get_attribute("src")
                    download_image(img_url, product_dir, f"{product_title}.jpg")
                except:
                    print("  Could not find main image.")
                return

        # Find all color options
        color_thumbnails = driver.find_elements(By.CSS_SELECTOR, thumb_selector)
        color_count = len(color_thumbnails)
        print(f"  Found {color_count} colors (Layout: {layout_type}).")

        for i in range(color_count):
            try:
                # Re-find elements
                thumbnails = driver.find_elements(By.CSS_SELECTOR, thumb_selector)
                if i >= len(thumbnails):
                    break
                
                thumb = thumbnails[i]
                
                # Scroll to thumbnail
                driver.execute_script("arguments[0].scrollIntoView(true);", thumb)
                time.sleep(0.5)
                
                # Click the color
                # For tab layout, the item itself might not be clickable, maybe an image inside?
                # But usually the container works.
                thumb.click()
                time.sleep(1.5) 
                
                # Get Color Name
                color_name = f"color_{i+1}" # Default
                try:
                    if layout_type == "drawer":
                        # Try button text first
                        try:
                            color_name_elem = driver.find_element(By.CSS_SELECTOR, ".style_ordering-box-modal_btn .d-block:first-of-type")
                            color_name = clean_filename(color_name_elem.text)
                        except:
                            # Try aria-label or title of the thumbnail we just clicked
                            color_name = clean_filename(thumb.get_attribute("title") or thumb.get_attribute("aria-label") or thumb.text or f"color_{i+1}")
                    else:
                        # Tab layout
                        try:
                            name_elem = thumb.find_element(By.CSS_SELECTOR, ".color-drawer__item-name")
                            color_name = clean_filename(name_elem.text)
                        except:
                            color_name = clean_filename(thumb.text or f"color_{i+1}")
                except Exception as e:
                    print(f"  Warning: Could not extract color name ({e}). Using default.")

                # Get Main Image
                try:
                    main_img = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "img.prod_view-img-main"))
                    )
                    img_url = main_img.get_attribute("src")
                    
                    # Download
                    filename = f"{product_title}-{color_name}.jpg"
                    download_image(img_url, product_dir, filename)
                except Exception as e:
                    print(f"  Error finding main image: {e}")
                    # Try fallback selector if any
                    try:
                         # Sometimes the class might be different or it's inside a container
                         container = driver.find_element(By.CSS_SELECTOR, ".prod_view-img-wrap")
                         img_url = container.find_element(By.TAG_NAME, "img").get_attribute("src")
                         filename = f"{product_title}-{color_name}.jpg"
                         download_image(img_url, product_dir, filename)
                    except:
                        pass
                
                # Re-open drawer if needed
                if layout_type == "drawer":
                     try:
                        # Check if drawer is closed (button exists and is visible)
                        driver.find_element(By.CSS_SELECTOR, "button.style_ordering-box-modal_btn").click()
                        time.sleep(1)
                     except:
                        pass
                
            except Exception as e:
                print(f"  Error processing color {i}: {e}")
                if layout_type == "drawer":
                    try:
                        driver.find_element(By.CSS_SELECTOR, "button.style_ordering-box-modal_btn").click()
                        time.sleep(1)
                    except:
                        pass

    except Exception as e:
        print(f"Error scraping product {product_url}: {e}")

def main():
    category_url = "https://www.tacklewarehouse.com/catpage-DAM.html"
    driver = setup_driver()
    try:
        print("Starting scraper...")
        links = get_product_links(driver, category_url)
        
        # Limit to first 3 for testing if needed, or run all. 
        # User wants the full program.
        for link in links:
            scrape_product(driver, link)
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
