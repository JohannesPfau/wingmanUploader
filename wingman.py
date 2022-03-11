from pymongo import MongoClient
import numpy as np
import json
from wingmanUtils import msToStr, strToMs, trimJson, getSearchDict, getPlayerCountFor, boons
# UPDATE ONCE DAILY OR SOMETHING? THEN ONLY READ RESULTS ON WEBPAGE

client = MongoClient('mongodb://ehmaccount:69wrz3KVCbPHs@nevermindcreations.de:27017')
db = client['gw2wingman']
logsCollection = db['logs']
bossStatsMeta = {"entries": []}
outpath = "D:/EVTC/"

# I/O Config:
onlyKills = True
onlyFails = False
includeAccounts = []  #['Mikahil.8596']
excludeAccounts = []
includeBoonuptimes = {}  #{'1187': 50}  # e.g. {'1187': 90} => Over 90% Quickness
noDeaths = False
noDownstates = False
onlyCM = False
displaySuccessRate = True
displayDurations = True
displayIncDmg = True
displayDps = True
displayRecordDps = True
displayBoonUptimes = True

# from https://dps.report/docs/bossIds.txt :
bosses = {15438: "Vale Guardian", 15429: "Gorseval", 15375: "Sabetha the Saboteur", 16123: "Slothasor",
            16115: "Matthias Gabrel", 16235: "Keep Construct", 16246: "Xera", 17194: "Cairn the Indomitable",
            17172: "Mursaat Overseer", 17188: "Samarog", 17154: "Deimos", 19767: "Soulless Horror", 19450: "Dhuum",
            43974: "Conjured Amalgamate", 21105: "Twin Largos", 20934: "Qadim", 22006: "Cardinal Adina",
            21964: "Cardinal Sabir", 22000: "Qadim the Peerless", 16088: "Bandit Trio", 16247: "Twisted Castle",
            19828: "River of Souls", 19691: "Broken King", 19536: "Soul Eater", 19651: "Eyes", 17021: "M A M A",
            17028: "Siax the Corrupted", 16948: "Ensolyss of the Endless Torment", 17632: "Skorvald the Shattered",
            17949: "Artsariiv", 17759: "Arkk", 23254: "Ai, Keeper of the Peak",
            22154: "Icebrood Construct", 22343: "The Voice and The Claw", 22492: "Fraenir of Jormag",
            22436: "Fraenir Construct", 22521: "Boneskinner", 22711: "Whisper of Jormag", 22836: "Varinia Stormsounder",
            21333: "Freezie"}

bosses = {15438: "Vale Guardian"}

bossStatsMeta.update({"onlyKills": onlyKills})
bossStatsMeta.update({"onlyFails": onlyFails})

for bossID in bosses.keys():
    # get avg stats of all tries/kills/fails of one boss
    search = getSearchDict(bossID, includeAccounts, excludeAccounts, onlyKills, onlyFails, noDeaths, noDownstates, includeBoonuptimes, onlyCM)

    # SUCCESS_RATE
    kills = logsCollection.count_documents(getSearchDict(bossID, includeAccounts, excludeAccounts, True, False, noDeaths, noDownstates, includeBoonuptimes, onlyCM))
    fails = logsCollection.count_documents(getSearchDict(bossID, includeAccounts, excludeAccounts, False, True, noDeaths, noDownstates, includeBoonuptimes, onlyCM))
    if kills+fails == 0:
        print("No records for " + str(bossID) + " (" + bosses[bossID] + ")")
        continue

    resultLogs = []
    alldps = []
    durations = []
    recordDuration = np.inf
    worstDuration = 0
    highestIncDps = 0
    lowestIncDps = np.inf
    incDamageArray = []
    downstates = []
    downtimes = []
    deaths = []
    deadtimes = []
    allProfessionsDps = {}
    damageProfessionsDps = {}
    bestPlayerDps = 0
    bestClassDps = {}
    bestClassDpsInfo = {}
    bossStats = {}

    print(">>> Parsing " + str(kills+fails) + " logs of boss " + str(bossID) + " (" + bosses[bossID] + ") <<<")
    if displaySuccessRate:
        print("success rate: " + str(np.round(100 * kills / (kills+fails), 2)) + "%")
    if onlyKills and kills == 0:
        continue
    for log in logsCollection.find(search):
        resultLogs.append(log)
        # DURATION
        duration = strToMs(log['duration'])
        durations.append(duration)
        if duration < recordDuration:
            recordDuration = duration
            recordLog = log
        if duration > worstDuration:
            worstDuration = duration
            worstLog = log
        # INC DAMAGE
        totalDamageInc = 0
        totalDownstates = 0
        totalDowntime = 0
        totalDead = 0
        totalDeadDuration = 0
        for player in log['players']:
            totalDamageInc += player['damageTaken']
            totalDownstates += player['downCount']
            totalDowntime += player['downDuration']
            totalDead += player['deadCount']
            totalDeadDuration += player['deadDuration']
        downstates.append(totalDownstates)
        downtimes.append(totalDowntime)
        deaths.append(totalDead)
        deadtimes.append(totalDeadDuration)
        totalDpsInc = totalDamageInc * 1000 / duration
        if totalDpsInc > highestIncDps:
            highestIncDps = totalDpsInc
            highestIncDamageLog = log
        if totalDpsInc < lowestIncDps:
            lowestIncDps = totalDpsInc
            lowestIncDamageLog = log
        incDamageArray.append(totalDamageInc)
        # DPS
        i = 0
        j = 0
        overallDps = 0
        overallDamageClassesDps = 0
        for player in log['players']:
            playerClass = player['profession']
            targetDps = player['dps']
            targetPDPS = player['powerDps']
            targetCDPS = player['condiDps']
            breakbarDamage = player['breakbarDamage']
            if not player['isSupport']:
                if not damageProfessionsDps.__contains__(playerClass):
                    damageProfessionsDps.update({playerClass : []})
                damageProfessionsDps[playerClass].append(targetDps)
                overallDamageClassesDps += targetDps
                j += 1
            if not allProfessionsDps.__contains__(playerClass):
                allProfessionsDps.update({playerClass: []})
            allProfessionsDps[playerClass].append(targetDps)
            overallDps += targetDps
            i += 1
            # best player dps
            if targetDps > bestPlayerDps:
                bestPlayerDps = targetDps
                bestPlayerDpsInfo = player['profession'] + " " + player['name'] + "(" + player['account'] + "): " + log['html']
            # best class dps
            if not bestClassDps.__contains__(player['profession']) or bestClassDps[player['profession']] < targetDps:
                bestClassDps.update({player['profession']: targetDps})
                bestClassDpsInfo.update({player['profession']: player['profession'] + " " + player['name'] + "(" + player['account'] + "): " + log['html']})

        overallDps /= i
        overallDamageClassesDps /= j
        # DPS of particular classes
        classesDps = {}
        damageClassesDps = {}
        for playerClass in allProfessionsDps.keys():
            classesDps.update({ playerClass : np.average(allProfessionsDps[playerClass]) })
        for playerClass in damageProfessionsDps.keys():
            damageClassesDps.update({playerClass : np.average(damageProfessionsDps[playerClass])})

        # CLEAVE DPS
        todo = True

    # sort dicts
    bestClassDps = dict(reversed(sorted(bestClassDps.items(), key=lambda item: item[1])))
    classesDps = dict(reversed(sorted(classesDps.items(), key=lambda item: item[1])))
    damageClassesDps = dict(reversed(sorted(damageClassesDps.items(), key=lambda item: item[1])))

    if displayDurations:
        print("avg Duration: " + msToStr(np.average(durations)))  # + LINK to closest!
        print("record Duration: " + msToStr(recordDuration) + " : " + recordLog['html'])
        print("worst Duration: " + msToStr(worstDuration) + " : " + worstLog['html'])
    if displayIncDmg:
        print("avg inc. dmg: " + str(int(np.average(incDamageArray))))
        print("avg inc. dps per player: " + str(int(1000/getPlayerCountFor(bossID) * np.average(incDamageArray) / np.average(durations))))
        print("cleanest Log: " + str(np.round(lowestIncDps/getPlayerCountFor(bossID), 2)) + " inc dps pp: " + lowestIncDamageLog['html'])
        print("dirtiest Log: " + str(np.round(highestIncDps/getPlayerCountFor(bossID), 2)) + " inc dps pp: " + highestIncDamageLog['html'])
        print("avg downstates: " + str(np.round(np.average(downstates), 2)) + " (" + str(int(np.average(downtimes))) + "ms)")
        print("avg deaths: " + str(np.round(np.average(deaths), 2)) + " (" + str(int(np.average(deadtimes))) + "ms)")

    if displayDps:
        # AVG DAMAGE OF (OVERALL) PLAYERS, then sorted by class
        # filter: Exclude healers (Healing Power), Exclude Support (Concentration), Exclude Tanks (Toughness)
        print("overall avg dps: " + str(int(overallDps)))
        print("overall avg dps of dmg classes: " + str(int(overallDamageClassesDps)))
        print(">> Unfiltered avg class dps: ")
        for playerClass in classesDps.keys():
            print(playerClass + ": " + str(int(classesDps[playerClass])))
        print(">> Non-Supporter avg class dps: ")
        for playerClass in damageClassesDps.keys():
            print(playerClass + ": " + str(int(damageClassesDps[playerClass])))

    if displayRecordDps:
        # BEST dps Player from class X of all logs of boss y
        print(">> Record Player DPS: ")
        print("Overall: " + str(bestPlayerDps) + " " + bestPlayerDpsInfo)
        for playerClass in bestClassDps.keys():
            print(playerClass + ": " + str(int(bestClassDps[playerClass])) + " " + bestClassDpsInfo[playerClass])
        # => Power
        # => Condi

    # => Mechanic Triggers

    # => Most typical class constellation
    # ==> LINK: Closest to average log from that constellation

    # save analytics
    bossStats.update({"triggerID": bossID})
    bossStats.update({"kills": kills})
    bossStats.update({"fails": fails})
    bossStats.update({"durations": durations})
    bossStats.update({"recordDurationLog": recordLog['html']})
    bossStats.update({"worstDurationLog": worstLog['html']})
    bossStats.update({"incDamage": incDamageArray})
    bossStats.update({"cleanestLog": lowestIncDamageLog['html']})
    bossStats.update({"dirtiestLog": highestIncDamageLog['html']})
    bossStats.update({"downstates": downstates})
    bossStats.update({"downtimes": downtimes})
    bossStats.update({"deaths":deaths})
    bossStats.update({"deadtimes":deadtimes})
    bossStats.update({"classesDps":classesDps})
    bossStats.update({"damageClassesDps":damageClassesDps})
    bossStats.update({"recordDps":bestPlayerDps})
    bossStats.update({"recordDpsInfo": bestPlayerDpsInfo})
    bossStats.update({"recordClassDps": bestClassDps})
    bossStats.update({"recordClassDpsInfo": bestClassDpsInfo})
    bossStatsMeta['entries'].append(bossStats)

    # Additional page: Insert name/acc? to see how good you are (compared to avg/record). And see your progress over time

with open(outpath + "metaResults.json", 'w') as outfile:
    json.dump(bossStatsMeta, outfile)

# db['metaResults'].insert_one(bossStatsMeta)

client.close()