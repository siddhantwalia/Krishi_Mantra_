from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json

chrome_options = Options()
chrome_options.add_argument("--head")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.myscheme.gov.in/search/category/Agriculture%2CRural%20%26%20Environment")
time.sleep(5)  # wait for JS to load

cards = driver.find_elements(By.CSS_SELECTOR, "div.p-4")
schemes = []

for i in range(len(cards)):
    # Re-fetch cards to avoid stale element reference
    cards = driver.find_elements(By.CSS_SELECTOR, "div.p-4")
    card = cards[i]

    try:
        title_tag = card.find_element(By.CSS_SELECTOR, "h2[id^='scheme-name'] a")
        title = title_tag.text
        link = title_tag.get_attribute("href")

        ministry_tag = card.find_elements(By.CSS_SELECTOR, "h2.mt-3")
        ministry = ministry_tag[0].text if ministry_tag else None

        desc_tag = card.find_elements(By.CSS_SELECTOR, "span[aria-label*='Brief description']")
        description = desc_tag[0].text if desc_tag else None

        # Go to scheme page
        driver.get(link)
        time.sleep(3)

        try:
            details = driver.find_element(By.CSS_SELECTOR, "div#details").text
            eligibility = driver.find_element(By.CSS_SELECTOR, "div#eligibility").text
            application_process = driver.find_element(By.CSS_SELECTOR, "div#application-process").text
            documents_required = driver.find_element(By.CSS_SELECTOR, "div#documents-required").text
        except:
            details = eligibility = application_process = documents_required = None

        schemes.append({
            "title": title,
            "link": link,
            "ministry": ministry,
            "description": description,
            "details": details,
            "eligibility": eligibility,
            "application_process": application_process,
            "documents_required": documents_required,
        })

        # Go back to main page
        driver.back()
        time.sleep(2)

    except Exception as e:
        print("Error:", e)
        continue


driver.quit()

# Save to JSON
with open("scheme.json", "w", encoding="utf-8") as f:
    json.dump(schemes, f, ensure_ascii=False, indent=4)

