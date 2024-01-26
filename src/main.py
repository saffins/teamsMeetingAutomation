import os.path
from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urlsplit, unquote
import time
from concurrent.futures import ThreadPoolExecutor
from logger import logger, WRK_DIR


def start_chrome():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-infobars")
    options.add_argument("start-maximized")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("prefs", {"profile.default_content_setting_values.media_stream_mic": 1,
                                              "profile.default_content_setting_values.media_stream_camera": 1,
                                              "profile.default_content_setting_values.notifications": 1
                                              })
    return webdriver.Chrome(options=options)


def get_direct_join_url(url):
    logger.debug(f"Original meeting url is {url}")
    base_url = "https://teams.microsoft.com/v2/?meetingjoin=true#"

    fragment = urlsplit(url).fragment
    if not fragment:
        fragment = urlsplit(unquote(url)).fragment

    main_url = base_url + fragment
    logger.debug(f"New meeting url generated is {main_url}")
    return main_url


def join_meeting(username, url):
    logger.debug(f"starting chrome driver for user -- {username}")
    driver = start_chrome()
    logger.debug(f"Chrome driver is running for user -- {username}")

    driver.get(url)

    wait_time_main_page = 5  # in mins
    counter = 0
    logger.debug(f"Waiting for meeting url to load for user -- {username}")
    while counter < (60 * wait_time_main_page):
        if driver.find_elements(By.XPATH, "//input[@placeholder='Type your name']"):
            break
        time.sleep(1)

    logger.debug(f"Meeting page is loaded for user -- {username}")
    driver.find_element(By.XPATH, "//input[@placeholder='Type your name']").send_keys(username)
    logger.debug(f"Entered Guest username for -- {username}")

    for div in driver.find_elements(By.CLASS_NAME, "fui-Flex.___1gzszts.f22iagw"):
        if div.find_elements(By.ID, "calling-prejoin-camera-state-id"):
            logger.debug(f"Disabling Mic and camera befor meeting join for user -- {username}")
            for checkbox in div.find_elements(By.XPATH, "//div[@role='checkbox']"):
                if checkbox.get_attribute("aria-checked") == 'true':
                    checkbox.click()
                    time.sleep(1)
            break

    time.sleep(2)

    logger.info(f"User {username} is joining the meeting..")
    driver.find_element(By.XPATH, "//button[text()='Join now']").click()
    logger.info(f"User {username} has successfully joined the meeting..")

    return driver


if __name__ == "__main__":
    # read the meeting url
    with open(os.path.join(WRK_DIR, "meeting_url.txt"), "r") as fp:
        meeting_url = fp.read()
        logger.debug(f"Read the meeting url from txt file. Url is {meeting_url}")

    if "context" not in meeting_url or "meetup-join&deeplinkId=" not in meeting_url:
        raise AttributeError("Join Meeting URL pattern does not match, Please check the url..")
    meeting_url = get_direct_join_url(meeting_url)

    # read the username
    with open(os.path.join(WRK_DIR, "usernames.txt"), "r") as fp:
        usernames = fp.readlines()
        usernames = [user.strip() for user in usernames]
        logger.debug(f"Read and found {len(usernames)} total users in username file.")

    # Read the meeting exit time.
    with open(os.path.join(WRK_DIR, "meeting_exit_time_in_minutes.txt"), "r") as fp:
        close_time = fp.read()
        logger.debug(f"Read the meeting exit time. It is {close_time}")

    try:
        close_time = int(close_time)
    except ValueError:
        logger.error(f"Unable to convert meeting exit time {close_time} to int")
        raise ValueError("Meeting time should be a integer number..")

    total_number_of_users = len(usernames)

    max_workers = (total_number_of_users // 5)+1
    logger.debug(f"Max number to workers are {max_workers}")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        drivers = executor.map(join_meeting, usernames, [meeting_url]*len(usernames))

    logger.info(f"Waiting for {close_time} minutes to close the browsers..")
    time.sleep(close_time*60)
    [driver.close() for driver in drivers]
