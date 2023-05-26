from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
import win32api, win32con
import time
import re

# To be able to conveniently use .text even if driver.find_elements returns None.
class NullDriver:
    text = ""

def get_url(keyword, location = None, start = None):
    url = 'https://' + domain + '/jobs?q={}'.format(keyword)
    if location is not None:
        url += '&l={}'.format(location)
    if start is not None:
        url += '&start={}'.format(start)
    url += '&sort=date'
    return url

def try_find_element(driver, by, value):
    results = driver.find_elements(by, value)
    if len(results) > 0:
        return results[0]
    else:
        return NullDriver

# Sometimes, we get Cloudflare CAPTCHA when opening the page. To automate the verification process,
# we perform a click at the screen position where the box appears. Fortunately, bypassing Cloudflare CAPTCHA seems to be this simple.
# By default, it is deactivated since it saves us a few seconds.
# The coordinates are customized for my screen, so they may need to be changed.
def click(x,y):
    win32api.SetCursorPos((x,y))
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN,x,y,0,0)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP,x,y,0,0)

autoclicker_enabled = False
autoclicker_x = 534
autoclicker_y = 405

domain = 'es.indeed.com'

# We select some job position, as well as the location if desired.
position = "profesor"
location = None

# File name where we will store the scraped data:
file_name_no_extension = 'ofertas_' + position
if location is not None:
    file_name_no_extension += '_' + location
file_name = file_name_no_extension + '.csv'

# Write the header of the CSV file
with open(file_name, "w", encoding='UTF8', newline='') as f:
    f.write('"ID","Código interno","Puesto","Empresa","Fecha","Ubicación","Salario","Tipo de trabajo","Turno","Resumen","Atributos"\n')

# The range of pages to scrape. We don't use 'range()' because we want to be able to manipulate the index
i = 0
until = 2

# Each offer has a unique id
id = 0

while i <= until:
    print("Index: " + str(i))
    # Obtain the URL of the page to scrape
    url = get_url(position, location, start=i*10)

    # Open the browser
    driver = webdriver.Chrome(executable_path="path")
    driver.maximize_window()

    # Wait for the page to load
    driver.implicitly_wait(5)

    # Open the URL
    driver.get(url)

    # Sometimes, we get Cloudflare CAPTCHA when opening the page. To automate the verification process,
    if autoclicker_enabled:
        time.sleep(4.5)
        click(autoclicker_x, autoclicker_y)
 
    # Obtain 'job_seen_beacon' elements, which contain the data of the offers
    offers = driver.find_elements(By.CLASS_NAME, 'job_seen_beacon')

    # It might happen that the page has not loaded yet, so we try again
    if len(offers) == 0:
        print("Repeating index: " + str(i))
        continue 

    # Wait time set to 0. This way we'll not have to wait for the page to load when searching for a non-existent element
    driver.implicitly_wait(0)

    for offer in offers:
        try:
            # Obtain data from the offer
            salary = ""
            job_type = ""
            shift = ""
            attributes = ""

            job_title_a = try_find_element(offer, By.CLASS_NAME, 'jcs-JobTitle')
            code = job_title_a.get_attribute('id') # Internal code of the offer, not to be confused with the CSV's ID
            job_title = job_title_a.text.replace('"', '""') # Escape double quotes
            company = try_find_element(offer, By.CLASS_NAME, 'companyName').text.replace('"', '""')
            location = try_find_element(offer, By.CLASS_NAME, 'companyLocation').text.replace('"', '""')
            
            # These attributes are not always present
            attribute_snippets = offer.find_elements(By.CLASS_NAME, 'attribute_snippet')
            for attribute_snippet in attribute_snippets:
                svg = try_find_element(attribute_snippet, By.TAG_NAME, 'svg') # svg is the icon of the attribute, which helps us identify it
                if svg != NullDriver and svg.get_attribute('aria-label') == 'Salary':
                    salary = attribute_snippet.text.replace('"', '""')
                elif svg != NullDriver and svg.get_attribute('aria-label') == 'Job type':
                    job_type = attribute_snippet.text.replace('"', '""')
                elif svg != NullDriver and svg.get_attribute('aria-label') == 'Shift':
                    shift = attribute_snippet.text.replace('"', '""')
                else:
                    # Some attributes are not identified by an icon, so we just add them to 'attributes'
                    attributes += (attribute_snippet.text.replace('"', '""') + ";")
                    
            summary = try_find_element(offer, By.CLASS_NAME, 'job-snippet').text
            date = try_find_element(offer, By.CLASS_NAME, 'date').text

            # Prepare the text to write in the CSV
            text = '"' + str(id) + '","' + code + '","' + job_title + '","' + company + '","' + date + '","' + location + '","' + salary + '","' + job_type + '","' + shift + '","' + summary + '","' + attributes + '"'
            text = text.replace("\n", "\\n")

            id += 1

            # Write the text in the CSV
            try:
                with open(file_name, "a", encoding='UTF8', newline='') as f:
                    f.write(text + "\n")
                print(text)
            except IndexError:
                print("Error at index: " + str(i) + ", text: " + text)
                pass

        except StaleElementReferenceException:
            continue
    
    i += 1
    # Close the browser in each iteration to avoid CAPTCHA appearing (or to get verified if it appears)
    driver.quit()