import os
import requests
import telebot
import csv
from urllib.parse import urlparse
import subprocess

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
    bot.send_message(CHAT_ID, message)


def get_content(url):
    try:
        html_content = requests.get(url=url).text
        return html_content
    except Exception as Error:
        return f"While downlading content from {url} the following exception occured \n{Error}"


def get_old_content(url):
    # check if old content exists other wise return that the old content doesn't exist
    url_file_name = urlparse(url).netloc + ".html"
    if not os.path.isfile(url_file_name):
        return "404"
    old_file = open(url_file_name, "r")
    old_file_content = old_file.read()
    old_file.close()
    return old_file_content


def compare_website(url):
    global is_changed
    # check if change detected
    old_html_content = get_old_content(url)
    new_html_content = get_content(url).replace("\r\n", "\n").replace("\r", "\n")

    if old_html_content == "404":
        # Website Page does not exist
        is_changed = True
        send_msg(f"For website {url} the original file does not exist")
    elif  old_html_content != "Error" and "the following exception occured" in new_html_content:
        # Some error occured
        # Send the error message
        is_changed = True
        send_msg(new_html_content)
        new_html_content = "Error"
    elif "Error" in old_html_content and "the following exception occured" not in new_html_content:
        # Error got fixed
        is_changed = True
        send_msg(f"{url} Error got fixed")
    elif "Error" in old_html_content and "the following exception occured" in new_html_content:
        # Error did not get fixed
        new_html_content = "Error"
    elif old_html_content != new_html_content:
        # Website change detected
        is_changed = True
        send_msg(f"Some change was detected on {url}")
    
    # write the content
    url_file_name = urlparse(url).netloc + ".html"
    file_object = open(url_file_name, "w", newline='\n')
    file_object.write(new_html_content)
    file_object.close()


def push_changes():
    # push changes
    # Config git
    os.system("git config --local user.name $USERNAME")
    os.system("git config --local user.email $EMAIL")
    os.system("git add .")
    os.system("git commit -m 'Update Website'")
    # send a message with the changes url if any change
    hashes = get_git_revisions_hash()
    hash1 = hashes[0][:7]
    hash2 = hashes[1][:7]
    send_msg(f"Update url: {BASE_URL}/compare/{hash2}..{hash1}")


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
if is_changed:
    push_changes()