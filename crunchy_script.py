#!/usr/bin/python
import sys
import time
from subprocess import check_output, call
from scraper import CrunchyScraper
from easygui import choicebox, multchoicebox
from termcolor import colored

def selection(msg, title, choices, multi_selection, text_only):
    if text_only <= 0:
        if multi_selection:
            selection = multchoicebox(msg, title, choices)
        else:
            selection = choicebox(msg, title, choices)
        return selection
    else:
        if multi_selection:
            def handle_dash(strin, choices):
                spl = strin.split("-")
                bgn = int(spl[0])
                end = int(spl[1])
                return choices[bgn-1:end]
            inp = None
            while inp is None:
                try:
                    inp = input(colored(f"\n{msg} - e.g. 1,2,4 for explicit selection, 1-4 for range\t", "green"))
                    if "," in inp:
                        insplit = inp.split(",")
                        out_selection = []
                        for spl in insplit:
                            if "-" in spl:
                                out_selection.extend(handle_dash(spl, choices))
                            else:
                                out_selection.append(choices[int(spl)-1])
                        return out_selection
                    elif "-" in inp:
                        return handle_dash(inp, choices)
                    else:
                        return [choices[int(inp)-1]]
                except:
                    pass
        else:
            inp = -1
            while inp == -1:
                try:
                    inp = input(colored(f"\n{msg}\t", "green"))
                    return choices[int(inp)-1]
                except:
                    inp = -1
                    pass




if __name__ == "__main__":
    #out = check_output(["gpg", "-d", "cred.passwd.gpg"])
    with open("config.cfg", "r") as cfg:
        config_lines = cfg.readlines()
        cfg.close()

    config = {}
    for line in config_lines:
        line_split = line.split("=")
        config[line_split[0]] = line_split[1].strip("\n")

    print(colored("\nScraping all Crunchyroll animes - if done for the first time, a browser window is opened, which"
          + " will take some time. Are you sure you want to continue?", "red"))

    input(colored("\n Press any key to continue...", "green"))

    text_only = int(config["TEXT_ONLY"])
    passwd_path = config["GPG_PASSWD_FILE"]
    passwd_split = check_output(["gpg", "-d", passwd_path]).decode("utf-8").split("\n")
    username = passwd_split[0].strip("\n")
    password = passwd_split[1].strip("\n")
    cs = CrunchyScraper(
        driver_path=config["CHROME_DRIVER_PATH"], anchor_start=config["FIRST_SERIES"], anchor_end=config["LAST_SERIES"],
        text_only=text_only, username=username, password=password, scroll_speed=config["SCROLL_SPEED"]
    )
    title = input(colored("\nPlease enter the name of the Anime you want to browse:\t", "green"))


    animes = cs.print_found_animes(title, 50)
    title_only_list = [f"{i+1}: {animes[i][0]}" for i in range(len(animes))]

    anime = selection("Select the Anime to scrape", "Anime selection", title_only_list, False, text_only)
    anime_index = int(anime.split(":")[0])-1

    anime = animes[anime_index]

    print(colored("Now we try to determine which Season and which Episodes to watch. If scraping an anime for the first time,"
          + " again please let the Browser continue. You will need to select the season in the modal dialogue", "green"))

    episodes = cs.browse_series(anime[0], anime[1])
    titles_only = list(episodes.keys())
    episodes_choices = [f"{i+1}: {titles_only[i]}" for i in range(len(titles_only))]
    for episode in episodes_choices:
        print(episode)
    episode_selection = selection("Please Select episodes to watch. If multiple are selected, they are streamed consecutively.",
                  "Episode selection", episodes_choices, True, text_only)

    for episode in episode_selection:
        title = episode.split(": ")[1]
        url = episodes[title]
        print(colored(f"Streaming {title} ({url})...", "green"))
        # wait till crunchyroll plugin is fixed
        #return_code = call(["streamlink", f"--crunchyroll-username='{username}'",
        #                    f"--crunchyroll-password='{password}'", url])

        crunchy_cli = "/home/marcel/.lib/crunchy-cli/crunchy-cli/target/release/crunchy-cli"
        return_code1 = call([f"{crunchy_cli} --credentials '{username}:{password}' login"], shell=True)
        return_code2 = call(
            [f"{crunchy_cli} download -a {config['AUDIO_LANG']} -s {config['SUBTITLE_LANG']} -o tmp.mp4 {url}"],
            shell=True)

        if return_code1 != 0 or return_code2 != 0:
            yn = input(colored(
                f"\nReturn code from crunchy_cli was {return_code1} (login) and {return_code2} (download) "
                +"instead of 0=OK! Do you want to continue with the next episode? Y/N", "red"
            ))
            if not (yn == "Y" or yn == "y"):
                sys.exit(return_code2)
        else:
            call(["vlc --play-and-exit --sub-track=0 tmp.mp4"], shell=True)
            call(["rm -rf tmp.mp4"], shell=True)






