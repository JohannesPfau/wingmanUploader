import os
import requests
import json
import time
import random
import itertools, glob, ctypes
import threading
import sys
import win32api
import win32con
import win32gui_struct
import psutil
import struct
import subprocess
from win32api import *
from win32gui import *
from sysTrayIcon import *
from win32com.shell import shell, shellcon
from win32com.client import Dispatch
import winshell
import datetime
import zipfile
import io

VERSION = "0.0.20"

testURL = "http://nevermindcreations.de:3500/testMongoDB"
versionURL = "http://nevermindcreations.de:3500/currentUploaderVersion"
# uploadURL = "http://nevermindcreations.de:3500/upload"
uploadProcessedURL = "http://nevermindcreations.de:3500/uploadProcessed"
checkUploadURL = "http://nevermindcreations.de:3500/checkUpload"
EIreleasesURL = "https://api.github.com/repos/baaron4/GW2-Elite-Insights-Parser/releases"
gw2EIconf = "SaveAtOut=true\n\
SaveOutHTML=true\n\
ParseCombatReplay=true\n\
SaveOutJSON=true"

initialConfig = {
    'logpath': '',
    'account': 'Account.' + str(random.randint(1000,9999)),                                                                                                                                                                                                              # commited by nala
    'autostart': True,
    'onlyUploadIfGw2Running': False,
    'onlyUploadIfGw2NotRunning': False,
    'notifications': False,
    # 'forceMode': False,
}
config = {}
verbose = True
notificationString = ""

def checkConfig():
    # config #
    if os.path.exists('wingmanUploader.config') and not os.path.exists('wingmanUploader.ini'):
        os.rename('wingmanUploader.config', 'wingmanUploader.ini')
    try:
        with open('wingmanUploader.ini', 'r', encoding='utf-8') as configFile:
            configStr = configFile.read().replace("\\","/")
            config = json.loads(configStr)
            configPresent = True
    except:
        config = {}
        configPresent = False
    configUpdated = False
    for configKey in initialConfig.keys():
        if not config.keys().__contains__(configKey):
            config.update({configKey: initialConfig[configKey]})
            configUpdated = True

    # check logpath
    if not config['logpath'] == "":
        path = os.path.abspath(config['logpath']).replace("\\", "/")
        if not config['logpath'].endswith("/"):
            config['logpath'] += "/"
            configUpdated = True
        if not os.path.exists(path):
            ctypes.windll.user32.MessageBoxW(0,"The logpath you configured does not exist. I set it to my current directory instead.", "gw2Wingman Uploader", 0)
            config['logpath'] = ""
            configUpdated = True
    # check account
    if config['account'].startswith("Account."):
        ctypes.windll.user32.MessageBoxW(0, "You did not specify your account name in the .ini - Please add this as it will accelerate the upload significantly.\r\n(We check each log for duplicates, but have to process it first to get the involved account names. If you specify your account in the ini, this process can be skipped and your logs will be uploaded way faster!)", "gw2Wingman Uploader", 0)

    if configUpdated:
        with open('wingmanUploader.ini', 'w') as outfile:
            json.dump(config, outfile, indent=4)
    return [configPresent, config]

discMsgDisplayed = False
def startUploadingProcess():
    global notificationString
    if notificationString:
        tryNotification(notificationString, True)
        notificationString = None

    if (config['onlyUploadIfGw2NotRunning'] and isGW2Running()) or (config['onlyUploadIfGw2Running'] and not isGW2Running()):
        sysTrayApp.changeMenuEntry("Status: SLEEPING")
        if verbose:
            print(str(datetime.datetime.now()) + ": Sleeping.")
        time.sleep(10)
        rethreadUploadingProcess()
        return

    # blacklist #
    if os.path.exists('wingmanUploader.exclude'):
        try:
            with open('wingmanUploader.exclude', 'r', encoding='utf-8') as blacklistFile:
                blacklist = json.load(blacklistFile)
                if blacklist.keys().__contains__('lastUpdate'):
                    del blacklist['lastUpdate']
        except:
            pass
    else:
        # blacklist = {"lastUpdate": 0, "excludeFiles": []}
        blacklist = {"excludeFiles": []}
        with open('wingmanUploader.exclude', 'w') as outfile:
            json.dump(blacklist, outfile)

    # look for new logs #
    filesToUpload = []
    fileTimes = []
    for r, d, f in os.walk(config['logpath']):
        for file in f:
            args = r + "/" + file
            if not args.endswith(".zevtc") and not args.endswith(".evtc") and not args.endswith(".evtc.zip"):
                continue
            # if os.path.getmtime(args) < blacklist['lastUpdate']:    # skip old files
            #     continue
            if os.path.getsize(args) < 100:  # skip small files
                continue
            if blacklist['excludeFiles'].__contains__(file):  # skip excluded files
                continue
            filesToUpload.append(args)
            fileTimes.append(os.path.getmtime(args))

    # test connection #
    if len(filesToUpload) > 0:
        testConnection = False
        try:
            testR = requests.get(testURL)
            if testR.text == "True":
                testConnection = True
        except:
            testConnection = False

        if not testConnection:
            sysTrayApp.changeMenuEntry("Status: DISCONNECTED")
            global discMsgDisplayed
            if not discMsgDisplayed:
                tryNotification("Unable to connect to server.")
                discMsgDisplayed = True
            if verbose:
                print(str(datetime.datetime.now()) + ": Disconnected.")
            time.sleep(60)
            rethreadUploadingProcess()
            return

    # sort after filetime #
    filesToUpload = [x for _,x in sorted(zip(fileTimes,filesToUpload))]
    # fileTimes = [x for _,x in sorted(zip(fileTimes,fileTimes))]

    # upload new logs #
    if len(filesToUpload) > 0:
        if verbose:
            print("Checking " + str(len(filesToUpload)) + " new logs.")
        tryNotification("Checking " + str(len(filesToUpload)) + " new logs.",False)
    filesUploaded = 0
    filesFailed = 0
    for fileToUpload in filesToUpload:
        # zip before upload if its not .zevtc
        if fileToUpload.endswith(".evtc"):
            try:
                # data
                file = os.path.basename(fileToUpload)
                filepath = os.path.dirname(fileToUpload)
                newFile = fileToUpload.replace(".evtc", ".zevtc")

                # zip
                zf = zipfile.ZipFile(fileToUpload.replace(".evtc", ".zevtc"), 'w', zipfile.ZIP_DEFLATED)
                zf.write(fileToUpload, file)
                zf.close()
                # remove
                os.remove(fileToUpload)

                # change reference
                fileToUpload = newFile
            except:
                print("Not able to zevtc")

        try:
            with open(fileToUpload, 'rb') as f:
                filename = os.path.basename(f.name)

                # check if needs to be uploaded
                payload = {'file': filename, 'filesize': os.stat(fileToUpload).st_size, 'account': config['account'],
                           'timestamp': int(os.stat(fileToUpload).st_mtime)}
                checkR = requests.post(checkUploadURL, data=payload)

                if checkR.text == "False" and not (config.keys().__contains__('forceMode') and config['forceMode']):
                    filesFailed += 1
                    if verbose:
                        print("[" + str(int(100*(filesUploaded+filesFailed)/len(filesToUpload))) + "%] ("+str(len(filesToUpload)-(filesUploaded+filesFailed))+" left). SKIP: " + f.name)
                else:
                    if checkR.text == "True" or (config.keys().__contains__('forceMode') and config['forceMode']):
                        # actually upload it
                        #r = requests.post(uploadURL, files={'file': f}, data={'account': config['account']})
                        # Rework: client-side processing before upload
                        directory = os.path.dirname(f.name)
                        directory = (os.path.abspath(directory) + "/").replace("\\", "/")
                        evtcFilesize = os.stat(directory + filename).st_size

                        # adjust sample.conf in case someone fooled around with it
                        try:
                            samplef = open("GW2EI/Settings/sample.conf", "w")
                            samplef.write(gw2EIconf)
                            samplef.close()
                        except:
                            ctypes.windll.user32.MessageBoxW(0, "Could not locate GW2EI config. Please reinstall or contact admin.", "gw2Wingman Uploader", 0)
                            sys.exit(1)

                        GW2EIdir = (os.path.abspath('') + "/GW2EI").replace("\\", "/")
                        args = '"'+GW2EIdir+'/GuildWars2EliteInsights.exe" -p -c "'+GW2EIdir+'/Settings/sample.conf" "' + directory + filename + '"'
                        if verbose:
                            print("run: " + args)
                            before = datetime.datetime.now().timestamp() * 1000
                        subprocess.run(args,shell=True)
                        if verbose:
                            print("GW2EI time: " + str(datetime.datetime.now().timestamp() * 1000 - before) + " ms")


                        # look for result files
                        resultFiles = [resFilename for resFilename in os.listdir(directory) if resFilename.startswith(filename.split(".")[0])]
                        for rf in resultFiles:
                            if rf.endswith(".log"):
                                os.remove(directory + rf)
                            if rf.endswith(".json"):
                                with open(directory + rf, 'r', encoding='utf-8') as logFile:
                                    try:
                                        htmlfile = rf.replace(".json", ".html")
                                        with open(directory + htmlfile, 'r', encoding='utf-8') as htmlF:
                                            # actually upload the files
                                            if config.keys().__contains__('forceMode'):
                                                r = requests.post(uploadProcessedURL, files={'file': f, 'htmlfile': htmlF, 'jsonfile': logFile}, data={'account': config['account'], 'forceMode': config['forceMode']}, stream=True)
                                            else:
                                                r = requests.post(uploadProcessedURL, files={'file': f, 'htmlfile': htmlF, 'jsonfile': logFile}, data={'account': config['account']}, stream=True)

                                            # TODO: only +1 if really uploaded! else "continue"
                                            if r.text != "True":
                                                print(r.text)
                                                filesFailed += 1
                                                continue

                                            filesUploaded += 1
                                            if verbose:
                                                print("[" + str(int(100 * (filesUploaded + filesFailed) / len(filesToUpload))) + "%] (" + str(len(filesToUpload) - (filesUploaded + filesFailed)) + " left). DONE: " + f.name)
                                    except:
                                        print("FAILED to parse: " + directory + rf)
                                        filesFailed += 1
                                        os.remove(directory + htmlfile)
                                        os.remove(directory + rf)
                                        continue

                                # delete afterwards
                                os.remove(directory + htmlfile)
                                os.remove(directory + rf)
                    else:
                        continue  # server error/unclear
                # write update to blacklist file
                blacklist['excludeFiles'].append(filename)
                # if os.path.getmtime(fileToUpload) > blacklist['lastUpdate']:
                #     blacklist['lastUpdate'] = os.path.getmtime(fileToUpload)
                with open('wingmanUploader.exclude', 'w') as outfile:
                    json.dump(blacklist, outfile)
                sysTrayApp.changeMenuEntry("Status: "+ str(int(100*(filesUploaded+filesFailed)/len(filesToUpload))) + "% UPLOADING (" + str(len(filesToUpload)-(filesUploaded+filesFailed)) +" left)")
                if verbose:
                    print(str(datetime.datetime.now()) + ": " + str(int(100*(filesUploaded+filesFailed)/len(filesToUpload))) + "% UPLOADING (" + str(len(filesToUpload)-(filesUploaded+filesFailed)) +" left)")
        except:
            print("Something went wrong")

    if len(filesToUpload) > 0:
        tryNotification("Finished uploading.\r\n" + str(filesUploaded) + " new logs submitted.\r\n" + str(filesFailed) + " duplicates omitted.",False)
    sysTrayApp.changeMenuEntry("Status: UP TO DATE")

    if verbose:
        print(str(datetime.datetime.now()) + ": Up to date.")
    time.sleep(10)
    rethreadUploadingProcess()
    return

def tryCreateAutostart():
    linkPath = shell.SHGetFolderPath(0,shellcon.CSIDL_STARTUP,0,0) + "/wingmanUploader.lnk"
    if config['autostart']:
        if not os._exists(linkPath):
            # create
            wshell = Dispatch('WScript.Shell')
            shortcut = wshell.CreateShortCut(linkPath)
            shortcut.Targetpath = os.path.abspath(".") + "/wingmanUploader.exe"
            shortcut.WorkingDirectory = os.path.abspath(".")
            shortcut.IconLocation = os.path.abspath(".") + "/wingmanUploader.exe"
            shortcut.save()
    else:
        if os.path.exists(linkPath):
            os.remove(linkPath)  # delete if still exists
    return

def tryNotification(message):
    return tryNotification(message,False)

def tryNotification(message, forceNotification):
    if forceNotification or config['notifications']:
        notificationThread = threading.Thread(target=notificationWindow.ShowWindow, args={message, "Wingman Uploader"})
        notificationThread.setDaemon(True)
        notificationThread.start()
    return

def isGW2Running():
    procs = [p for p in psutil.process_iter() if 'Gw2.exe' in p.name() or 'Gw2-64.exe' in p.name()or 'Gw2-32.exe' in p.name()]
    if len(procs) > 0:
        return True
    return False

def rethreadUploadingProcess():
    uploadThread = threading.Thread(target=startUploadingProcess)
    uploadThread.setDaemon(True)
    uploadThread.start()
    return

# Main tray application
if __name__ == '__main__':
    # check for singleton instance:
    procs = [p for p in psutil.process_iter() if 'wingmanUploader.exe' in p.name()]
    if len(procs) > 2:  #2 because of daemon
        sys.exit(1)

    if not os.path.exists("favicon.ico"):
        ctypes.windll.user32.MessageBoxW(0, "Hey! It seems that you have lost 'favicon.ico'. Please put this in the same folder or download the uploader again.", "gw2Wingman Uploader", 0)
        sys.exit(1)
    localEIversion = ""
    if os.path.exists("GW2EI/GuildWars2EliteInsights.exe"):
        localEIversion = Dispatch("Scripting.FileSystemObject").GetFileVersion("GW2EI/GuildWars2EliteInsights.exe")
    localEIversion = "v" + localEIversion
    EIrequest = requests.get(EIreleasesURL).json()
    recentEIversion = EIrequest[0]["name"]
    # print("Compare:", localEIversion, recentEIversion, localEIversion==recentEIversion)

    if not localEIversion==recentEIversion:
        for asset in EIrequest[0]["assets"]:
            if asset["name"] == "GW2EI.zip":
                assetURL = asset["browser_download_url"]
                print("download", asset["browser_download_url"])
                eizip_r = requests.get(asset["browser_download_url"])
                if not eizip_r.ok:
                    ctypes.windll.user32.MessageBoxW(0, "I was unable to update the most recent Elite Insights version! You might want to report this.", "gw2Wingman Uploader", 0)
                    sys.exit(1)
                eizip = zipfile.ZipFile(io.BytesIO(eizip_r.content))
                eizip.extractall("GW2EI")
                # global notificationString
                notificationString = "Updated EliteInsights version to " + recentEIversion + "."
                break

    icons = itertools.cycle(glob.glob('*.ico'))
    icon = next(icons)

    def visit(sysTrayIcon): os.startfile("https://gw2wingman.nevermindcreations.de/")
    def openLogFolder(sysTrayIcon): os.startfile(config['logpath'])
    def openConfig(sysTrayIcon): os.startfile("wingmanUploader.ini")
    def help(sysTrayIcon): os.startfile("https://gw2wingman.nevermindcreations.de/uploader")
    def bye(sysTrayIcon): print('Shutting down.')

    menu_options = (('Status: PENDING',icon, help),
                    ('Visit gw2wingman',icon, visit),
                    ('Open log folder', icon, openLogFolder),
                    ('Open config', icon, openConfig),
                    ('Help (v'+str(VERSION)+')', icon, help),
                    # ('Switch Icon', None, switch_icon),
                    # ('A sub-menu', next(icons), (('Say Hello to Simon', next(icons), simon),
                    #                              ('Switch Icon', next(icons), switch_icon),
                    #                              ))
                    )

    [configPresent, config] = checkConfig()
    if not configPresent:  # if not configured: open it in advance
        ctypes.windll.user32.MessageBoxW(0, "Hey!\r\nIt seems that this is your first time running gw2wingman uploader.\r\nPlease specify the path to your arcdps logs in the .ini (if you didnt put the uploader into the same directory) and add your ingame account name (helps with faster uploads).", "gw2Wingman Uploader", 0)
        openConfig(icon)
    else:  # start tray app
        shutdown = False
        try:
            versionR = requests.get(versionURL)
            if "Error" in versionR.text:
                response = ctypes.windll.user32.MessageBoxW(0,"I was not able to reach the wingman server :( \r\nPlease try again later.","gw2Wingman Uploader", 1)
                shutdown = True
            elif versionR.text.replace("!","") != VERSION:
                if not versionR.text.__contains__("!"):
                    response = ctypes.windll.user32.MessageBoxW(0,"A new version is available!\r\nPress OK to download the update and replace the wingmanUploader.exe","gw2Wingman Uploader", 1)
                    if response == 1: # OK
                        os.startfile("https://gw2wingman.nevermindcreations.de/downloadUploader")
                else:
                    response = ctypes.windll.user32.MessageBoxW(0,"A critical update is required!\r\nPlease download the latest version and replace the wingmanUploader.exe","gw2Wingman Uploader", 1)
                    if response == 1: # OK
                        os.startfile("https://gw2wingman.nevermindcreations.de/downloadUploader")
                    shutdown = True # dont shutdown in try block
        except:
            print("no server connection")
        if shutdown:
            sys.exit(0)

        notificationWindow = WindowsBalloonTip()
        tryCreateAutostart()
        sysTrayApp = SysTrayIcon(next(icons), "gw2wingman Uploader", menu_options, on_quit=bye, default_menu_index=1)
        if verbose:
            print(str(datetime.datetime.now()) + ": Startup")
        uploadThread = threading.Thread(target=startUploadingProcess)
        uploadThread.setDaemon(True)
        uploadThread.start()
        sysTrayApp.startTray()