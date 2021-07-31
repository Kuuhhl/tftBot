#! python3
import time
import pywintypes
import requests
import pyautogui as pg, sys, win32gui
import config
from lcu_driver import Connector
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Internal League API doesn't have valid SSL certificate
# ► Disabled warnings to prevent console getting spammed every call
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

connector = Connector()


def clickMouse(side="left", delay=0.2):
    pg.mouseDown(button=side)
    time.sleep(delay)
    pg.mouseUp(button=side)


def buyChampions(amount=0):
    for j in range(amount):
        pg.moveTo(
            config.firstChampion[0] + (j * config.distanceOfChampions),
            config.firstChampion[1],
            0.5,
        )
        clickMouse()


def levelUp(amount=0):
    pg.moveTo(config.levelUpButton[0], config.levelUpButton[1], 0.5)

    for _ in range(amount):
        clickMouse()


def moveCharacter(destination=0):
    # Random position 1
    if destination == 0:
        pg.moveTo(config.randomPos1[0], config.randomPos1[1], 0.5)
        clickMouse("right", 0.5)
        return

    # Random position 2
    if destination == 1:
        pg.moveTo(config.randomPos2[0], config.randomPos2[1], 0.5)
        clickMouse("right", 0.5)
        return


def clickExitGame():
    pg.moveTo(config.exitGameButton[0], config.exitGameButton[1])
    clickMouse()


async def getPhase(connection):
    phase = await connection.request("get", "/lol-gameflow/v1/gameflow-phase")
    return await phase.json()


async def searchGame(connection):
    # Keep requeuing if thrown out of lobby
    while True:
        # Create TFT Lobby
        await connection.request("post", "/lol-lobby/v2/lobby", data={"queueId": 1090})
        # Enter queue
        await connection.request(
            "post", "/lol-lobby/v2/lobby/matchmaking/search", data={}
        )

        while True:
            phase = await getPhase(connection)

            # Accept ReadyCheck if shown
            if phase == "ReadyCheck":
                await connection.request(
                    "post", "/lol-matchmaking/v1/ready-check/accept", data={}
                )

            # keep waiting for queue pop
            # / until client finishes reconnecting
            elif phase == "Matchmaking" or phase == "Reconnect":
                pass

            # Requeue if we are thrown out of the queue
            elif phase == "Lobby" or phase == "None":
                break

            # stop searching completely if game started
            else:
                return

            time.sleep(1)


def getTime():
    return requests.get(
        "https://127.0.0.1:2999/liveclientdata/gamestats", verify=False
    ).json()["gameTime"]


def getSummonerName():
    return requests.get(
        "https://127.0.0.1:2999/liveclientdata/activeplayername", verify=False
    ).text[1:-1]


def isDead():
    summonerName = getSummonerName()
    players = requests.get(
        "https://127.0.0.1:2999/liveclientdata/playerlist", verify=False
    ).json()
    for player in players:
        if player["summonerName"] == summonerName:
            return player["isDead"]
    # Player is not dead if does not exist
    return False


def isRunning():
    try:
        requests.get(
            "https://127.0.0.1:2999/liveclientdata/allgamedata", verify=False
        ).json()["gameData"]

        # Check if time changes or is stuck:
        # Before the game starts, the API is already available,
        # but the gameTime stays the same until the loading screen is completed.
        baseTime = getTime()
        time.sleep(1)
        return not getTime() == baseTime

    # if API isn't started yet / doesn't work properly,
    # the game is not running.
    except:
        return False


def waitForGameStart():
    while not isRunning():
        time.sleep(1)
    return


@connector.ready
async def main(connection):
    while True:
        print("Looking for game...")

        await searchGame(connection)

        print("Waiting for game to start...")

        waitForGameStart()

        print("Moving Game to foreground...")

        # Move game to foreground
        leagueGame = win32gui.FindWindow(0, "League of Legends (TM) Client")
        try:
            win32gui.SetForegroundWindow(leagueGame)
            win32gui.BringWindowToTop(leagueGame)
        # For some reason bringing the window to the top doesn't work sometimes.
        except:
            print("Error bringing window to top. Please do it manually.")
            while win32gui.GetForegroundWindow() != leagueGame:
                time.sleep(1)

        print("Starting the bot...")

        # Creating timer for 900 seconds = 15 mins.
        # At predefined timestamps, we do some actions

        remaining = 900
        while True:
            remaining = remaining - 1
            time.sleep(1)

            try:
                if isDead():
                    print("Dead. Entering next game...")

                    # Click 'Leave' button until game closes
                    while isRunning():
                        clicarSairJogo()
                        time.sleep(1)
                    break
            # if we cannot ask the game API if we are dead,
            # it is already closed -> the game is not running anymore.
            except:
                print("Game ended. Entering next game...")
                break

            if remaining == 830:
                buyChampions(2)
                moveCharacter(0)
                moveCharacter(1)

            if remaining == 775:
                buyChampions(1)

            if remaining == 709:
                moveCharacter(1)
                buyChampions(1)
                levelUp(1)

            if remaining == 660:
                buyChampions(1)
                levelUp(1)

            if remaining == 590:
                moveCharacter(1)
                buyChampions(1)
                moveCharacter(0)

            if remaining == 320:
                buyChampions(1)
                levelUp(1)

            if remaining == 260:
                levelUp(1)
                buyChampions(2)
                moveCharacter(1)

            if remaining == 60:
                levelUp(20)
                moveCharacter(0)
                moveCharacter(1)

            # every whole minute after 15 minutes:
            if remaining < 1 and remaining % 60 == 0:
                levelUp(1)
                buyChampions(1)

        print("Starting next game...\n")


connector.start()
