# Description

Script as well as class to scrape episode titles and links from Crunchyroll with the help
of Selenium, and then stream selected episodes consecutively with player of your choice.

CAVE: THIS WILL START CHROME/CHROMIUM BROWSER TO SCRAPE THE ANIMES. PLEASE LET IT CONTINUE
(Headless browser seems to not work with cloudflare protection on crunchyroll!)

I will not promise that I'm actively maintaining this when crunchyroll updates their 
website, depends on when I will need the update myself for private usage.

## What it does

Scrapes all series from https://www.crunchyroll.com/videos/alphabetical and saves dict
as animes.pkl for later usage. 
If you want to update the saved series (e.g. crunchyroll adds series), delete the 
flag-animes.read and re-run the script.

Scraping the series needs anchor_start (=Name of the first series on that page, to verify
the page has loaded) and anchor_end (=Name of the last series on that page, to verify all
animes were scraped), fields for that are in the config file.

All season titles of a series are stored in Anime-Cache/series-title/seasons.pkl - delete that if you want to update it

All episode titles and links are stored in Anime-Cache/series-title/seasontitle.pkl - delete that if you want to update

## Workflow
At the beginning, the script will ask for the password you have set to gpg decrypt your password file.

During the script execution, it will first ask for a series title (e.g. One Piece), it will then
search all animes and present you results, from which you have to choose which series to 
watch.

Afterwards it will present you with options for all seasons of that show, you have to select the season.

Then it will present you with all episodes for that season, from which you have to select
the episodes you want to watch.

The selected episodes will then be streamed with player of your choice consecutively.

# Usage

Just call ./crunchy-script.py (maybe chmod +x crunchy_script.py to make it executable)

# Necessary steps 
-Download webdriver for selenium, then config the Path as CHROME_DRIVER_PATH <br>
	-Only tested it with Chrome/Chromium webdriver. SHOULD work with firefox, but
	needs changes to the selenium code, aka use Firefox webdriver <br>

-Create password file (simple text file) which stores crunchyroll username and password <br>
	-first line: crunchyroll-username <br>
	-second line: crunchyroll-password <br>
	
-Encrypt the file with gpg -c file_name <br>
	-Select password for decrypt later, store in password manager or remember it
	-delete the plain password file <br>
	-configure path to encrypted password file as GPG_PASSWD_FILE <br>
	
-Check that FIRST_SERIES and LAST_SERIES are correct in config file <br>

# Legal warning
(Copied from https://github.com/Godzil/Crunchy)
This application is not endorsed or affliated with CrunchyRoll. 
The usage of this application enables episodes to be downloaded for offline convenience which may be forbidden 
by law in your country. Usage of this application may also cause a violation of the agreed Terms of Service between you 
and the stream provider. A tool is not responsible for your actions; please make an informed decision prior to using 
this application.

ONLY USE THIS TOOL IF YOU HAVE A PREMIUM ACCOUNT

# Configuration 

Please see config.cfg.example for the Fields which are currently used
for configuration.

## Fields

CHROME_DRIVER_PATH <br>
	-path to chrome webdriver binary for selenium <br>
GPG_PASSWD_FILE <br>
	-path to gpg encrypted passwd file. Plain text file has to have 2 lines, first
	line is the username, second line is the password. <br>
TEXT_ONLY <br>
	-<= 0 => Script will only ask for your input as text in terminal <br>
	- > 0 => Series, Season and Episode selection will use easygui choicebox <br>
SCROLL_SPEED <br>
	- https://www.crunchyroll.com/videos/alphabetical is scrolled by just repeatedly
	invoking ARROW_DOWN to the page body. This reflects the amount how often the key
	is invoked in one scrolling step <br>
FIRST_SERIES <br>
	- name of the first series on https://www.crunchyroll.com/videos/alphabetical <br>
LAST_SERIES <br>
	- name of the last series on https://www.crunchyroll.com/videos/alphabetical <br>
AUDIO_LANG <br>
	- which audio language to download - reflects options from crunchy-cli /
	streamlink <br>
SUBTITLE_LANG <br>
	- which subtitle language to download - reflects options from crunchy-cli /
	streamlink <br>
DELETE_AFTER_DOWNLOAD <br>
	- only affects ONLY_STREAM=0. If set to <= 0, the downloaded episodes are stored
	as <title>.mp4 <br>
	- If set to > 0, the episodes are stored as tmp.mp4, and deleted after the player
	finishes <br>
ONLY_STREAM <br>
	- <=0 => Crunchy-CLI is used to download the episodes first, and then open them
	with player of your choice <br>
	- > 0 => streamlink is used to just stream the episodes directly to player of your
	choice. BROKEN ATM AS STREAMLINK CRUNCHYROLL PLUGIN THROWS 403! <br>
JARO_WEIGHT <br>
	- when searching for series, jellyfish jaro_similarity,
	damerau_levenshtein_distance and hamming_distance are used to compare the strings <br>
	- this is the weight how heavily the score influences the rank of the results <br>
	- I found just jaro_weight = 1, rest =0 to give the best results <br>
LEVEN_WEIGHT <br>
	- weight of damerau_levenshtein_distance <br>
HAMMING_WEIGHT <br>
	- weight of the hamming_distance <br>
SHOW_SERIES_AMOUNT <br>
	- amount of series to show for selection <br>
CASE_SENSITIVE <br>
	- search for series case sensitive (> 0) or not (<= 0) <br>
PLAYER_NAME <br>
	- name of the player to open the files. Must be the exact name of the bin which
	is used to open in terminal <br>
PLAYER_OPTIONS <br>
	- start options to pass to the player <br>
CRUNCHY_CLI_PATH <br>
	- path to crunchy_cli binary <br>
