import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Initializes the Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment to run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def dismiss_cookie_banner(driver):
    """Dismisses cookie consent banner if present."""
    try:
        # Try to find and click the accept/reject button
        cookie_selectors = [
            "#onetrust-accept-btn-handler",
            "#onetrust-reject-all-handler",
            ".onetrust-close-btn-handler",
            "button[aria-label='Close']"
        ]
        for selector in cookie_selectors:
            try:
                btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                btn.click()
                time.sleep(0.5)
                print("  Dismissed cookie banner.")
                return True
            except:
                continue
    except:
        pass
    return False

def js_click(driver, element):
    """Click element using JavaScript to bypass overlays."""
    driver.execute_script("arguments[0].click();", element)

def get_product_links(driver, category_url):
    """Extracts all product links from the category page."""
    print(f"Navigating to category page: {category_url}")
    driver.get(category_url)
    time.sleep(3)

    # Dismiss cookie banner if present
    dismiss_cookie_banner(driver)

    # Scroll down to load all lazy-loaded content
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Find all product links (descpage URLs)
    all_links = driver.find_elements(By.TAG_NAME, "a")
    product_links = set()

    for link in all_links:
        href = link.get_attribute('href') or ''
        if 'descpage' in href:
            # Normalize URL - remove query params and anchors for deduplication
            base_url = href.split('?')[0].split('#')[0]
            product_links.add(base_url)

    links = list(product_links)
    print(f"Found {len(links)} unique products.")
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
    time.sleep(2)  # Wait for page to fully load

    # Dismiss cookie banner first
    dismiss_cookie_banner(driver)

    try:
        # Get Product Title - improved selectors
        product_title = None
        title_selectors = [
            "h1.desc_top-head-brand",
            ".desc_top-head-brand",
            "h1",
            ".product-title",
            "[data-testid='product-title']"
        ]

        for selector in title_selectors:
            try:
                title_elem = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                title_text = title_elem.text.strip()
                if title_text:
                    product_title = clean_filename(title_text)
                    break
            except:
                continue

        # Fallback: extract from URL
        if not product_title:
            try:
                # Extract product name from URL like descpage-DHYD.html
                url_part = product_url.split('/')[-1].replace('.html', '').replace('descpage-', '')
                product_title = clean_filename(url_part)
            except:
                product_title = f"product_{int(time.time())}"

        if not product_title:
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
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.style_ordering-box-modal_btn"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", color_btn)
            time.sleep(0.5)
            js_click(driver, color_btn)
            time.sleep(1.5)
            thumb_selector = "button.color-drawer__item-button"
            layout_type = "drawer"
        except:
            try:
                # Method 2: All Colors Tab (e.g. Hydra Evolution)
                tab_btn = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#prod_colors"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab_btn)
                time.sleep(0.5)
                js_click(driver, tab_btn)
                time.sleep(1)
                thumb_selector = ".color-drawer__item"
                layout_type = "tab"
            except:
                print("  Could not find color selection mechanism.")
                # Fallback: just download main image
                try:
                    img_elem = driver.find_element(By.CSS_SELECTOR, "img.main_image")
                    img_url = img_elem.get_attribute("src")
                    if 'nw=' in img_url:
                        img_url = img_url.split('nw=')[0] + 'nw=800'
                    download_image(img_url, product_dir, f"{product_title}.jpg")
                except:
                    print("  Could not find main image.")
                return

        # Find all color options
        color_thumbnails = driver.find_elements(By.CSS_SELECTOR, thumb_selector)
        color_count = len(color_thumbnails)
        print(f"  Found {color_count} colors (Layout: {layout_type}).")

        # If no colors found, download the main image as fallback
        if color_count == 0:
            print("  No color options found, downloading main image...")
            try:
                img_elem = driver.find_element(By.CSS_SELECTOR, "img.main_image")
                img_url = img_elem.get_attribute("src")
                if 'nw=' in img_url:
                    img_url = img_url.split('nw=')[0] + 'nw=800'
                download_image(img_url, product_dir, f"{product_title}.jpg")
            except Exception as e:
                print(f"  Could not download main image: {e}")
            return

        for i in range(color_count):
            try:
                # Re-find elements
                thumbnails = driver.find_elements(By.CSS_SELECTOR, thumb_selector)
                if i >= len(thumbnails):
                    break

                thumb = thumbnails[i]

                # Scroll to element with offset to avoid header overlap
                driver.execute_script("""
                    arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});
                    window.scrollBy(0, -150);
                """, thumb)
                time.sleep(0.8)

                # Use JavaScript click to bypass overlay elements
                js_click(driver, thumb)
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

                # Get Main Image - try multiple selectors
                img_url = None
                main_img_selectors = [
                    "img.main_image",
                    "img.is-zoomable",
                    ".prod_view img",
                    "img.prod_view-img-main",
                    ".carousel__image"
                ]

                for selector in main_img_selectors:
                    try:
                        main_img = driver.find_element(By.CSS_SELECTOR, selector)
                        img_url = main_img.get_attribute("src")
                        if img_url and 'tacklewarehouse' in img_url:
                            break
                    except:
                        continue

                if img_url:
                    # Get higher resolution by changing nw parameter
                    if 'nw=' in img_url:
                        img_url = img_url.split('nw=')[0] + 'nw=800'

                    # Determine file extension from URL or default to jpg
                    if '.webp' in img_url.lower():
                        ext = '.webp'
                    elif '.png' in img_url.lower():
                        ext = '.png'
                    else:
                        ext = '.jpg'

                    filename = f"{product_title}-{color_name}{ext}"
                    download_image(img_url, product_dir, filename)
                else:
                    print(f"  Could not find main image for color {color_name}")
                
                # Re-open drawer if needed
                if layout_type == "drawer":
                    try:
                        reopen_btn = driver.find_element(By.CSS_SELECTOR, "button.style_ordering-box-modal_btn")
                        js_click(driver, reopen_btn)
                        time.sleep(1)
                    except:
                        pass

            except Exception as e:
                print(f"  Error processing color {i}: {e}")
                if layout_type == "drawer":
                    try:
                        reopen_btn = driver.find_element(By.CSS_SELECTOR, "button.style_ordering-box-modal_btn")
                        js_click(driver, reopen_btn)
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
