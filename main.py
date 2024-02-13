import os
from requests import get
import telebot
import csv
from urllib.parse import urlparse
import subprocess
from fake_headers import Headers
from bs4 import BeautifulSoup
import urllib.parse

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
BASE_URL = os.environ.get('BASE_URL')
bot = telebot.TeleBot(BOT_TOKEN)

is_changed = False


def get_git_revisions_hash():
    hashes = []
    hashes.append(subprocess.check_output(['git', 'rev-parse', 'HEAD']))
    hashes.append(subprocess.check_output(['git', 'rev-parse', 'HEAD^']))
    hashes = [hash_.decode() for hash_ in hashes]
    return hashes


def send_msg(message):
    bot.send_message(CHAT_ID, message, disable_web_page_preview=True)


def get_content(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203'}
    response = get(url, headers=headers, timeout=5)
    html_content = response.text
    html_content = save_and_read(html_content)
    return reformat(html_content)


def get_old_content(url):
    # check if old content exists other wise return that the old content doesn't exist
    url_file_name = urlparse(url).netloc + ".html"
    if not os.path.isfile(url_file_name):
        return 404
    old_file = open(url_file_name, "r", newline='\n')
    old_file_content = old_file.read()
    old_file.close()
    return old_file_content


def save_and_read(file_content):
    temp_file = open('temp.html', 'w', newline='\n')
    temp_file.write(file_content)
    temp_file.close()
    temp_file = open('temp.html', 'r', newline='\n')
    content = temp_file.read()
    temp_file.close()
    os.remove('temp.html')
    return content


def reformat(html_content):
    # Remove unecessary lines
    lines = html_content.split('\n')
    blacklisted_keywords = ('Dynamic page generated in', 'Cached page generated by WP-Super-Cache on', 'Drupal.settings', 'form_build_id', 'csrf-token', 'view-dom-id', 'views_dom_id')
    lines = [line for line in lines if not any(x in line for x in blacklisted_keywords)]
    reformatted_html_content = '\n'.join(lines)
    return reformatted_html_content


def compare_website(url):
    global is_changed
    # check if change detected
    try:
        old_html_content = get_old_content(url)
        new_html_content = get_content(url)
    except:
        return
    if old_html_content == 404:
        # Website Page does not exist
        is_changed = True
        send_msg(f"For website {url} the original file does not exist")

    elif old_html_content != new_html_content:
        is_changed = True
        send_msg(f"{url} was modified.")
    
    # write the content
    url_file_name = urlparse(url).netloc + ".html"
    file_object = open(url_file_name, "w", newline='\n')
    file_object.write(new_html_content)
    file_object.close()


def push_changes():
    # push changes
    os.system("git add .")
    os.system("git commit -m 'Update Website'")
    # send a message with the changes url if any change
    hashes = get_git_revisions_hash()
    hash1 = hashes[0][:7]
    hash2 = hashes[1][:7]
    send_msg(f"Update url: {BASE_URL}/compare/{hash2}..{hash1}")

# JEE Only
jeeUpdate = False
def fetch_latest_notices():
    url = r"https://jeemain.nta.ac.in/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203'}
    response = get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(response.content, "html.parser")
    notices = soup.find_all("div", class_="news-eve-scroll pr-2")
    latest_notices = []
    for notice in notices:
        li_elements = notice.find_all("li")
        for li in li_elements:
            title = li.text.strip().replace("\n", "").replace("\t", "").replace("\r", "")
            try:
                href = li.find("a")["href"]
                latest_notices.append((title, href))
            except:
                latest_notices.append((title, ""))
                
    return latest_notices

def read_notices_from_file():
    try:
        with open("jee.txt", "r") as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        return []

def write_notices_to_file(notices):
    global jeeUpdate
    with open("jee.txt", "w") as file:
        for title, href in notices:
            file.write(f"{title}\n")

# Function to check for changes in notices
def check_for_changes(previous_notices):
    latest_notices = fetch_latest_notices()
    new_notices = [(title, href) for title, href in latest_notices if title not in previous_notices]
    if new_notices:
        jeeUpdate = True
        msg = "New Notices added or changed:\n"
        for title, href in new_notices:
            encoded_href = urllib.parse.quote(href, safe=':\\/')
            msg += f"{title} - {encoded_href}\n"
        send_msg(msg)
    return latest_notices

# try:
check_for_changes(read_notices_from_file())
write_notices_to_file(fetch_latest_notices())
# except:
#     pass


# Create a csv file if not exists for the urls
try:
    urls_file = open("urls.csv", "r")
    urls = [url[0] for url in csv.reader(urls_file)]
    urls_file.close()
except:
    urls_file = open("urls.csv", "w", newline='\n')
    urls = []
    urls_file.close()

for url in urls:
    compare_website(url)
if is_changed or jeeUpdate:
    push_changes()