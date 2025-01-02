import hashlib
import re
import time
from datetime import datetime

import requests
from croniter import croniter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from webdriver_manager.chrome import ChromeDriverManager

TOKEN_ID = "7645591135:AAHCheX22ciW2sXRDhVcKRX0D4qQrEDLPyo"
CHAT_ID = "@tweetcatcherhittiessss"

keywords = ["AI", "SOLana", "agent", "pump", "live", "swarm"]
required_number_of_keywords = 2

scroll_limit = 10

filter = "%20lang%3Aen%20-filter%3Alinks%20-filter%3Areplies&src=typed_query"
query = "https://x.com/search?f=live&q="
def load_proxies(file_path):
    with open(file_path, 'r') as file:
        proxies = file.readlines()
    return [proxy.strip() for proxy in proxies]

def load_auth_tokens(file_path):
    with open(file_path, 'r') as file:
        tokens = file.readlines()
    return [token.strip() for token in tokens]


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") # Run in headless mode (optional)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def inject_auth_token(driver, auth_token):
    driver.get("https://x.com")
    time.sleep(2)
    cookie = {
    "name": "auth_token",
    "value": auth_token,
    "domain": "x.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
}

    driver.add_cookie(cookie)
    driver.refresh()
    time.sleep(2)

def getSearchLink(keywords):
    converted_string = f"({'%20OR%20'.join(keywords)})"
    return query + converted_string + filter

def contains_required_keywords(tweet):
    count = 0
    for key in keywords:
        if(key.lower() in tweet.lower()):
            count = count +1
    return count,(count >= required_number_of_keywords)



def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN_ID}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Message sent to Telegram.")
    else:
        print("Failed to send message:", response.text)

def getAccurateTweet(driver,tweets):
    print("Fetched data length: " +str(len(tweets)))
    print("now sorting..")
    for tweet in tweets:
        author = tweet["author"]
        content = tweet["content"]
        count,containsTheRequiredKeyword = contains_required_keywords(content)
        if(containsTheRequiredKeyword):
            print(f"Author:: {author}\nTweet Content: {content.strip()}\n==========================")
            send_telegram_message(f"Author:: {author}\nTweet Content: {content.strip()}\n==========================")
        else:
            driver.get(author)
            time.sleep(3)
            try:
                bio_element = driver.find_element(By.XPATH, '//div[@data-testid="UserDescription"]').text
                count2, containsTheRequiredKeyword1 = contains_required_keywords(bio_element)
                if(count + count2 == required_number_of_keywords):
                    print(f"Author:: {author}\nTweet Content: {content.strip()}\n==========================")
                    send_telegram_message(
                        f"Author:: {author}\nTweet Content: {content.strip()}\n==========================")
            except:
                pass

def get_twitter(driver):
    try:
        url = getSearchLink(keywords)
        driver.get(url)
        print("the url: " +url)
        time.sleep(5)
        tweets = []
        tweet_hashes = set()  # To track unique tweets


        for _ in range(scroll_limit):
            # Find tweet elements
            tweet_elements = driver.find_elements(By.XPATH, '//article[@role="article"]')

            for tweet in tweet_elements:
                try:
                    content = tweet.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
                    user_link_elements = tweet.find_elements(By.XPATH, './/div[@data-testid="User-Name"]//a[@role="link"]')
                    userlink = ""
                    if user_link_elements:
                        user_link = user_link_elements[0].get_attribute(
                            'href')
                        userlink = user_link

                    tweet_hash = hashlib.md5(f"{content}".encode()).hexdigest()

                    if tweet_hash not in tweet_hashes:
                        tweets.append(
                            {
                                "author" : userlink,
                                'content': content
                            })
                        tweet_hashes.add(tweet_hash)
                except Exception as e:
                    continue


            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
        getAccurateTweet(driver,tweets)
        return
    except Exception as e:
        print(f"Error : {e}")
    return None

def monitor_bot():
    print("Starting")
    driver = setup_driver()
    tokens = load_auth_tokens('auth_tokens.txt')

    try:
        for auth_token in tokens:
            print(f"Using auth token: {auth_token}...")
            inject_auth_token(driver, auth_token)
            get_twitter(driver)

    except Exception as e:
        print(f"Error during monitoring with token : {e}")

        print("Rotating to next auth token...")
        time.sleep(1)


cron_expression = "* * * * *"
base_time = datetime.now()
cron = croniter(cron_expression, base_time)

while True:
    next_run = cron.get_next(datetime)
    now = datetime.now()

    sleep_duration = (next_run - now).total_seconds()

    if sleep_duration > 0:
        print(f"Next run scheduled for: {next_run}")
        time.sleep(sleep_duration)

    monitor_bot()
