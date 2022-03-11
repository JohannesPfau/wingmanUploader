import statistics
import os
import numpy as np
import scipy.stats
import time
import subprocess
from pymongo import MongoClient
from pymongo.errors import DocumentTooLarge, WriteError
from wingmanUtils import updateBusyTimes, checkIfBusy, trimJson
import json

path = "C:/Users/Jo/Documents/Guild Wars 2/addons/arcdps/arcdps.cbtlogs/"
outpath = "D:/EVTC/"
finalpath = "D:/wingman/wingman/static/logs/html/"
EIexe = "D:/GW2EI/GuildWars2EliteInsights.exe"
client = MongoClient('mongodb://ehmaccount:69wrz3KVCbPHs@nevermindcreations.de:27017')
db = client['gw2wingman']
logsCollection = db['logs']
skipFailGolems = True
golemIDs = [16199, 19645, 19676, 16202, 16177, 16198]
skipFilesOnHDD = False  # DONT USE THIS! Multiple players could produce a log at the same second
skipFilesInDB = True # Use THIS, also considers filesize
skipOldFiles = True
checkBusyDuplicates = True
totalFiles = 0
totalUpdates = 0

# ensure that outpath and finalpath exist
if not os.path.exists(outpath):
    os.makedirs(outpath)
if not os.path.exists(finalpath):
    os.makedirs(finalpath)

# reload blacklist
try:
    with open(outpath + "blacklist.json", 'r', encoding='utf-8') as blacklistFile:
        blacklist = json.load(blacklistFile)
except:
    blacklist = {"lastUpdate": 0, "excludeFiles": []}

for r, d, f in os.walk(path):
    for file in f:
        # write update to blacklist file
        with open(outpath + "blacklist.json", 'w') as outfile:
            json.dump(blacklist, outfile)

        args = r + "/" + file
        if not args.endswith(".zevtc") and not args.endswith(".evtc"):
            continue
        if skipOldFiles and os.path.getmtime(args) < blacklist['lastUpdate']:
            print("Skipping " + args + " (older than last update)")
            continue
        if blacklist['excludeFiles'].__contains__(file):
            print("Skipping " + args + " (blacklisted from previous trial)")
            continue
        totalFiles += 1
        filesize = os.stat(r+"/"+file).st_size
        if skipFilesOnHDD and len([filename for filename in os.listdir(outpath) if filename.startswith(file.split(".")[0])]) > 0:
            print("Skipping " + args + ", already exists in outpath.")
            continue
        if skipFilesOnHDD and len([filename for filename in os.listdir(finalpath) if filename.startswith(file.split(".")[0])]) > 0:
            print("Skipping " + args + ", already exists in finalpath.")
            continue
        DBfilter = {"$and": [{"file": file}, {"filesize": filesize}]}
        if skipFilesInDB and logsCollection.find_one(DBfilter) is not None:
            print("Skipping " + args + ", already exists in DB.")
            blacklist['excludeFiles'].append(file)
            continue

        # convert evtc into json+html
        print("Converting " + args)
        subprocess.run([EIexe, args])

        # process results
        resultFiles = [filename for filename in os.listdir(outpath) if filename.startswith(file.split(".")[0])]
        for rf in resultFiles:
            if rf.endswith(".log"):
                os.remove(outpath+rf)
            if rf.endswith(".json"):
                # upload json to mongoDB
                with open(outpath+rf, 'r', encoding='utf-8') as logFile:
                    try:
                        logJson = json.load(logFile)
                        htmlfile = rf.replace(".json",".html")
                        # check if fail golem
                        if skipFailGolems and golemIDs.__contains__(logJson['triggerID']) and logJson['success'] == False:
                            print("Skipping Fail Golem: " + outpath + rf)
                            blacklist['excludeFiles'].append(file)
                            os.remove(outpath + htmlfile)
                        else:
                            # check if duplicate log (from another recording player)
                            if checkBusyDuplicates and checkIfBusy(logJson, db):
                                print("FAIL: Log includes busy players: " + outpath + rf)
                                blacklist['excludeFiles'].append(file)
                                os.remove(outpath + htmlfile)
                            else:
                                shortLog = trimJson(logJson)
                                shortLog['html'] = rf.split(".")[0] + ".html"
                                shortLog['file'] = file
                                shortLog['filesize'] = filesize
                                try:
                                    logsCollection.insert_one(shortLog)
                                    updateBusyTimes(shortLog, db)
                                    totalUpdates += 1
                                    #with open(outpath + "trimmed/trimmed_" + rf, 'w') as outfile:
                                    #    json.dump(shortLog, outfile)
                                    # move html into finalpath
                                    os.rename(outpath+htmlfile,finalpath+htmlfile)

                                except (DocumentTooLarge):
                                    print("FAIL: Document too large: " + outpath + rf)
                                    blacklist['excludeFiles'].append(file)
                                    os.remove(outpath + htmlfile)
                    except OSError:
                        print("FAILED to parse: " + outpath + rf)
                        blacklist['excludeFiles'].append(file)
                        os.remove(outpath + htmlfile)
                # remove json afterwards
                os.remove(outpath + rf)
        if len(resultFiles) < 2:  # log + json
            print("... Conversion failed. Possibly fight too short (<2200ms)")
            blacklist['excludeFiles'].append(file)

client.close()
# write update to blacklist file
blacklist['lastUpdate'] = time.time()
with open(outpath + "blacklist.json", 'w') as outfile:
    json.dump(blacklist, outfile)

print("COMPLETE. Updated " + str(totalUpdates) + " logs, excluded " + str(totalFiles-totalUpdates) + " logs.")
