import subprocess
import sys
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install('selenium')
install('pandas')
install('lxml')
install('xlsxwriter')
install('openpyxl')
install('xlrd')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

from bs4 import BeautifulSoup
import time
from datetime import datetime
from datetime import date, timedelta
import os
import re
import pandas as pd
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Find the E-Mail credentials to send notifications later
path_to_file_credentials = os.path.dirname(os.path.realpath(__file__))
path_to_file_credentials = path_to_file_credentials.replace('Python', 'Excel')
path_to_file_credentials = os.path.join(path_to_file_credentials, "Zugangsdaten.xlsx")
file_credentials = pd.ExcelFile(path_to_file_credentials)
file_credentials = file_credentials.parse('Tabelle1')
email = file_credentials['e-mail']
email = str(email[0])
password = file_credentials['python_app_password']
password = str(password[0])

# Define function to get last file from the game results output folder
def get_last_file_alphabetically(folder_path):
    files = os.listdir(folder_path)
    files.sort()
    return files[-1]

# Find last date results where downloaded
path = os.path.dirname(os.path.realpath(__file__))
folder_path = os.path.join(path, "outputs", "game_results_not_refined")
last_file = get_last_file_alphabetically(folder_path)
last_date_str = last_file.split('.') [0]
last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
last_date = last_date.date()
today = date.today()

# Function delete forbidden values
def delete_forbidden_and_next_four(lst, forbidden_values):
    i = 0
    while i < len(lst):
        if lst[i] in forbidden_values:
            # Check if 3rd and 4th element after are empty
            if i < len(lst) - 5 and lst[i+3] == lst[i+4] == '':
                # Delete the forbidden value and the next four elements
                del lst[i:i+5]
            else:
                # Delete the forbidden value and the next two elements
                del lst[i:i+3]
        else:
            i += 1
    return lst

# Define forbidden values
forbidden_values = ['Postp.', 'Canc.', 'AAW']

# Define function to add all times to forbidden values
def add_times_to_forbidden(lst, forbidden_values):
    time_pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
    for value in lst:
        if isinstance(value, str) and time_pattern.match(value):
            forbidden_values.append(value)
    return forbidden_values

# Define function to convert all numbers saved as text in data into numbers
def convert_numbers(lst):
    for i in range(len(lst)):
        if isinstance(lst[i], str) and lst[i].isnumeric():
            lst[i] = int(lst[i])
    return lst

# Define function to split the long vector into a data frame
def split_vector(vector, break_points):
    # Initialize an empty DataFrame
    df = pd.DataFrame()

    # Initialize the start index
    start = 0

    # Iterate over the break points
    for i in break_points:
        # Create a new row from the vector slice and append it to the DataFrame
        df = df._append(pd.Series(vector[start:i+1]), ignore_index=True)
        # Update the start index
        start = i + 1

    # Append the last slice of the vector if there are any elements left
    if start < len(vector):
        df = df._append(pd.Series(vector[start:]), ignore_index=True)

    return df

# Define function to find the break points
def find_break_points(lst):
    break_points = []
    for i in range(1, len(lst)-4):
        if (isinstance(lst[i-1], (int, float)) or lst[i-1] == '') and all(isinstance(x, str) and x != '' for x in lst[i:i+5]):
            break_points.append(i-1)
    return break_points

# Define Function to send E-Mail if it worked
def send_email(subject, body):
    body = str(body)
    msg = MIMEText(body, _charset='utf-8')
    msg['From'] = email
    msg['To'] = 'loebus.l@gmail.com'
    msg['Subject'] = subject

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(email, password)
        smtp_server.sendmail(email, 'loebus.l@gmail.com', msg.as_string())
    
# Set up the Chrome options
options = Options()
options.headless = True

# Create a new instance of the Chrome driver
driver = webdriver.Chrome(options=options)

#Initialize start_date
if last_date == today - timedelta(days=1):
    start_date = last_date
else:
    start_date = last_date + timedelta(days=1)

while start_date < today:
    # Go to the website
    date_games = start_date.strftime("%Y-%m-%d")
    url = date_games + '/'
    url = 'https://www.livescore.com/en/football/' + url
    driver.get(url)

    data = []  # Initialize the list to store data

    # Wait for the JavaScript to load
    driver.implicitly_wait(10)

    # Scroll through the website
    for i in range(0, 300000, 200): 
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(0.25)  # Pause time to reload
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

    # Find all div elements with a class attribute that is in the list of classes
        divs = soup.select('div.Ef, div.Gf, div.sp, div.xp, div.yp, span.Gt')

    # Extract the data from the div elements and add it to the list
        for div in divs:
            data.append(div.text)

    time.sleep(0.5)

    # Add times to forbidden values
    forbidden_values = add_times_to_forbidden(data, forbidden_values)
    forbidden_values = list(set(forbidden_values))

    # Delete Faulty Games
    data = delete_forbidden_and_next_four(data, forbidden_values)

    # Convert numbers in data
    data = convert_numbers(data)

    # Find the break points in the data
    break_points = find_break_points(data)

    # Split the vector with the break points
    df = split_vector(data, break_points)

    df = df.drop_duplicates() # delete all the duplicate rows

    df = df[pd.to_numeric(df.iloc[:, 5], errors='coerce').notnull()] # remove all rows where 6th element is not numeric, as these are faulty leagues

    date_games_path = date_games + '.xlsx'
    df.to_excel(os.path.join(folder_path, date_games_path), index=False, header=True)

    # Send E-Mail about status of that day
    error_text = 'Data Frame for ' + date_games + ' was empty. No data added for this day.'
    success_text = 'Day ' + date_games + ' has been added to the unrefined data base.'

    if df.empty:
        send_email('Error in Match Updates', error_text)
    else:
        send_email('Successful Match Update', success_text)

    start_date += timedelta(days=1)

# Close the browser window
driver.quit()
