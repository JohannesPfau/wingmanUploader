import json
import datetime
from pymongo import MongoClient

def msToStr(duration):
    durM = int(duration / 60000)
    durS = int((duration - durM * 60000) / 1000)
    durMS = int(duration - durM * 60000 - durS * 1000)
    return str(durM) + "m " + str(durS) + "s " + str(durMS) + "ms"

def strToMs(durationStr):
    durationStrs = str(durationStr).split(" ")
    durationM = int(durationStrs[0].replace("m",""))
    durationS = int(durationStrs[1].replace("s", ""))
    durationMS = int(durationStrs[2].replace("ms", ""))
    return (durationM*60 + durationS) * 1000 + durationMS

def trimJson(jsonLog):
    shortLog = {}
    shortLog.update({"triggerID": jsonLog['triggerID']})
    shortLog.update({"timeStart": jsonLog['timeStartStd']})
    shortLog.update({"timeEnd": jsonLog['timeEndStd']})
    shortLog.update({"duration": jsonLog['duration']})
    shortLog.update({"success": jsonLog['success']})
    shortLog.update({"isCM": jsonLog['isCM']})
    #shortLog.update({"players": jsonLog['players']})
    shortPlayers = []
    boonUptimes = {}
    for boon in boons.keys():
        boonUptimes.update({str(boon): 0})
    for oriPlayer in jsonLog['players']:
        player = {}
        player.update({"account": oriPlayer['account']})
        player.update({"name": oriPlayer['name']})
        player.update({"profession": oriPlayer['profession']})
        player.update({"damageTaken": oriPlayer['defenses'][0]['damageTaken']})
        player.update({"downCount": oriPlayer['defenses'][0]['downCount']})
        player.update({"downDuration": oriPlayer['defenses'][0]['downDuration']})
        player.update({"deadCount": oriPlayer['defenses'][0]['deadCount']})
        player.update({"deadDuration": oriPlayer['defenses'][0]['deadDuration']})
        player.update({"dps": oriPlayer['dpsTargets'][0][0]['dps']})
        player.update({"powerDps": oriPlayer['dpsTargets'][0][0]['powerDps']})
        player.update({"condiDps": oriPlayer['dpsTargets'][0][0]['condiDps']})
        player.update({"breakbarDamage": oriPlayer['dpsTargets'][0][0]['breakbarDamage']})
        isSupport = 0
        if oriPlayer['concentration'] > 0 or oriPlayer['healing'] > 0 or oriPlayer['toughness'] > 0:
            isSupport = 1
        player.update({"isSupport": isSupport})
        for buff in oriPlayer['buffUptimes']:
            if boons.keys().__contains__(buff['id']):
                boonUptimes[str(buff['id'])] += buff['buffData'][0]['uptime'] / getPlayerCountFor(jsonLog['triggerID'])

        shortPlayers.append(player)

    shortLog.update({"players": shortPlayers})
    shortLog.update({"boonUptimes": boonUptimes})
    mechanics = {}
    if jsonLog.keys().__contains__('mechanics'):
        for mechanic in jsonLog['mechanics']:
            mechaName = str(mechanic['name']).replace(".","_").replace(" ", "_").replace("$","_")
            mechanics.update({mechaName: len(mechanic['mechanicsData'])})
        shortLog.update({"mechanics": mechanics})

    return shortLog

toleranceTimeWindow = 10  # +- seconds
def updateBusyTimes(log, db):
    playersBusy = db['playersBusy']

    startTime = datetime.datetime.strptime(log['timeStart'], "%Y-%m-%d %H:%M:%S %z").timestamp() - toleranceTimeWindow
    endTime = datetime.datetime.strptime(log['timeEnd'], "%Y-%m-%d %H:%M:%S %z").timestamp() + toleranceTimeWindow
    for player in log['players']:
        busyTimeEntry = playersBusy.find_one({"account": player['account']})
        if busyTimeEntry is None:
            busyTimeEntry = {"account": player['account']}
            busyTimeEntry.update({"startBusyTimes": []})
            busyTimeEntry.update({"endBusyTimes": []})
        else:
            playersBusy.delete_one({"account": player['account']})
        busyTimeEntry['startBusyTimes'].append(startTime)
        busyTimeEntry['endBusyTimes'].append(endTime)
        playersBusy.insert_one(busyTimeEntry)
    return

def checkIfBusy(log, db):
    playersBusy = db['playersBusy']

    startTime = datetime.datetime.strptime(log['timeStartStd'], "%Y-%m-%d %H:%M:%S %z").timestamp()
    for player in log['players']:
        search = {"account": player['account']}
        dbPlayer = playersBusy.find_one(search)
        if dbPlayer is not None:
            for i in range(0, len(dbPlayer['startBusyTimes'])):
                if dbPlayer['startBusyTimes'][i] <= startTime <= dbPlayer['endBusyTimes'][i]:
                    # print("player " + player['name'] + " is already included in a DB log to that time.")
                    return True
    return False

def getSearchDict(bossID, includeAccounts, excludeAccounts, onlyKills, onlyFails, noDeaths, noDownstates, includeBoonuptimes, onlyCM):
    search = {"$and": []}
    search['$and'].append({"triggerID": bossID})
    for account in includeAccounts:
        search['$and'].append({"players": {"$elemMatch": {"account": account}}})
    for account in excludeAccounts:
        search['$and'].append({"players": {"nin": {"account": account}}})
    if onlyKills:
        search['$and'].append({"success": True})
    if onlyFails:
        search['$and'].append({"success": False})
    if noDeaths:
        search['$and'].append({"players": {"$not": {"$elemMatch": {"deadCount": {"$gt": 0}}}}})
    if noDownstates:
        search['$and'].append({"players": {"$not": {"$elemMatch": {"downCount": {"$gt": 0}}}}})
    if includeBoonuptimes is not None and len(includeBoonuptimes.keys()) > 0:
        for boon in includeBoonuptimes.keys():
            search['$and'].append({"boonUptimes."+str(boon): {"$gte": includeBoonuptimes[boon]}})
    if onlyCM:
        search['$and'].append({"isCM": True})
    return search

def getPlayerCountFor(bossID):
    if bossID == 17021 or bossID == 17028 or bossID == 16948 or bossID == 17632 or bossID == 17949 or bossID == 17759 or bossID == 23254:
        return 5
    if golemIDs.__contains__(bossID):
        return 1
    return 10

boons = {873: "Retaliation", 1187: "Quickness", 719: "Swiftness", 717: "Protection", 740: "Might", 718: "Regeneration",
         725: "Fury", 26980: "Resistance", 30328: "Alacrity", 1122: "Stability", 743: "Aegis", 726: "Vigor"}
golemIDs = [16199, 19645, 19676, 16202, 16177, 16198]