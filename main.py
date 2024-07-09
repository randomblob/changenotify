import os
from requests import get
import telebot
import csv
from urllib.parse import urlparse
import subprocess
from fake_headers import Headers
from bs4 import BeautifulSoup
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BASE_URL = os.environ.get("BASE_URL")
DEBUG = os.environ.get("DEBUG")

bot = telebot.TeleBot(BOT_TOKEN)

is_changed = False
jeeUpdate = False
maitUpdates = True
ipuUpdates = True


def init():
    global is_changed
    # Create urls.csv if not exists
    if not os.path.isfile("urls.csv"):
        urls_file = open("urls.csv", "w", newline="\n")
        urls_file.close()
        is_changed = True
    # Create files directory if not exists
    if not os.path.isdir("files"):
        os.mkdir("files")


def get_git_revisions_hash():
    hashes = []
    hashes.append(subprocess.check_output(["git", "rev-parse", "HEAD"]))
    hashes.append(subprocess.check_output(["git", "rev-parse", "HEAD^"]))
    hashes = [hash_.decode() for hash_ in hashes]
    return hashes


def send_msg(message):
    bot.send_message(CHAT_ID, message, disable_web_page_preview=True)


def send_normal_msg(message):
    bot.send_message(CHAT_ID, message)


def send_silent_msg(message):
    bot.send_message(
        CHAT_ID, message, disable_web_page_preview=True, disable_notification=True
    )


def get_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203"
    }
    response = get(url, headers=headers, timeout=5)
    html_content = response.text
    html_content = save_and_read(html_content)
    return reformat(html_content)


def get_old_content(url):
    # check if old content exists other wise return that the old content doesn't exist
    url_file_name = urlparse(url).netloc + ".html"
    if not os.path.isfile(url_file_name):
        return None
    old_file = open(url_file_name, "r", newline="\n")
    old_file_content = old_file.read()
    old_file.close()
    return old_file_content


def save_and_read(file_content):
    temp_file = open("temp.html", "w", newline="\n")
    temp_file.write(file_content)
    temp_file.close()
    temp_file = open("temp.html", "r", newline="\n")
    content = temp_file.read()
    temp_file.close()
    os.remove("temp.html")
    return content


def reformat(html_content):
    # Remove unecessary lines
    lines = html_content.split("\n")
    blacklisted_keywords = (
        "Dynamic page generated in",
        "Cached page generated by WP-Super-Cache on",
        "Drupal.settings",
        "form_build_id",
        "csrf-token",
        "view-dom-id",
        "views_dom_id",
    )
    lines = [line for line in lines if not any(x in line for x in blacklisted_keywords)]
    reformatted_html_content = "\n".join(lines)
    return reformatted_html_content


def compare_website(url):
    global is_changed
    # check if change detected
    try:
        old_html_content = get_old_content(url)
        new_html_content = get_content(url)
    except:
        return
    if old_html_content == None:
        # Website Page does not exist
        is_changed = True
        send_msg(f"For website {url} the original file does not exist")

    elif old_html_content != new_html_content:
        is_changed = True
        send_msg(f"{url} was modified.")

    # write the content
    url_file_name = urlparse(url).netloc + ".html"
    file_object = open(url_file_name, "w", newline="\n")
    file_object.write(new_html_content)
    file_object.close()


def commit_changes():
    # push changes
    os.system("git add .")
    os.system("git commit -m 'Update Website'")
    # send a message with the changes url if any change
    hashes = get_git_revisions_hash()
    hash1 = hashes[0][:7]
    hash2 = hashes[1][:7]
    send_silent_msg(f"Update url: {BASE_URL}/compare/{hash2}..{hash1}")


# JEE Only
def fetch_latest_notices():
    url = r"https://jeemain.nta.ac.in/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203"
    }
    response = get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(response.content, "html.parser")
    notices = soup.find_all("div", class_="news-eve-scroll pr-2")
    latest_notices = []
    for notice in notices:
        li_elements = notice.find_all("li")
        for li in li_elements:
            title = (
                li.text.strip().replace("\n", "").replace("\t", "").replace("\r", "")
            )
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
    with open("jee.txt", "w") as file:
        for title, href in notices:
            file.write(f"{title}\n")


# Function to check for changes in notices
def check_for_changes(previous_notices):
    global is_changed
    latest_notices = fetch_latest_notices()
    new_notices = [
        (title, href) for title, href in latest_notices if title not in previous_notices
    ]
    if new_notices:
        is_changed = True
        msg = "New Notices added or changed:\n"
        for title, href in new_notices:
            encoded_href = urllib.parse.quote(href, safe=":\\/")
            msg += f"{title} - {encoded_href}\n"
        send_msg(msg)
    return latest_notices


# MAIT
def fetch_mait_notices():
    url = r"https://mait.ac.in/index.php/noticesboard/all"
    response = get(url, headers=Headers().generate())
    soup = BeautifulSoup(response.content, "html.parser")
    notices = soup.find_all("h3", {"class": "ma-title"})
    latest_notices = []
    for notice in notices:
        title = notice.find_all("a")[0].text.strip()
        url = r"https://mait.ac.in" + notice.find_all("a")[0]["href"]
        url = urllib.parse.quote(url, safe=":\\/")
        latest_notices.append((title, url))
    return latest_notices


def read_mait_notices_from_file():
    try:
        file = open("files/mait.txt", "r")
    except FileNotFoundError:
        return []
    notices = [line.strip() for line in file.readlines()]
    file.close()
    return notices


def write_mait_notices_to_file(notices):
    file = open("files/mait.txt", "w")
    for title, url in notices:
        file.write(f"{title}\n")
    file.close()


def check_mait_updates():
    global is_changed
    updated = False
    latest_notices = fetch_mait_notices()
    if not latest_notices:
        return
    old_notices = read_mait_notices_from_file()
    # Compare only last 5 notices
    latest_notices = latest_notices[:5]
    old_notices = old_notices[:5]
    for title, url in latest_notices:
        if title not in old_notices:
            send_normal_msg(f"New Notice on MAIT: {title} - {url}")
            is_changed = True
            updated = True
    if updated:
        write_mait_notices_to_file(latest_notices)


# IPU Updates
def fetch_ipu_notices(notices_url, base_url):
    url = notices_url
    try:
        response = get(url)
    except:
        return []
    soup = BeautifulSoup(response.content, "html.parser")
    all_notices = soup.select("tr td a")
    latest_notices = []
    for notice in all_notices[:100]:
        title = notice.text.strip().replace("\n", " ").replace("\t", "").replace("\r", "")
        url = base_url + notice["href"]
        url = urllib.parse.quote(url, safe=":\\/")
        latest_notices.append((title, url))
    return latest_notices


def read_ipu_notices_from_file(file_path):
    try:
        file = open(file_path, "r")
    except FileNotFoundError:
        return []
    notices = [line.strip() for line in file.readlines()]
    file.close()
    return notices


def write_ipu_notices_to_file(notices, file_path):
    file = open(file_path, "w")
    for title, url in notices:
        file.write(f"{title}\n")
    file.close()


def check_ipu_updates(notices_url, base_url, file_path):
    global is_changed
    updated = False
    latest_notices = fetch_ipu_notices(notices_url, base_url)
    if not latest_notices:
        return
    old_notices = read_ipu_notices_from_file(file_path)
    # Compare last 50 notices
    latest_notices = latest_notices[:50]
    # old_notices = old_notices[:100]
    # Only update for at most 5 notices
    updates = 0
    for title, url in latest_notices:
        if updates < 5 and title not in old_notices:
            updates += 1
            send_normal_msg(f"New Notice on IPU: {title} - {url}")
            is_changed = True
            updated = True
    if updated:
        write_ipu_notices_to_file(latest_notices, file_path)


def read_url_file():
    try:
        with open("urls.csv", "r") as file:
            return [url[0] for url in csv.reader(file)]
    except FileNotFoundError:
        return []


def write_url_file(urls):
    with open("urls.csv", "w", newline="\n") as file:
        writer = csv.writer(file)
        for url in urls:
            writer.writerow([url])


def current_websites():
    urls = read_url_file()
    # Custom Implementations
    if maitUpdates:
        urls.append("https://mait.ac.in/")
    if ipuUpdates:
        urls.append("http://ipu.ac.in/")
        urls.append("http://ggsipu.ac.in/ExamResults/ExamResultsmain.htm")
    if jeeUpdate:
        urls.append("https://jeemain.nta.ac.in/")
    send_msg(f"Current URLs: {' ,'.join(urls)}")


if __name__ == "__main__":
    init()
    urls_file = open("urls.csv", "r")
    urls = [url[0] for url in csv.reader(urls_file)]
    urls_file.close()
    new_updates = bot.get_updates(allowed_updates=["messages"], long_polling_timeout=1)
    last_update_id = None
    try:
        for update in new_updates:
            last_update_id = update.update_id
            if update.message.chat.id == int(CHAT_ID):
                message = update.message.text.split()
                if len(message) == 1 and message[0] == "current":
                    current_websites()
                    continue
                if len(message) != 2 or message[0] not in ["delete", "add"]:
                    send_msg(
                        "Invalid Command. Send in the format: delete <url> or add <url> or current."
                    )
                    continue
                operation, url = message[0], message[1]
                if operation == "delete":
                    urls = read_url_file()
                    if url in urls:
                        urls.remove(url)
                        write_url_file(urls)
                        is_changed = True
                        send_msg(f"Deleted {url}")
                    else:
                        send_msg(f"{url} not found in the list.")

                elif operation == "add":
                    urls = read_url_file()
                    if url not in urls:
                        urls.append(url)
                        write_url_file(urls)
                        is_changed = True
                        send_msg(f"Added {url}")
                    else:
                        send_msg(f"{url} already exists in the list.")
                send_msg(f"Current URLs: {' ,'.join(read_url_file())}")
    except Exception as e:
        send_msg(f"Error: {e}")

    if last_update_id:
        bot.get_updates(offset=last_update_id + 1, long_polling_timeout=0)

    # try:
    #     check_for_changes(read_notices_from_file())
    #     write_notices_to_file(fetch_latest_notices())
    # except:
    #     pass
    for url in urls:
        compare_website(url)
    if maitUpdates:
        check_mait_updates()
    if ipuUpdates:
        check_ipu_updates(r"http://ggsipu.ac.in/ExamResults/ExamResultsmain.htm", r"http://ggsipu.ac.in/ExamResults/", "files/ipuexams.txt")
        # check_ipu_updates(r"http://www.ipu.ac.in/notices.php", r"http://www.ipu.ac.in", "files/ipu.txt")
    if DEBUG is None and (is_changed or jeeUpdate):
        commit_changes()
