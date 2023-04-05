#!/usr/bin/python
import sys
from subprocess import check_output, call
from multiprocessing import Process
from scraper import CrunchyScraper
from easygui import choicebox, multchoicebox
from termcolor import colored
import os
from pathlib import Path
import signal
import datetime


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
                    if "++" in inp:
                        if "," in inp or "-" in inp:
                            print(colored("++ is only allowed with single episode - aborting", "red"))
                            terminate_sigint(None, None)

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
                        if "++" in inp:
                            return choices[int(inp) - 1:]
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

    def terminate_sigint(SignalNumber, Frame):
        print(colored("Terminating Process and removing temporary files as SIGINT was caught!", "red"))
        variables = globals()
        if 'proc' in variables and proc is not None:
            print(colored("Process was found, calling terminate() function", "red"))
            proc.terminate()

        if 'delete_after' in variables and delete_after > 0:
            tmp_path = Path.joinpath(CrunchyScraper.FILE_PATH, "episodes-tmp")
            for filename in tmp_path.glob("tmp*.mp4"):
                print(colored(f"Deleting {filename}", "red"))
                os.remove(filename)
        print(colored("Cleanup done, exiting.", "green"))
        sys.exit(1)

    signal.signal(signal.SIGINT, terminate_sigint)

    with open(Path.joinpath(CrunchyScraper.FILE_PATH,"config.cfg"), "r") as cfg:
        config_lines = cfg.readlines()
        cfg.close()

    config = {}
    for line in config_lines:
        eq_index = line.index("=")
        config[line[:eq_index]] = line[eq_index+1:].strip("\n")

    print(colored("\nScraping all Crunchyroll animes - if done for the first time, a browser window is opened, which"
          + " will take some time. Are you sure you want to continue?", "red"))

    input(colored("\n Press any key to continue...", "green"))

    text_only = int(config["TEXT_ONLY"])
    passwd_path = config["GPG_PASSWD_FILE"]
    passwd_split = check_output(["gpg", "-d", passwd_path]).decode("utf-8").split("\n")
    username = passwd_split[0].strip("\n")
    password = passwd_split[1].strip("\n")
    force_episodes = False if int(config["FORCE_EPISODES_UPDATE"]) <= 0 else True
    force_seasons = False if int(config["FORCE_SEASONS_UPDATE"]) <= 0 else True
    case_sens = int(config["CASE_SENSITIVE"])
    delete_after = int(config["DELETE_AFTER_DOWNLOAD"])
    episodes_tmp_path = Path.joinpath(CrunchyScraper.FILE_PATH, "episodes-tmp")
    episodes_save_path = Path.joinpath(CrunchyScraper.FILE_PATH, "episodes-save")

    if not os.path.exists(episodes_tmp_path) and delete_after > 0:
        os.mkdir(episodes_tmp_path)
    elif not os.path.exists(episodes_save_path) and delete_after <= 0:
        os.mkdir(episodes_save_path)
    if case_sens <= 0:
        case_sens = False
    else:
        case_sens = True
    cs = CrunchyScraper(
        driver_path=config["CHROME_DRIVER_PATH"], anchor_start=config["FIRST_SERIES"], anchor_end=config["LAST_SERIES"],
        text_only=text_only, username=username, password=password, scroll_speed=config["SCROLL_SPEED"],
        force_episode_update=force_episodes, force_seasons_update=force_seasons
    )
    title = input(colored("\nPlease enter the name of the Anime you want to browse:\t", "green"))

    animes = cs.print_found_animes(title, how_many_entries_to_show=int(config["SHOW_SERIES_AMOUNT"]),
                                   jaro_weight=int(config["JARO_WEIGHT"]),
                                   leven_weight=int(config["LEVEN_WEIGHT"]),
                                   hamming_weight=int(config["HAMMING_WEIGHT"]), case_sensitive=case_sens)
    title_only_list = [f"{i+1}: {animes[i][0]}" for i in range(len(animes))]

    anime = selection("Select the Anime to scrape", "Anime selection", title_only_list, False, text_only)
    anime_index = int(anime.split(":")[0])-1

    anime = animes[anime_index]

    print(colored(
        "Now we try to determine which Season and which Episodes to watch. If scraping an anime for the first time,"
        + " again please let the Browser continue. You will need to select the season in the modal dialogue", "green"))

    episodes, season_title = cs.browse_series(anime[0], anime[1])
    season_title_stripped = season_title.replace(' ', '')
    last_episode_path = Path.joinpath(
        cs.FILE_PATH, "Anime-Cache", anime[0], season_title_stripped + "_last_episode.txt")

    titles_only = list(episodes.keys())
    episodes_choices = [f"{i+1}: {titles_only[i]}" for i in range(len(titles_only))]
    for episode in episodes_choices:
        print(episode)

    if os.path.exists(last_episode_path):
        last_log = open(last_episode_path, "r")
        content = last_log.readlines()
        newest_title = ''
        newest_count = -1
        newest_date = datetime.datetime(1970, 1, 1, 12, 0, 0, 0)
        for line in content:
                line = line.replace("\n", "")
                spl = line.split(";split;")
                ep_date = datetime.datetime.strptime(spl[2], "%c")
                if ep_date > newest_date:
                    newest_count = int(spl[1])
                    newest_title = spl[0]
                    newest_date = ep_date
        print(colored(
            f"\nThe last, new episode of that season you have seen was {newest_title}\n"
            + f"You have seen that episode {newest_count} times, the last time on {newest_date.strftime('%c')}", "green"
        ))
        last_log.close()

    episode_selection = selection(
        "Please Select episodes to watch. If multiple are selected, they are streamed consecutively.",
        "Episode selection", episodes_choices, True, text_only)

    proc = None
    downloaded = 0
    for episode in episode_selection:
        title = episode.split(": ")[1]
        url = episodes[title]

        if int(config["ONLY_STREAM"]) > 0:
            print(colored("Not supported at the moment as streamlink crunchyroll plugin is broken! Aborting", "red"))
            sys.exit()
            # print(colored(f"Streaming {title} ({url})...", "green"))
            # wait till crunchyroll plugin is fixed
            # return_code = call(["streamlink", f"--crunchyroll-username='{username}'",
            #                    f"--crunchyroll-password='{password}'", url])
        else:
            print(colored(f"Downloading and then streaming {title} ({url})...", "green"))
            crunchy_cli = config["CRUNCHY_CLI_PATH"]
            return_code1 = call([f"{crunchy_cli} --credentials '{username}:{password}' login"], shell=True)
            if delete_after > 0:
                file_name = Path.joinpath(episodes_tmp_path, f"tmp{downloaded}.mp4")
                return_code2 = call(
                    [f"{crunchy_cli} download -a {config['AUDIO_LANG']} -s {config['SUBTITLE_LANG']} -o {file_name} {url}"],
                    shell=True)
            else:
                title_stripped = title.replace(' ', '')
                file_name = Path.joinpath(episodes_save_path, f"{title_stripped}.mp4")
                return_code2 = call(
                    [f"{crunchy_cli} download -a {config['AUDIO_LANG']} -s {config['SUBTITLE_LANG']} "
                     + f"-o {file_name} {url}"], shell=True)

            if return_code1 != 0 or return_code2 != 0:
                yn = input(colored(
                    f"\nReturn code from crunchy_cli was {return_code1} (login) and {return_code2} (download) "
                    + "instead of 0=OK! Do you want to continue with the next episode? Y/N", "red"
                ))
                if not (yn == "Y" or yn == "y"):
                    terminate_sigint(None, None)
            else:
                def play_file(player_name, player_options, filename, delete=True):
                        call([f"{player_name} {player_options} {filename}"], shell=True)
                        if delete > 0:
                            call([f"rm -rf {filename}"], shell=True)

                if proc is not None:
                    proc.join()

                content = []
                if os.path.exists(last_episode_path):
                    log_file = open(last_episode_path,"r")
                    content = log_file.readlines()
                    log_file.close()

                with open(last_episode_path, "w") as last_log:
                    new_content = []
                    title_found = False
                    for line in content:
                        spl = line.split(";split;")
                        print(f"Comparing {title} to {spl[0]} equals {title in spl[0]}")
                        if title in spl[0]:
                            new_content.append(f"{spl[0]};split;{int(spl[1])+1};split;{datetime.datetime.now().strftime('%c')}\n")
                            title_found = True
                        else:
                            new_content.append(line)
                    if not title_found:
                        new_content.append(f"{title};split;1;split;{datetime.datetime.now().strftime('%c')}\n")
                    last_log.writelines(new_content)
                    last_log.close()

                proc = Process(target=play_file, args=(config['PLAYER_NAME'], config['PLAYER_OPTIONS'], file_name,
                                                       delete_after))
                proc.start()
                downloaded += 1








