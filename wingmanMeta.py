from pymongo import MongoClient
import numpy as np
import json
import matplotlib
import matplotlib.pyplot as plt
# UPDATE ONCE DAILY OR SOMETHING? THEN ONLY READ RESULTS ON WEBPAGE

client = MongoClient('mongodb://ehmaccount:69wrz3KVCbPHs@nevermindcreations.de:27017')
db = client['gw2wingman']
metaCollection = db['metaResults']
bossStatsMeta = {}
outpath = "D:/EVTC/Meta/"
bosses = {15438: "Vale Guardian", 15429: "Gorseval", 15375: "Sabetha the Saboteur", 16123: "Slothasor",
            16115: "Matthias Gabrel", 16235: "Keep Construct", 16246: "Xera", 17194: "Cairn the Indomitable",
            17172: "Mursaat Overseer", 17188: "Samarog", 17154: "Deimos", 19767: "Soulless Horror", 19450: "Dhuum",
            43974: "Conjured Amalgamate", 21105: "Twin Largos", 20934: "Qadim", 22006: "Cardinal Adina",
            21964: "Cardinal Sabir", 22000: "Qadim the Peerless", 16088: "Bandit Trio", 16247: "Twisted Castle",
            19828: "River of Souls", 19691: "Broken King", 19536: "Soul Eater", 19651: "Eyes", 17021: "M A M A",
            17028: "Siax the Corrupted", 16948: "Ensolyss of the Endless Torment", 17632: "Skorvald the Shattered",
            17949: "Artsariiv", 17759: "Arkk", 23254: "Ai, Keeper of the Peak",
            22154: "Icebrood Construct", 22343: "The Voice and The Claw", 22492:"Fraenir of Jormag",
            22436: "Fraenir Construct", 22521: "Boneskinner", 22711: "Whisper of Jormag", 22836: "Varinia Stormsounder",
            21333: "Freezie"}

metaResults = metaCollection.find_one()

successRates = {}
averageDps = {}

for bossEntry in metaResults['entries']:
    # SUCCESS RATE
    fig1, ax1 = plt.subplots()
    ax1.pie([int(bossEntry["kills"]), int(bossEntry['fails'])], explode=(0, 0.05), startangle=90, colors=["#31d42b", "#fa8c05"])
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.savefig(outpath + "Figures/" + str(bossEntry['triggerID']) + "_successPieChart")
    successRates.update({bossEntry['triggerID']: np.round(100*bossEntry["kills"]/(bossEntry["kills"]+bossEntry["fails"]),2)})
    plt.close()

# sort dicts
successRates = dict(sorted(successRates.items(), key=lambda item: item[1]))

print("Sorted by success rate:")
for triggerID in successRates.keys():
    print(str(successRates[triggerID]) + "%: [" + str(triggerID) + "] " + bosses[triggerID])

client.close()