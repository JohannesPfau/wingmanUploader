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
# from win32com.shell import shell, shellcon
from win32com.client import Dispatch
import winshell
import datetime
import zipfile
import io

VERSION = "0.0.19"

testURL = "https://gw2wingman.nevermindcreations.de/testMongoDB"
versionURL = "https://gw2wingman.nevermindcreations.de/currentUploaderVersion"
uploadURL = "https://gw2wingman.nevermindcreations.de/upload"
uploadProcessedURL = "https://gw2wingman.nevermindcreations.de/uploadProcessed"
checkUploadURL = "https://gw2wingman.nevermindcreations.de/checkUpload"
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
            # if not file in ["20210922-230443.zevtc","20210922-231134.zevtc","20210922-231623.zevtc","20210922-232645.zevtc","20210923-005513.zevtc","20210923-145952.zevtc","20210923-150459.zevtc","20210923-150900.zevtc","20210923-151421.zevtc","20210923-011554.zevtc","20210923-011844.zevtc","20210923-151859.zevtc","20210923-012453.zevtc","20210923-013527.zevtc","20210923-014227.zevtc","20210923-014904.zevtc","20210923-003157.zevtc","20210923-003548.zevtc","20210923-004141.zevtc","20210923-004919.zevtc","20210923-005439.zevtc","20210923-010229.zevtc","20210923-212915.zevtc","20210923-144810.zevtc","20210923-145107.zevtc","20210923-145607.zevtc","20210923-150151.zevtc","20210923-150846.zevtc","20210923-151627.zevtc","20210923-152044.zevtc","20210923-152904.zevtc","20210923-163236.zevtc","20210923-164138.zevtc","20210923-164527.zevtc","20210923-165225.zevtc","20210923-180934.zevtc","20210923-181626.zevtc","20210923-183137.zevtc","20210923-184107.zevtc","20210923-184838.zevtc","20210923-124844.zevtc","20210923-195153.zevtc","20210923-125349.zevtc","20210923-210920.zevtc","20210923-211508.zevtc","20210923-212803.zevtc","20210923-213355.zevtc","20210923-213535.zevtc","20210923-213826.zevtc","20210923-205405.zevtc","20210923-215756.zevtc","20210923-220202.zevtc","20210923-220551.zevtc","20210923-210829.zevtc","20210923-212010.zevtc","20210923-221907.zevtc","20210923-212306.zevtc","20210923-222621.zevtc","20210923-212722.zevtc","20210923-222815.zevtc","20210923-212946.zevtc","20210923-223356.zevtc","20210923-223631.zevtc","20210923-223957.zevtc","20210923-214221.zevtc","20210923-224401.zevtc","20210923-224759.zevtc","20210923-215155.zevtc","20210923-225100.zevtc","20210923-215514.zevtc","20210923-225731.zevtc","20210923-230249.zevtc","20210923-220441.zevtc","20210923-220525.zevtc","20210923-220847.zevtc","20210923-221015.zevtc","20210923-230937.zevtc","20210923-221315.zevtc","20210923-221618.zevtc","20210923-222203.zevtc","20210923-222246.zevtc","20210923-232906.zevtc","20210923-223136.zevtc","20210923-233141.zevtc","20210923-223510.zevtc","20210923-223619.zevtc","20210923-233704.zevtc","20210923-224024.zevtc","20210923-221207.zevtc","20210923-224518.zevtc","20210923-234437.zevtc","20210923-225201.zevtc","20210923-225259.zevtc","20210923-235458.zevtc","20210923-175822.zevtc","20210924-082338.zevtc","20210924-083303.zevtc","20210924-084630.zevtc","20210924-085308.zevtc","20210924-090203.zevtc","20210923-190433.zevtc","20210923-190919.zevtc","20210923-191352.zevtc","20210923-191810.zevtc","20210924-091829.zevtc","20210923-192142.zevtc","20210924-092456.zevtc","20210923-192515.zevtc","20210924-092723.zevtc","20210923-193340.zevtc","20210923-193737.zevtc","20210923-194147.zevtc","20210923-195041.zevtc","20210923-201336.zevtc","20210923-201403.zevtc","20210923-201720.zevtc","20210923-201903.zevtc","20210923-202420.zevtc","20210923-202736.zevtc","20210923-202943.zevtc","20210923-203758.zevtc","20210923-174350.zevtc","20210923-175259.zevtc","20210923-180245.zevtc","20210923-210251.zevtc","20210923-180540.zevtc","20210923-180651.zevtc","20210923-211256.zevtc","20210923-182336.zevtc","20210923-182807.zevtc","20210923-183325.zevtc","20210923-213331.zevtc","20210923-183609.zevtc","20210923-184327.zevtc","20210923-214838.zevtc","20210923-185241.zevtc","20210923-215508.zevtc","20210923-215651.zevtc","20210923-185725.zevtc","20210923-190228.zevtc","20210923-190633.zevtc","20210923-192145.zevtc","20210923-222545.zevtc","20210923-193057.zevtc","20210923-194852.zevtc","20210923-225406.zevtc","20210923-225855.zevtc","20210923-230829.zevtc","20210923-230847.zevtc","20210923-231639.zevtc","20210923-231839.zevtc","20210923-232107.zevtc","20210923-233334.zevtc","20210923-203536.zevtc","20210923-234113.zevtc","20210923-204426.zevtc","20210923-234750.zevtc","20210923-235706.zevtc","20210923-205942.zevtc","20210924-000020.zevtc","20210924-000922.zevtc","20210923-211112.zevtc","20210923-211424.zevtc","20210924-001732.zevtc","20210923-212008.zevtc","20210923-212654.zevtc","20210923-213326.zevtc","20210924-004739.zevtc","20210924-005438.zevtc","20210924-010253.zevtc","20210923-223205.zevtc","20210923-224142.zevtc","20210923-224418.zevtc","20210923-221945.zevtc","20210923-222326.zevtc","20210923-222458.zevtc","20210923-224621.zevtc","20210923-225654.zevtc","20210923-231225.zevtc","20210923-203334.zevtc","20210923-203916.zevtc","20210923-204902.zevtc","20210923-211600.zevtc","20210923-212506.zevtc","20210923-213321.zevtc","20210923-214629.zevtc","20210923-215047.zevtc","20210923-215458.zevtc","20210923-221517.zevtc","20210923-222333.zevtc","20210924-190712.zevtc","20210924-191038.zevtc","20210924-191253.zevtc","20210924-191659.zevtc","20210924-192030.zevtc","20210924-192314.zevtc","20210924-192537.zevtc","20210924-193026.zevtc","20210924-193343.zevtc","20210924-193636.zevtc","20210924-193859.zevtc","20210924-194650.zevtc","20210924-215004.zevtc","20210924-215142.zevtc","20210924-195143.zevtc","20210924-195442.zevtc","20210924-215536.zevtc","20210924-195957.zevtc","20210924-220224.zevtc","20210924-220951.zevtc","20210924-221517.zevtc","20210924-221719.zevtc","20210924-222007.zevtc","20210924-222407.zevtc","20210924-223431.zevtc","20210924-223743.zevtc","20210924-224156.zevtc","20210924-224706.zevtc","20210924-225238.zevtc","20210924-225941.zevtc","20210924-230619.zevtc","20210924-211714.zevtc","20210924-212312.zevtc","20210924-213142.zevtc","20210924-160233.zevtc","20210924-161521.zevtc","20210924-161720.zevtc","20210924-162240.zevtc","20210924-224927.zevtc","20210924-225258.zevtc","20210924-225747.zevtc","20210924-165839.zevtc","20210924-230125.zevtc","20210924-230412.zevtc","20210924-231103.zevtc","20210924-231623.zevtc","20210924-232054.zevtc","20210924-232507.zevtc","20210924-233139.zevtc","20210924-233308.zevtc","20210924-234655.zevtc","20210924-235226.zevtc","20210924-214019.zevtc","20210924-214632.zevtc","20210924-205335.zevtc","20210924-215524.zevtc","20210924-220319.zevtc","20210924-210722.zevtc","20210924-210957.zevtc","20210924-211726.zevtc","20210924-222027.zevtc","20210924-212126.zevtc","20210924-212541.zevtc","20210924-152730.zevtc","20210924-222745.zevtc","20210924-153153.zevtc","20210924-213338.zevtc","20210924-223331.zevtc","20210924-223912.zevtc","20210924-225221.zevtc","20210924-225534.zevtc","20210924-230334.zevtc","20210924-231116.zevtc","20210924-230514.zevtc","20210925-000754.zevtc","20210924-231207.zevtc","20210925-001823.zevtc","20210924-231917.zevtc","20210925-002743.zevtc","20210925-003037.zevtc","20210924-233043.zevtc","20210925-003558.zevtc","20210925-004813.zevtc","20210924-175217.zevtc","20210924-235512.zevtc","20210925-010026.zevtc","20210925-000235.zevtc","20210924-180302.zevtc","20210924-181005.zevtc","20210925-001140.zevtc","20210925-001243.zevtc","20210924-181509.zevtc","20210925-001555.zevtc","20210925-001605.zevtc","20210924-181938.zevtc","20210924-182324.zevtc","20210925-002325.zevtc","20210924-182657.zevtc","20210925-002731.zevtc","20210925-003318.zevtc","20210925-003508.zevtc","20210924-183508.zevtc","20210925-003758.zevtc","20210925-004045.zevtc","20210925-004726.zevtc","20210924-184856.zevtc","20210925-005658.zevtc","20210925-010004.zevtc","20210924-190312.zevtc","20210925-010707.zevtc","20210924-191014.zevtc","20210924-191621.zevtc","20210925-012024.zevtc","20210925-012219.zevtc","20210924-192307.zevtc","20210925-012347.zevtc","20210924-192926.zevtc","20210925-013422.zevtc","20210925-014036.zevtc","20210924-194139.zevtc","20210924-194905.zevtc","20210924-195014.zevtc","20210924-195417.zevtc","20210925-015910.zevtc","20210924-200503.zevtc","20210924-223205.zevtc","20210924-223531.zevtc","20210924-223904.zevtc","20210924-225545.zevtc","20210924-230247.zevtc","20210924-215355.zevtc","20210924-220400.zevtc","20210924-190520.zevtc","20210924-190734.zevtc","20210924-191025.zevtc","20210924-221412.zevtc","20210924-191645.zevtc","20210924-222210.zevtc","20210924-192804.zevtc","20210924-193324.zevtc","20210924-193853.zevtc","20210924-195953.zevtc","20210924-232813.zevtc","20210924-233447.zevtc","20210924-203944.zevtc","20210924-204401.zevtc","20210924-205216.zevtc","20210924-210157.zevtc","20210924-210748.zevtc","20210924-211720.zevtc","20210925-001905.zevtc","20210925-122237.zevtc","20210925-002649.zevtc","20210925-204552.zevtc","20210925-205604.zevtc","20210925-210537.zevtc","20210925-210915.zevtc","20210925-211538.zevtc","20210925-212726.zevtc","20210925-213424.zevtc","20210925-214129.zevtc","20210925-214914.zevtc","20210925-215717.zevtc","20210925-220530.zevtc","20210924-124225.zevtc","20210924-125004.zevtc","20210924-125851.zevtc","20210924-130422.zevtc","20210925-135422.zevtc","20210925-135712.zevtc","20210925-140131.zevtc","20210925-141105.zevtc","20210925-141521.zevtc","20210925-141748.zevtc","20210925-142141.zevtc","20210925-142613.zevtc","20210925-142906.zevtc","20210925-143307.zevtc","20210925-143959.zevtc","20210925-144319.zevtc","20210925-144532.zevtc","20210925-144759.zevtc","20210925-145406.zevtc","20210925-230315.zevtc","20210925-150700.zevtc","20210925-230708.zevtc","20210925-230950.zevtc","20210925-151117.zevtc","20210925-231438.zevtc","20210925-211843.zevtc","20210925-212050.zevtc","20210925-212159.zevtc","20210925-212412.zevtc","20210925-213045.zevtc","20210925-214206.zevtc","20210925-155642.zevtc","20210925-220738.zevtc","20210925-221435.zevtc","20210925-221841.zevtc","20210925-222351.zevtc","20210925-223117.zevtc","20210925-164828.zevtc","20210925-164940.zevtc","20210925-225014.zevtc","20210925-225131.zevtc","20210925-165201.zevtc","20210925-165311.zevtc","20210925-225250.zevtc","20210925-165641.zevtc","20210925-165630.zevtc","20210925-230233.zevtc","20210925-170711.zevtc","20210925-171234.zevtc","20210925-231126.zevtc","20210925-231315.zevtc","20210925-231508.zevtc","20210925-232022.zevtc","20210925-172139.zevtc","20210925-172420.zevtc","20210925-232435.zevtc","20210925-232830.zevtc","20210925-172915.zevtc","20210925-232943.zevtc","20210925-173122.zevtc","20210925-233241.zevtc","20210925-233433.zevtc","20210925-173523.zevtc","20210925-174204.zevtc","20210925-234305.zevtc","20210925-234450.zevtc","20210925-174621.zevtc","20210925-235133.zevtc","20210925-092331.zevtc","20210925-092929.zevtc","20210925-183547.zevtc","20210925-184120.zevtc","20210925-184358.zevtc","20210925-094413.zevtc","20210925-094946.zevtc","20210925-174937.zevtc","20210925-022406.zevtc","20210925-185356.zevtc","20210925-095436.zevtc","20210925-100042.zevtc","20210925-100437.zevtc","20210925-101037.zevtc","20210925-200115.zevtc","20210925-200656.zevtc","20210925-200956.zevtc","20210925-201706.zevtc","20210925-202739.zevtc","20210925-202844.zevtc","20210925-203222.zevtc","20210925-203610.zevtc","20210925-203725.zevtc","20210925-203904.zevtc","20210925-204156.zevtc","20210925-204615.zevtc","20210925-204617.zevtc","20210925-205420.zevtc","20210925-210340.zevtc","20210925-211040.zevtc","20210925-211829.zevtc","20210925-221841.zevtc","20210925-222400.zevtc","20210925-212548.zevtc","20210925-213047.zevtc","20210925-223143.zevtc","20210925-213317.zevtc","20210925-213448.zevtc","20210925-223547.zevtc","20210925-223925.zevtc","20210925-225548.zevtc","20210925-230344.zevtc","20210925-230846.zevtc","20210925-231532.zevtc","20210925-221815.zevtc","20210925-232015.zevtc","20210925-232110.zevtc","20210925-232346.zevtc","20210925-222506.zevtc","20210925-232757.zevtc","20210925-233044.zevtc","20210925-233149.zevtc","20210925-233307.zevtc","20210925-223653.zevtc","20210925-233631.zevtc","20210925-234312.zevtc","20210925-234300.zevtc","20210925-224458.zevtc","20210925-234856.zevtc","20210925-225533.zevtc","20210925-235433.zevtc","20210925-230204.zevtc","20210926-003401.zevtc","20210923-194927.zevtc","20210923-195356.zevtc","20210923-195829.zevtc","20210923-201003.zevtc","20210923-202557.zevtc","20210923-203318.zevtc","20210923-205646.zevtc","20210923-210346.zevtc","20210926-011451.zevtc","20210926-011814.zevtc","20210926-012446.zevtc","20210926-012851.zevtc","20210926-025745.zevtc","20210926-120952.zevtc","20210926-121922.zevtc","20210926-122842.zevtc","20210926-113950.zevtc","20210926-124630.zevtc","20210926-124818.zevtc","20210926-125008.zevtc","20210926-125953.zevtc","20210926-002003.zevtc","20210926-002331.zevtc","20210926-003111.zevtc","20210926-003434.zevtc","20210926-003958.zevtc","20210926-004418.zevtc","20210925-114310.zevtc","20210925-114853.zevtc","20210925-115319.zevtc","20210925-120800.zevtc","20210924-173306.zevtc","20210924-174530.zevtc","20210924-175444.zevtc","20210923-210858.zevtc","20210923-211210.zevtc","20210923-213929.zevtc","20210923-210001.zevtc","20210923-210711.zevtc","20210923-211112.zevtc","20210925-030719.zevtc","20210925-031117.zevtc","20210925-031444.zevtc","20210925-031904.zevtc","20210925-032340.zevtc","20210925-032818.zevtc","20210925-033142.zevtc","20210925-033455.zevtc","20210925-034036.zevtc","20210925-034332.zevtc","20210924-172727.zevtc","20210924-173052.zevtc","20210924-173423.zevtc","20210924-173755.zevtc","20210924-174224.zevtc","20210924-174343.zevtc","20210924-174634.zevtc","20210922-231233.zevtc","20210922-232146.zevtc","20210922-232521.zevtc","20210922-233050.zevtc","20210923-003930.zevtc","20210923-122404.zevtc","20210923-120922.zevtc","20210923-121453.zevtc","20210923-121941.zevtc","20210923-122257.zevtc","20210923-122704.zevtc","20210923-123627.zevtc","20210923-124054.zevtc","20210923-124521.zevtc","20210923-125209.zevtc","20210923-125914.zevtc","20210923-130316.zevtc","20210923-130725.zevtc","20210923-081156.zevtc","20210923-131409.zevtc","20210923-131742.zevtc","20210923-132815.zevtc","20210923-134158.zevtc","20210923-134510.zevtc","20210923-135057.zevtc","20210923-135418.zevtc","20210923-135649.zevtc","20210923-140741.zevtc","20210923-144220.zevtc","20210923-144651.zevtc","20210923-144956.zevtc","20210923-145332.zevtc","20210923-145613.zevtc","20210923-150228.zevtc","20210923-150633.zevtc","20210923-150946.zevtc","20210923-151223.zevtc","20210923-151651.zevtc","20210923-152131.zevtc","20210923-102330.zevtc","20210923-152527.zevtc","20210923-102821.zevtc","20210923-152900.zevtc","20210923-153141.zevtc","20210923-153922.zevtc","20210923-154312.zevtc","20210923-154629.zevtc","20210923-155004.zevtc","20210923-105227.zevtc","20210923-155500.zevtc","20210923-160109.zevtc","20210923-160559.zevtc","20210923-160917.zevtc","20210923-161617.zevtc","20210923-162005.zevtc","20210923-162402.zevtc","20210923-162713.zevtc","20210923-163205.zevtc","20210923-163541.zevtc","20210923-163835.zevtc","20210923-164104.zevtc","20210923-164636.zevtc","20210923-165008.zevtc","20210923-170015.zevtc","20210923-170300.zevtc","20210923-170546.zevtc","20210923-170858.zevtc","20210923-172927.zevtc","20210923-173157.zevtc","20210923-174346.zevtc","20210923-180436.zevtc","20210923-190510.zevtc","20210923-180727.zevtc","20210923-181241.zevtc","20210923-181816.zevtc","20210923-182059.zevtc","20210923-182333.zevtc","20210923-183226.zevtc","20210923-183648.zevtc","20210923-184027.zevtc","20210923-184400.zevtc","20210923-184828.zevtc","20210923-185239.zevtc","20210923-190007.zevtc","20210923-193040.zevtc","20210923-213417.zevtc","20210923-220324.zevtc","20210923-223853.zevtc","20210923-154209.zevtc","20210923-161335.zevtc","20210923-161752.zevtc","20210923-165137.zevtc","20210923-181531.zevtc","20210923-181900.zevtc","20210923-182205.zevtc","20210924-013323.zevtc","20210923-174907.zevtc","20210923-175156.zevtc","20210924-184538.zevtc","20210924-192653.zevtc","20210924-201626.zevtc","20210924-152701.zevtc","20210924-153529.zevtc","20210924-183035.zevtc","20210925-001037.zevtc","20210925-002354.zevtc","20210925-002959.zevtc","20210925-003424.zevtc","20210925-113154.zevtc","20210924-130525.zevtc","20210924-130758.zevtc","20210924-131337.zevtc","20210924-131648.zevtc","20210924-132302.zevtc","20210924-132649.zevtc","20210924-132942.zevtc","20210924-133546.zevtc","20210924-133911.zevtc","20210924-134445.zevtc","20210924-134711.zevtc","20210924-134943.zevtc","20210924-135241.zevtc","20210924-135529.zevtc","20210924-135912.zevtc","20210924-140539.zevtc","20210924-141017.zevtc","20210924-141344.zevtc","20210924-141629.zevtc","20210924-142810.zevtc","20210924-143044.zevtc","20210924-150410.zevtc","20210924-150818.zevtc","20210924-151146.zevtc","20210924-151514.zevtc","20210924-151825.zevtc","20210924-152054.zevtc","20210924-152341.zevtc","20210924-152608.zevtc","20210924-152851.zevtc","20210924-153741.zevtc","20210924-154118.zevtc","20210924-155009.zevtc","20210924-155244.zevtc","20210924-160037.zevtc","20210924-160314.zevtc","20210924-160838.zevtc","20210924-161452.zevtc","20210924-161728.zevtc","20210924-163336.zevtc","20210924-164248.zevtc","20210924-194130.zevtc","20210924-195202.zevtc","20210924-195445.zevtc","20210924-200210.zevtc","20210924-210506.zevtc","20210924-210747.zevtc","20210924-211025.zevtc","20210924-211721.zevtc","20210924-212029.zevtc","20210924-212501.zevtc","20210924-212822.zevtc","20210924-213233.zevtc","20210924-213517.zevtc","20210924-214321.zevtc","20210924-214657.zevtc","20210924-215246.zevtc","20210924-220159.zevtc","20210924-220619.zevtc","20210924-221014.zevtc","20210924-221431.zevtc","20210924-221750.zevtc","20210924-223118.zevtc","20210924-223437.zevtc","20210924-224323.zevtc","20210924-230621.zevtc","20210925-133716.zevtc","20210925-134135.zevtc","20210925-134542.zevtc","20210925-135124.zevtc","20210925-135403.zevtc","20210925-135739.zevtc","20210925-140153.zevtc","20210925-140533.zevtc","20210925-140914.zevtc","20210925-141930.zevtc","20210925-142159.zevtc","20210925-142828.zevtc","20210925-143100.zevtc","20210923-130750.zevtc","20210923-131047.zevtc","20210923-131303.zevtc","20210923-131730.zevtc","20210923-132047.zevtc","20210923-145157.zevtc","20210923-150425.zevtc","20210923-150701.zevtc","20210924-004229.zevtc","20210924-004635.zevtc","20210924-005138.zevtc","20210925-171432.zevtc","20210925-171825.zevtc","20210925-172534.zevtc","20210925-173017.zevtc","20210925-173310.zevtc","20210924-183855.zevtc","20210925-214744.zevtc","20210925-215217.zevtc","20210925-215511.zevtc","20210925-215949.zevtc","20210925-220358.zevtc","20210925-220741.zevtc","20210925-192948.zevtc"]:
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
    fileTimes = [x for _,x in sorted(zip(fileTimes,fileTimes))]

    # upload new logs #
    if len(filesToUpload) > 0:
        if verbose:
            print("Checking " + str(len(filesToUpload)) + " new logs.")
        tryNotification("Checking " + str(len(filesToUpload)) + " new logs.")
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
        tryNotification("Finished uploading.\r\n" + str(filesUploaded) + " new logs submitted.\r\n" + str(filesFailed) + " duplicates omitted.")
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
                global notificationString
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