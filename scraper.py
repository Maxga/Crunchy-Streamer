import os.path

import requests
from requests.auth import HTTPBasicAuth
import time
import cloudscraper
import json
from haralyzer import HarParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException as TEX
import pickle
import jellyfish
from pathlib import Path
from easygui import choicebox
from termcolor import colored

class CrunchyScraper:
    _animes = {}
    driver_path = None
    text_only = False
    username = ''
    password = ''
    FILE_PATH = Path(os.path.dirname(__file__))
    PICKLE_FILE_NAME = Path.joinpath(FILE_PATH, "animes.pkl")
    FLAG_FILE_NAME = Path.joinpath(FILE_PATH,"flag-animes.read")
    CACHE_DIRECTORY = Path.joinpath(FILE_PATH, "Anime-Cache")
    # how often selenium tries to recover by scrolling when looking for episodes (because of maybe element stale exc)
    MAX_ERROR_COUNT = 3

    # @driver_path: str, path to webdriver binary
    # @anchor_start: str, text that is supposed to be shown on base_url webpage after loading is finished
    # @anchor_end: str, title after which scraping breaks (last title usually)
    # @scroll_speed: int, how many ARROW_DOWN events are send per scrape. I tried with page_down, but some entries were skipped
    # @har_path: str, if set it will try to parse .har file in order to create the dict, without selenium
    def __init__(self, driver_path=None, anchor_start='11eyes', anchor_end='ZOMBIE LAND SAGA', scroll_speed=5,
                 har_path = None, text_only=0, username='', password=''):
        self.text_only = text_only
        self.username = username
        self.password = password
        if os.path.exists(self.FLAG_FILE_NAME):
            print(colored(
                "\nAnimes already read - loading. If you want to re-parse, delete {}".format(self.FLAG_FILE_NAME), "green"
            ))
            with open(self.PICKLE_FILE_NAME, 'rb') as ani_file:
                self._animes = pickle.load(ani_file)
                print(colored("\nAnimes successfully loaded.", "green"))
                ani_file.close()
            return

        if har_path is not None:
            self.parse_har(har_path)
            return

        self.base_url = "https://www.crunchyroll.com/videos/alphabetical"
        # This does not work in headless mode due to cloudflare..
        if driver_path is not None:
            wdrv = webdriver.Chrome(driver_path)
            self.driver_path = driver_path
        else:
            wdrv = webdriver.Chrome()
        wdrv.maximize_window()
        wdrv.get(self.base_url)
        try:
            self.wait_for_string_in_page(wdrv, anchor_start)
        except TimeoutError:
            print("Error while waiting for {} in page_source".format(anchor_start))
            wdrv.close()
            return None

        bgn = time.time()
        end_anchor_read = False
        while True:
            elems = wdrv.find_elements(By.XPATH,"//a[contains(@class,'horizontal-card-static')]")
            for elem in elems:
                try:
                    title = elem.get_attribute("title")
                    href = elem.get_attribute("href")
                    # just overwriting is faster I think, bot lookup is constant anyways
                    if title not in self._animes and title != '':
                        self._animes[title] = href

                    if title == anchor_end:
                        end_anchor_read = True
                except:
                    print("No title found for elem - has the crunchyroll page layout changed?")

            # scroll and wait
            body = wdrv.find_element(By.CSS_SELECTOR,'body')
            for i in range(scroll_speed):
                body.send_keys(Keys.ARROW_DOWN)

            if time.time() - bgn > 1200:
                print("Breaking because of timeout")
                break
            if end_anchor_read:
                print("Breaking because end anchor was found - all was parsed")
                break

        # save dict and write flag
        with open('animes.pkl', 'wb') as ani_file:
            pickle.dump(self._animes, ani_file)
            print("Animes pickled into animes.pkl.")
            ani_file.close()
        open("flag-animes.read", "w").close()
        wdrv.close()

    def _wait_until_appears(self, wdrv, by_what):
        element = WebDriverWait(wdrv, 10).until(EC.presence_of_element_located(by_what))
        return element

    def _wait_until_multiple_appear(self, wdrv, by_what):
        elements = WebDriverWait(wdrv, 10).until(EC.presence_of_all_elements_located(by_what))
        return elements

    def _login(self, wdrv):
        user_icon = self._wait_until_appears(wdrv, (By.XPATH, "//div[contains(@class,'erc-anonymous-user-menu')]"))
        user_icon.click()
        login_menu = self._wait_until_appears(wdrv, (By.XPATH, "//div[contains(@class,'user-menu-section')]"))
        # first is "Create Account", second is "Log In"
        login_button = WebDriverWait(login_menu, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "erc-user-menu-nav-item")))[1]
        login_button.click()
        username_field = self._wait_until_appears(wdrv, (By.ID, "username_input"))
        password_field = self._wait_until_appears(wdrv, (By.ID, "password_input"))
        submit_button = self._wait_until_appears(wdrv, (By.ID, "submit_button"))
        username_field.send_keys(self.username)
        password_field.send_keys(self.password)
        submit_button.click()

    def _get_season_number_from_user(self, season_titles):
        season_selection_titles = [f"{i+1}: {season_titles[i]}" for i in range(len(season_titles))]
        if self.text_only <= 0:
            choice = None
            while choice is None:
                choice = choicebox("Select the Season to scrape.", "Season selection ",season_selection_titles)
            return int(choice.split(":")[0])
        else:
            for i in range(len(season_titles)):
                print(f"{i+1}: {season_titles[i]}")
            inp = -1
            while inp == -1:
                try:
                    inp = int(input(colored(f"\nSelect the Season to scrape.\t", "green")))
                    if inp > 0 and inp <= len(season_titles):
                        return inp
                except:
                    pass
                finally:
                    inp = -1

    def _load_episodes_for_season(self, wdrv):
        episodes_dict = {}
        errors_detected = 0
        while True:
            try:
                episodes = \
                    self._wait_until_multiple_appear(wdrv,
                                                     (By.XPATH, "//a[contains(@class,'playable-card-static__link')]"))
                for episode in episodes:
                    title = episode.get_attribute("title")
                    href = episode.get_attribute("href")
                    if title != '':
                        episodes_dict[title] = href
            except TEX:
                print("No Episodes detected - this should not happen, trying to scroll to save it")
                body = wdrv.find_element(By.CSS_SELECTOR, 'body')
                body.send_keys(Keys.PAGE_DOWN)
                errors_detected += 1
                if errors_detected >= self.MAX_ERROR_COUNT:
                    print("Failed to recover - critical error! Aborting!")
                    wdrv.close()
                    return None
                pass

            try:
                buttons = \
                    self._wait_until_multiple_appear(wdrv, (By.XPATH, "//div[contains(@role,'button')]"))
                show_more_present = False
                for button in buttons:
                    if button.get_attribute("data-t") == "show-more-btn":
                        show_more_present = True
                        show_more_button = button
                if not show_more_present:
                    raise TEX("Show More button is not present!")
            except TEX:
                print("All episodes loaded - finishing season scraping")
                return episodes_dict

            # This part is only executed, if Show More button is present -> else return
            bgn = time.time()
            while not show_more_button.is_displayed():
                body = wdrv.find_element(By.CSS_SELECTOR, 'body')
                body.send_keys(Keys.PAGE_DOWN)
                if time.time() - bgn > 30:
                    print("Timeout while trying to bring the show more button into sight - aborting")
                    wdrv.close()
                    return None
            WebDriverWait(wdrv, 10).until(EC.element_to_be_clickable(show_more_button))
            show_more_button.click()

    def _load_season(self, wdrv, season_titles=None, season_title=None):
        try:
            div_parent = self._wait_until_appears(wdrv, (By.XPATH, "//div[contains(@class,'season-info')]"))
            WebDriverWait(div_parent, 10).until(EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'erc-seasons-select')]")
            )).click()
            seasons = self._wait_until_multiple_appear(wdrv, (By.XPATH, "//div[contains(@class,'extended-option')]"))

            if season_titles is None or season_title is None:
                season_titles = []
                for i in range(len(seasons)):
                    season_titles.append(seasons[i].text)
                inp = self._get_season_number_from_user(season_titles)
                season_title = season_titles[inp - 1]
            else:
                inp = season_titles.index(season_title) + 1
            seasons[inp - 1].click()
            # episodes_amount = season_title.split("\n")[1].split(" ")[0]
        except TEX:
            if season_titles is None:
                print("Season-Info DIV not found - assuming only one season - scraping...")
                div_parent = self._wait_until_appears(wdrv, (By.XPATH, "//div[contains(@class,'seasons-select')]"))
                season_title = WebDriverWait(div_parent, 10).until(EC.presence_of_element_located(
                    (By.XPATH, "//h4[contains(@class,'text')]")
                )).text
                season_titles = [season_title]
        return season_titles, season_title

    def browse_series(self, title, url):
        if not os.path.exists(self.CACHE_DIRECTORY):
            os.mkdir(self.CACHE_DIRECTORY)

        title_subdir_path = Path.joinpath(self.CACHE_DIRECTORY, title.lower())
        if not os.path.exists(title_subdir_path):
            os.mkdir(title_subdir_path)

        seasons_pickle_path = Path.joinpath(title_subdir_path, "seasons.pkl")
        season_titles = None
        season_title = None
        season_loaded = False

        if os.path.exists(seasons_pickle_path):
            with open(seasons_pickle_path, 'rb') as seas_pckl:
                season_titles = pickle.load(seas_pckl)
                seas_pckl.close()
                print(colored(
                    f"\nSeason titles load from pickle-Cache - if you want to update, delete {seasons_pickle_path}", "green"
                ))
            season_title = season_titles[self._get_season_number_from_user(season_titles) - 1]
            season_title_formatted = season_title.replace(' ', '').replace('\n', '')
            title_pickle_path = Path.joinpath(title_subdir_path, f"{season_title_formatted}.pkl")
            x = os.path.exists(title_pickle_path)
            season_loaded = True

            if os.path.exists(title_pickle_path):
                with open(title_pickle_path, 'rb') as tit_pick:
                    episodes_dict = pickle.load(tit_pick)
                    tit_pick.close()
                    print(colored(
                        f"\nEpisodes load from pickle-Cache - if you want to update, delete {title_pickle_path}", "green"
                    ))
                    return episodes_dict

        if self.driver_path is not None:
            wdrv = webdriver.Chrome(driver_path)
        else:
            wdrv = webdriver.Chrome()
        wdrv.maximize_window()
        wdrv.get(url)
        self._login(wdrv)
        body = wdrv.find_element(By.CSS_SELECTOR, 'body')
        body.send_keys(Keys.PAGE_DOWN)
        season_titles, season_title = self._load_season(wdrv, season_titles, season_title)
        season_title_formatted = season_title.replace(' ', '').replace('\n','')

        if not season_loaded:
            with open(seasons_pickle_path, 'wb') as seas_pckl:
                pickle.dump(season_titles, seas_pckl)
                seas_pckl.close()
                print(colored(
                    f"\nSeasons pickled - cached for later usage. If you want to update, delete {seasons_pickle_path}", "green"
                ))

        # Click accept cookies if available
        try:
            WebDriverWait(wdrv, 10).until(EC.element_to_be_clickable((By.ID, "_evidon-decline-button"))).click()
        except:
            pass

        episodes_dict = self._load_episodes_for_season(wdrv)
        title_pickle_path = Path.joinpath(title_subdir_path, f"{season_title_formatted}.pkl")
        with open(title_pickle_path, 'wb') as episode_pickle:
            pickle.dump(episodes_dict, episode_pickle)
            print(colored(
                f"\nEpisodes pickled - cached for later usage. If you want to update, delete {title_pickle_path}", "green"
            ))
            episode_pickle.close()
        wdrv.close()
        return episodes_dict

    #Manually( or automated with some browser script) inspect network traffic with developer tools,
    # scroll / browse so that every anime in the base_url is parsed
    # then save that .har file and give it to this function
    # UNTESTED!!! needs more work
    def parse_har(self, har_path):
        anime_urls = {}
        with open(har_path, "r") as har_file:
            har_parser = HarParser(json.loads(har_file.read()))
            har_data = har_parser.har_data['entries']
        for entry in har_data:
            url = entry['request']['url']
            if "https://www.crunchyroll.com/content/v2/discover/browse?n=" in url:
                anime_chunk = json.loads(entry['response']['content']['text'])['data']
                for anime in anime_chunk:
                    title = anime['title']
                    url = "https://www.crunchyroll.com/series/{}".format(anime['id'])
                    if title not in anime_urls and title != '':
                        anime_urls[title] = url
        self._animes = anime_urls

    def wait_for_string_in_page(self, webdriver, substring, timeout=30):
        bgn = time.time()
        end = time.time()
        while substring not in webdriver.page_source:
            time.sleep(1)
            end = time.time()
            if end-bgn > timeout:
                raise TimeoutError("Timeout while waiting for {} to be present in page_source".format(substring))

    def get_animes(self):
        return self._animes

    def _animes_to_case_insensitive(self):
        case_ins_animes = {}
        for key in self._animes:
            case_ins_animes[key.lower()] = self._animes[key]
        self._animes = case_ins_animes

    # does not scale well, but okay for the small number of animes on crunchyroll
    # weights: how to scale different string similarity results, I found best results are found with only jaro simil.
    def find_animes(self, title_to_find, how_many_entries_to_show=50, jaro_weight=1, leven_weight=0, hamming_weight=0,
                    case_sensitive=False):
        if not case_sensitive:
            self._animes_to_case_insensitive()
            title_to_find = title_to_find.lower()
        title_distance_list = [
            (title, self._animes[title],
             jellyfish.damerau_levenshtein_distance(title, title_to_find),
             jellyfish.jaro_similarity(title, title_to_find),
             jellyfish.hamming_distance(title, title_to_find)
             )
            for title in self._animes
        ]
        leven_sort = sorted(title_distance_list, key=lambda tup: tup[2])
        jaro_sort = sorted(title_distance_list, key=lambda tup: tup[3], reverse=True)
        hamming_sort = sorted(title_distance_list, key=lambda tup: tup[4])
        title_metrics = {key:0 for key in self._animes}
        for i in range(len(self._animes)):
            title_metrics[leven_sort[i][0]] += leven_weight*float(i)
            title_metrics[jaro_sort[i][0]] += jaro_weight*float(i)
            title_metrics[hamming_sort[i][0]] += hamming_weight*float(i)


        title_list = [(title, self._animes[title]) for title in self._animes]
        title_list.sort(key=lambda tup:title_metrics[tup[0]])
        return title_list[:how_many_entries_to_show]

    def print_found_animes(self, title_to_find, how_many_entries_to_show=50, jaro_weight=1, leven_weight=0,
                           hamming_weight=0, case_sensitive=False):
        titles = self.find_animes(title_to_find, how_many_entries_to_show,
                                  jaro_weight, leven_weight, hamming_weight, case_sensitive)
        for i in range(how_many_entries_to_show):
            print(f"{i+1}. {titles[i][0]} ({titles[i][1]})\n")
        return titles


# Another possibility: cloudscraper, which works, but I didnt finish it because I eventually hit Captcha,
# which the free version of cloudscraper cant handle
# call this in a loop with n=50, n=100, etc...
#         # self.base_url = "https://www.crunchyroll.com/content/v2/discover/browse?n=50&sort_by=alphabetical&locale=en-US"
# self.scraper = cloudscraper.create_scraper(interpreter='native')
        #
        # header = {
        #     "Authorization": "Basic Y3Jfd2ViOg=="
        # }
        #
        # body = {
        #     "grant_type":"client_id"
        # }
        #
        # response = self.scraper.post("https://www.crunchyroll.com/auth/v1/token", headers=header, data=body)
        # if response.status_code != 200:
        #     print("Something went wrong")
        #     return
        # bearer_token = json.loads(response.text)['access_token']
        #
        # header = {
        #     "Authorization": "Bearer {}".format(bearer_token),
        #     "Content-Type": "application/x-www-form-urlencoded",
        #     "Referer": "https://www.crunchyroll.com/videos/alphabetical",
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:111.0) Gecko/20100101 Firefox/111.0"
        # }
        #
        # self.dbg = self.scraper.get(self.base_url, headers=header)