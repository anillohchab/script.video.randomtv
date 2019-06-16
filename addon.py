import xbmc
import xbmcgui
import xbmcaddon
import json
import random
import threading
import sys
import time


def log(msg):
	xbmc.log("%s: %s" % (name,msg),level=xbmc.LOGDEBUG )


def buildPlaylist(myEpisodes):
	# Clear Playlist
	myPlaylist.clear()
	addPlaylist(myEpisodes)

def addPlaylist(myEpisodes):
	for myEpisode in myEpisodes:
		log("Added Episode to Playlist: " + str(myEpisode['episodeId']) + " -- " + myEpisode['episodeShow'] + " - " + myEpisode['episodeName'])
		episodesInPlaylist.append(myEpisode)	
		myPlaylist.add(url=myEpisode['episodeFile'])	


def ResetPlayCount(myEpisode):
	xbmc.Monitor().waitForAbort(5)
	log("--------- ResetPlayCount")
	log("-- Episode Id: " + str(myEpisode['episodeId']))
	log("-- Episode Name: " + str(myEpisode['episodeName']))
	log("-- Last Played: " + myEpisode['lastPlayed'])
	log("-- Play Count: " + str(myEpisode['playCount']))
	log("-- Resume Position: " + str(myEpisode['resume']['position']))
	log("-- Resume Total: " + str(myEpisode['resume']['total']))
	command = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": { "episodeid": %d, "lastplayed": "%s", "playcount": %d, "resume": { "position": %d, "total": %d } }, "id": 1}' % (myEpisode['episodeId'], myEpisode['lastPlayed'], myEpisode['playCount'], myEpisode['resume']['position'], myEpisode['resume']['total'])
	response = json.loads(xbmc.executeJSONRPC(command))
	log("-- " + str(response))

def randomIndexWithWeight(tvShowIds, weights):
	log("-- tvShowIds: " + str(tvShowIds))
	log("-- weights: " + str(weights))
	sumOfWeights = 0
	for tvShowId in tvShowIds:
		sumOfWeights += weights.get(tvShowId, 1)
	rnd = random.randrange(sumOfWeights)
	for tvShowId in tvShowIds:
		if (rnd < weights.get(tvShowId, 1)):
			return tvShowId
		rnd -= weights.get(tvShowId, 1)
	return 0

def randomEpisodes(limit=5, tvShowEpisodes={}, tvShowIds=[], tvShowWeights={}):
	randomlySelectedExpisodes = []
	for i in range(limit):
		tvShowId = randomIndexWithWeight(tvShowIds, tvShowWeights)
		log("tvselected tvShowId=" + str(tvShowId))

		if tvShowEpisodes[tvShowId]['result']['limits']['total'] <= 0:
			i -= 1
			continue

		episodes = tvShowEpisodes[tvShowId]['result']['episodes']
		episode = episodes[random.randrange(len(episodes))]
		if addon.getSetting("IncludeUnwatched") != "true" and episode['playcount'] <= 0:
			i -= 1
			continue

		randomlySelectedExpisodes.append({'episodeId': episode['episodeid'], 'episodeShow': episode['showtitle'].encode('utf-8').strip(), 'episodeName': episode['label'].encode('utf-8').strip(), 'episodeFile': episode['file'].encode('utf-8').strip(), 'playCount': episode['playcount'], 'lastPlayed': episode['lastplayed'], 'resume': episode['resume']})	

		log("randomlySelectedExpisodes=" + str(randomlySelectedExpisodes))

	return randomlySelectedExpisodes	
  
class MyPlayer(xbmc.Player):
	def __init__(self, *args):
		xbmc.Player.__init__(self, *args)
		self.mediaStarted = False
		self.mediaEnded = False
		self.scriptStopped = False
		log("============================================================= INIT")

	def onPlayBackStarted(self):
		self.mediaStarted = True
		log("============================================================= START")

	def onPlayBackEnded(self):
		self.mediaEnded = True
		log("============================================================= END")

	def onPlayBackStopped(self):
		self.scriptStopped = True
		log("============================================================= STOP")
#


# Set some variables
addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo("id")
name = addon.getAddonInfo("name")
icon = addon.getAddonInfo("icon")

busyDiag = xbmcgui.DialogBusy()
myEpisodes = []
episodesInPlaylist = []

includedShows = addon.getSetting("includedShows")

# Some new settings
playlistSizeLimit = 5

log("setting showProbablitiesjson " + addon.getSetting("showProbablities"))
showProbablities = {}
try:
	# Keys inside a json is always a string so converting them to string.
	# We know it must be int so, if it fails resetting it back.
	showProbablitiesJson = json.loads(addon.getSetting("showProbablities"))
	for showIdStr in showProbablitiesJson:
		showProbablities[int(showIdStr)] = showProbablitiesJson[showIdStr]
except:
	log("Failed to parse show probablities, resetting them to default")
	showProbablities = {}

log("read setting for showProbablities=" + str(showProbablities))

# Select Shows Settings Dialog
if len(sys.argv) > 1:
	if sys.argv[1] == "SelectShows":		
		log("--------- Settings - SelectShows")
		busyDiag.create()
		listShows = []
		listPreSelect = []
		listPostSelect = []
		command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"sort": {"ignorearticle": true, "method": "label", "order": "ascending"}}, "id": 1}'
		allShows = json.loads(xbmc.executeJSONRPC(command))
		if allShows['result']['limits']['total'] > 0:
			for show in allShows['result']['tvshows']:
				listShows.append(show['label'])
				
				if not includedShows == "":
					if show['tvshowid'] in map(int, includedShows.split(", ")):
						listPreSelect.append(len(listShows) - 1)

			
		busyDiag.close()
		selectedShows = xbmcgui.Dialog().multiselect(addon.getLocalizedString(32012), listShows, preselect=listPreSelect)

		
		if not selectedShows is None:
			for selectedShow in selectedShows:
				listPostSelect.append(allShows['result']['tvshows'][selectedShow]['tvshowid'])
			
			includedShows = ", ".join(str(i) for i in listPostSelect)
			addon.setSetting("includedShows", includedShows)

		xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonid)
		xbmc.executebuiltin('SetFocus(201)')
	elif sys.argv[1] == "ModifyShowsProbability":		
		log("--------- Settings - ModifyShowsProbability")
		log("start showProbablities=" + str(showProbablities))
		tvShowIds = []

		busyDiag.create()
		if addon.getSetting("IncludeAll") == "true":
			command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "id": 1}'
			allShowIds = json.loads(xbmc.executeJSONRPC(command))
	
			if allShowIds['result']['limits']['total'] > 0:
				for show in allShowIds['result']['tvshows']:
					tvshows.append(int(show['tvshowid']))		
		else:
			for includedShow in map(int, includedShows.split(", ")):
				tvShowIds.append(includedShow)	
		
		selectedShowTitleItems = []
		for tvShowId in tvShowIds:
			# command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "properties": ["showtitle", "file", "playcount", "lastplayed", "resume"] }, "id": 1}' % tvShowId
			command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": %d}, "id": 1}'  % tvShowId

			currentShowDetails = json.loads(xbmc.executeJSONRPC(command))
			currentShowLabel = currentShowDetails['result']['tvshowdetails']['label']
			selectedShowTitleItems.append(xbmcgui.ListItem(currentShowLabel + " : " +  str(showProbablities.get(tvShowId, 1)), currentShowLabel))
		busyDiag.close()

		perShowProbablity = []				
		while True:
			selectedShow = xbmcgui.Dialog().select("Select A Show", selectedShowTitleItems)
			if selectedShow == -1:
				break			
			tvShowId = tvShowIds[selectedShow]
			selectedProbablity = int(xbmcgui.Dialog().numeric(0, "Select a number", str(showProbablities.get(tvShowId, 1))))
			showTitleItem = selectedShowTitleItems[selectedShow]
			showTitleItem.setLabel(showTitleItem.getLabel2() + " : " + str(selectedProbablity))

			showProbablities[tvShowId] = selectedProbablity
		
		log("end showProbablities=" + str(showProbablities))
		addon.setSetting("showProbablities", json.dumps(showProbablities))
	quit()
#


# Display Starting Notification
if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, addon.getLocalizedString(32007), 2000, icon))
log("-------------------------------------------------------------------------")
log("Starting")
busyDiag.create()
backWindow = xbmcgui.Window()
backWindow.show()

tvShowIds = []
tvShowEpisodes = {}

# Get TV Episodes
if addon.getSetting("IncludeAll") == "true":
	command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "id": 1}'
	allShowIds = json.loads(xbmc.executeJSONRPC(command))
	
	if allShows['result']['limits']['total'] > 0:
		for show in allShows['result']['tvshows']:
			tvShowIds.append(int(show['tvshowid']))
else:
	for includedShow in map(int, includedShows.split(", ")):
		tvShowIds.append(includedShow)


for tvShowId in tvShowIds:
		command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "properties": ["showtitle", "file", "playcount", "lastplayed", "resume"] }, "id": 1}' % tvShowId
		allEpisodes = json.loads(xbmc.executeJSONRPC(command))
			
		if allEpisodes['result']['limits']['total'] > 0:
			tvShowEpisodes[tvShowId] = allEpisodes		

myEpisodes.extend(randomEpisodes(playlistSizeLimit, tvShowEpisodes, tvShowIds, showProbablities))

log("Total Episodes: " + str(len(myEpisodes)))


# If no episodes, display notification and quit
if len(myEpisodes) == 0:
	log("--------- No episodes")
	xbmcgui.Dialog().ok(name, addon.getLocalizedString(32008), addon.getLocalizedString(32009))
	xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonid)
	quit()
else:
	log("--------- Episodes Found")
	# Get Auto Stop Check Time - Current Time + Auto Stop Check Timer
	if addon.getSetting("AutoStop") == "true":
		log("-- Auto Stop Enabled")
		log("-- Auto Stop Timer: " + addon.getSetting("AutoStopTimer"))
		log("-- Auto Stop Wait: " + addon.getSetting("AutoStopWait"))
		AutoStopCheckTime = int(time.time()) + (int(addon.getSetting("AutoStopTimer")) * 60)
		AutoStopWait = (int(addon.getSetting("AutoStopWait")) * 60)
		AutoStopDialog = xbmcgui.DialogProgress()
	#

	# Initialize our Player
	player = MyPlayer()
	
	# Create Playlist
	myPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

	# Shuffle Episodes
	random.shuffle(myEpisodes)
	
	# Build Playlist
	buildPlaylist(myEpisodes)

	# Start Player
	player.play(item=myPlaylist)
#


while (not xbmc.Monitor().waitForAbort(1)):
	if addon.getSetting("AutoStop") == "true":
		if int(time.time()) >= AutoStopCheckTime:
			log("-- Auto Stop Timer Reached")
			AutoStopDialog.create(name, addon.getLocalizedString(32015))
			while int(time.time()) < AutoStopCheckTime + AutoStopWait:
				AutoStopDialog.update(int(int(time.time() - AutoStopCheckTime) * 100 / AutoStopWait), addon.getLocalizedString(32015), str(AutoStopWait - int(time.time() - AutoStopCheckTime)) + " " + addon.getLocalizedString(32016))
				if AutoStopDialog.iscanceled():
					log("-- Dialog Cancelled - Breaking")
					break
				#
				xbmc.Monitor().waitForAbort(0.1)
			#
			if AutoStopDialog.iscanceled():
				log("-- Dialog Cancelled")
				AutoStopCheckTime = int(time.time()) + (int(addon.getSetting("AutoStopTimer")) * 60)
			#
			else:
				log("-- Dialog Not Cancelled")
				xbmc.executebuiltin('PlayerControl(Stop)')
			#
			AutoStopDialog.close()
			xbmc.Monitor().waitForAbort(0.2)
		#
	#

	
	if player.mediaStarted:
		log("--------- mediaStarted")
		busyDiag.close()

		if 'lastEpisode' in locals():
			log("-- lastEpisode")
			if addon.getSetting("UpdatePlayCount") == "false":
				log("-- Start ResetPlayCount Thread")
				thread = threading.Thread(target=ResetPlayCount, args=(episodesInPlaylist[lastEpisode],))
				thread.start()
			#
		#

		showName = episodesInPlaylist[myPlaylist.getposition()]['episodeShow']
		episodeName = episodesInPlaylist[myPlaylist.getposition()]['episodeName']

		log("-- Started: " + showName + " - " + episodeName)
		if addon.getSetting("ShowNotifications") == "true": 
			xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, showName + "\r\n" + episodeName, 5000, icon))
		
		log("-- Playlist Position: " + str(myPlaylist.getposition()))


		if myPlaylist.size() - myPlaylist.getposition() <= 2:
			log("-- Playlist about to end, lets backfil")
			itemsToBackfil = playlistSizeLimit - (myPlaylist.size() - myPlaylist.getposition())
			addPlaylist(randomEpisodes(itemsToBackfil, tvShowEpisodes, tvShowIds))
			log("-- Playlist backfilled, size=" + str(myPlaylist.size()))
			log("-- current episodesInPlaylist=" + str(episodesInPlaylist))
		
		lastEpisode = myPlaylist.getposition()
		player.mediaStarted = False

	#


	if player.mediaEnded:
		log("--------- mediaEnded")
		log("-- Playlist Position: " + str(myPlaylist.getposition()))
		
		if myPlaylist.getposition() < 0:
			log("-- Playlist Finished")
			if addon.getSetting("RepeatPlaylist") == "true":
				if addon.getSetting("ShuffleOnRepeat") == "true":
					busyDiag.create()
					log("-- Shuffling Playlist")
					if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, addon.getLocalizedString(32010), 5000, icon))
					random.shuffle(myEpisodes)
					buildPlaylist(myEpisodes)
				#

				log("-- Restarting Playlist")
				player.play(item=myPlaylist)
			else:
				player.scriptStopped = True
		elif myPlaylist.size() - myPlaylist.getposition() <= 2:
			log("-- Playlist about to end, lets backfil")
			itemsToBackfil = playlistSizeLimit - (myPlaylist.size() - myPlaylist.getposition())
			addPlaylist(randomEpisodes(itemsToBackfil, tvShowEpisodes, tvShowIds))
			log("-- Playlist backfilled")
		else:
			log("-- Playlist still going")
		#

		player.mediaEnded = False
	#


	if player.scriptStopped:
		log("--------- scriptStopped")
		if addon.getSetting("UpdatePlayCount") == "false" and 'lastEpisode' in locals():
			log("-- Start ResetPlayCount Thread")
			thread = threading.Thread(target=ResetPlayCount, args=(episodesInPlaylist[lastEpisode],))
			thread.start()
		break
	#
#


# Display Stopping Notification
if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, addon.getLocalizedString(32011), 2000, icon))
backWindow.close()
log("Stopping")
log("-------------------------------------------------------------------------")
