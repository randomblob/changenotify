import requests
import csv
def add_url(url):
    # check if valid
    try:
        print(f"Recieved status code: {requests.get(url)} and adding it to the list of urls")
        # URL is valid, save it
        urls_file = open("urls.csv", "a")
        csv.writer(urls_file).writerow([url])
        print("Added to the list")

    except Exception as Error:
        print(f"Probably Invalid Url.\nRecieved the following error:\n{Error}")

while True:
    url = input("Enter Url: ")
    add_url(url)