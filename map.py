#!/usr/bin/env python

# Offline Map Activity : http://wiki.laptop.org/go/User:Ndoiron/OfflineMap
# All code open-source under the MIT license
#
# based on Map Version 3
# Original Map code copyright (c) 2008, Media Modifications Ltd.

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import gtk
import gobject
import os
import threading
from threading import *
import time
import hippo
import shutil
import urllib
import random

from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.toolbutton import ToolButton
from sugar.activity import activity
from sugar.graphics import style

from filepicker import FilePicker

from constants import Constants
from webviewer import WebViewer
from server import Server
from logic import ServerLogic
from result import ServerResult
from instance import Instance
from constants import Constants
from model import Model
from tray import HTray
from photocanvas import PhotoCanvas
from p5 import P5
from gplay import Gplay
from gplay import PlayVideoWindow
import serialize
import utils
from button import SavedButton
from savedmap import SavedMap
import _camera

# sharing
import telepathy
from dbus.service import method, signal
from dbus.gobject_service import ExportedGObject
from sugar.graphics.alert import NotifyAlert
from sugar.presence import presenceservice
from sugar.presence.tubeconn import TubeConnection

SERVICE = "org.laptop.map"
IFACE = SERVICE
PATH = "/org/laptop/map"

imgWidth = 180
imgHeight = 135
webWidth = imgWidth*5
webHeight = imgHeight*4

class Map(activity.Activity):

	#temp values until they get assigned
	cometPort = 8889
	ajaxPort = 8890
	
	initLat = '42.9'
	initLng = '-71.0'
	initZoom = '6'

	popW = 500
	popH = 375
	popB = 5
	
	def __init__(self, handle):
		activity.Activity.__init__(self, handle)
		Instance(self)
		Constants(self)
		self.modify_bg( gtk.STATE_NORMAL, Constants.colorBg.gColor )
		gobject.idle_add(self._initme, None)

	def _initme( self, userdata=None ):
		self.basePath = activity.get_bundle_path()
		self.htmlPath = os.path.join(self.basePath, "mapviewer")
		self.libPath = "/home/olpc/Activities/OfflineMaps.activity/MapPack/"
		self.m = Model(self)
		self.cond = Condition()

		self.SAVING_SEARCH = False
		self.shownSave = None
		self.shownRecd = None
		#these get updated whenever we hear back from the server
		self.NOW_MAP_CENTER_LAT = self.__class__.initLat
		self.NOW_MAP_CENTER_LNG = self.__class__.initLng
		self.NOW_MAP_ZOOM = self.__class__.initZoom
		self.NOW_MAP_TAGS = ""

		#calc unique ports
		h = hash(Instance.instanceId)
		self.__class__.cometPort = 1024 + (h%32255) * 2
		self.__class__.ajaxPort = self.__class__.cometPort + 1

		#ui
		self.windowStack = []

		self.toolbox = activity.ActivityToolbox(self)
		self.set_toolbox(self.toolbox)
		self.searchToolbar = SearchToolbar(self)
		self.searchToolbar.connect("address-update", self._addressUpdateCb)
		self.searchToolbar.connect("zoom-in", self._zoomInCb)
		self.searchToolbar.connect("zoom-out", self._zoomOutCb)
		self.searchToolbar.connect("save-search", self._saveSearchCb)
		self.searchToolbar.connect("library-search", self._librarySearchCb)
		self.searchToolbar.connect("search-update", self._searchUpdateCb)
		self.searchToolbar.set_sensitive(False)
		self.toolbox.add_toolbar( Constants.istrSearch, self.searchToolbar )
		self.addToolbar = AddToolbar(self)
		self.toolbox.add_toolbar( Constants.istrAnnotate, self.addToolbar )
		self.addToolbar.connect("add-media", self._addMediaCb)
		self.addToolbar.connect("add-kml", self._addKMLCb)
		self.addToolbar.connect("add-info", self._addInfoCb)
		self.addToolbar.connect("delete-media", self._deleteMediaCb)
		self.addToolbar.connect("measure", self._measureCb)
		self.addToolbar.set_sensitive(False)
		self.firstSearch = True
		self.toolbox.set_current_toolbar(1)

		self.dlToolbar = dlToolbar(self)
		self.toolbox.add_toolbar( Constants.istrDownload, self.dlToolbar )
		self.dlToolbar.connect("panoramio", self._panoramioCb)
		self.dlToolbar.connect("local-wiki", self._localwikiCb)
		self.dlToolbar.connect("wikimapia",self._wikimapiaCb)

		self.toolbox.remove(self.toolbox._separator)
		#taken directly from toolbox.py b/c I don't know how to mod the hongry hippo
		separator = hippo.Canvas()
		box = hippo.CanvasBox(
					border_color=Constants.colorBg.get_int(),
					background_color=Constants.colorBg.get_int(),
					box_height=style.TOOLBOX_SEPARATOR_HEIGHT,
					border_bottom=style.LINE_WIDTH)
		separator.set_root(box)
		self.toolbox.separator = separator
		self.toolbox._notebook.set_property("can-focus", False)
		self.toolbox.show()

		#add components
		vbox = gtk.VBox()
		
		self.tray = HTray()
		self.tray.set_size_request(-1, 130)
		self.tray.connect("enter-notify-event", self._trayMouseCb)
		self.tray.viewport.connect("enter-notify-event", self._trayMouseCb)
		self.tray.viewport.traybar.connect("enter-notify-event", self._trayMouseCb)
		self.tray.scroll_left.connect("enter-notify-event", self._trayMouseCb)
		self.tray.scroll_right.connect("enter-notify-event", self._trayMouseCb)
		self.tray.scroll_left_event.connect("enter-notify-event", self._trayMouseCb)
		self.tray.scroll_right_event.connect("enter-notify-event", self._trayMouseCb)
		fakeTray = gtk.VBox()
		fakeTray.set_size_request(-1, 130)
		fakeTray.modify_bg( gtk.STATE_NORMAL, Constants.colorBg.gColor )
		fakeTrayEvent = gtk.EventBox()
		fakeTrayEvent.modify_bg( gtk.STATE_NORMAL, Constants.colorBg.gColor )
		fakeTrayEvent.set_size_request(-1, 130)
		fakeTrayEvent.add( fakeTray )
		self.trayBox = gtk.Notebook()
		self.trayBox.set_size_request(-1, 130)
		self.trayBox.set_show_tabs(False)
		#vbox.pack_start(self.trayBox, expand=False)
		self.trayBox.append_page(self.tray)
		self.trayBox.append_page(fakeTrayEvent)
		self.realTrayIndex = self.trayBox.page_num(self.tray)
		self.fakeTrayIndex = self.trayBox.page_num(fakeTrayEvent)
		self.trayBox.set_current_page(self.realTrayIndex)
		fakeTrayEvent.add_events(gtk.gdk.VISIBILITY_NOTIFY_MASK)
		fakeTrayEvent.connect_after("visibility-notify-event", self._fakeTrayVisibleNotifyCb)

		self.browseBox = gtk.VBox()
		self.browser = WebViewer()
		self.htmlScale = 1.43
		self.browser.set_size_request(int(webWidth*self.htmlScale), int(webHeight*self.htmlScale))
		self.browseBox.pack_start(self.browser, expand=False)
 		self.browseBox.set_size_request(int(webWidth*self.htmlScale), int(webHeight*self.htmlScale))
		vbox.pack_start(self.browseBox)
		#vbox.pack_start(self.trayBox, expand=False)

		#important to call these in this order to ensure they show up
		self.set_canvas(vbox)
		self.browser.show()

		#fire up the web engine, spiderman!
		self.cometLogic = ServerLogic(self)

		ajaxServer = ServerThread(self.__class__.ajaxPort, self.cometLogic)
		ajaxServer.start()

		cometServer = ServerThread(self.__class__.cometPort, self.cometLogic)
		cometServer.start()

		self.browser.load_uri("file://" + self.htmlPath + "/mapCenter.html?ajaxPort=" + str(self.__class__.ajaxPort) + "&cometPort=" + str(self.__class__.cometPort))

		self.loaded = True
		self.loadingWindow = gtk.Window()
		self.addToWindowStack( self.loadingWindow, self )
		self.loadingWindow.modify_bg( gtk.STATE_NORMAL, Constants.colorBlack.gColor )
		loadingVBox = gtk.VBox()
		self.loadingWindow.add(loadingVBox)

		loadingTopEventBox = gtk.EventBox()
		loadingTopEventBox.modify_bg( gtk.STATE_NORMAL, Constants.colorBlack.gColor )
		loadingVBox.pack_start(loadingTopEventBox, expand=True)

		self.loadingCanvas = PhotoCanvas()
		self.loadingCanvas.modify_bg( gtk.STATE_NORMAL, Constants.colorBlack.gColor )
		self.loadingCanvas.set_size_request( 1200, 600 )
		loadingVBox.pack_start(self.loadingCanvas, expand=True)

		loadingInfo = gtk.Label()
		loadingInfo.set_alignment( .5, 0 )
		loadingInfo.set_text( "<b><span foreground='white' size='xx-large'>" + Constants.istrConnecting + "</span></b>")
		loadingInfo.set_use_markup( True )
		loadingVBox.pack_start(loadingInfo, expand=False)

		loadingBotEventBox = gtk.EventBox()
		loadingBotEventBox.modify_bg( gtk.STATE_NORMAL, Constants.colorBlack.gColor )
		loadingVBox.pack_start(loadingBotEventBox, expand=True)
		self.loadingWindow.resize( gtk.gdk.screen_width(), gtk.gdk.screen_height()-(self.toolbox.allocation.height) )
		self.moveWinOffscreen(self.loadingWindow)

		self.popWindow = gtk.Window()
		self.addToWindowStack( self.popWindow, self.loadingWindow )
		self.popWindow.modify_bg( gtk.STATE_NORMAL, Constants.colorBlack.gColor )
		self.popWindow.resize( self.popW+(2*self.popB), self.popH+(2*self.popB) )
		self.popUpBg = PopUpP5()
		self.popWindow.add( self.popUpBg )
		self.moveWinOffscreen(self.popWindow)
		self.popWindow.show_all()

		self.mediaWindow = gtk.Window()
		self.addToWindowStack(self.mediaWindow, self.popWindow)
		#self.moveWinOffscreen(self.mediaWindow)
		self.mediaWindow.show_all()
		self.mediaWindow.hide()

		#self.infoWindow = gtk.Window()
		#self._fillInInfoWindow()
		#self.addToWindowStack(self.infoWindow, self.mediaWindow)
		#self.moveWinOffscreen(self.infoWindow)
		#self.infoWindow.hide()
		
		# GTK science form window, based on infoWindow
		#self.scienceWindow = gtk.Window()
		#self._fillInScienceWindow()
		#self.moveWinOffscreen(self.scienceWindow)
		#self.scienceWindow.show_all()

		#self.selectWindow = gtk.Window()
		#self.selectWindow.modify_bg( gtk.STATE_NORMAL, Constants.colorBlack.gColor )
		#self.addToWindowStack(self.selectWindow, self.infoWindow)
		#self.moveWinOffscreen(self.selectWindow)
		#self.selectWindow.hide()

		self.photoCanvas = PhotoCanvas()

		self.gplayWin = PlayVideoWindow( Constants.colorBlack.gColor )
		self.gplay = Gplay()
		self.gplay.window = self.gplayWin

		self.connect("destroy", self.destroy)
		self.TOOLBOX_SIZE_ALLOCATE_ID = self.toolbox.connect_after("size-allocate", self._sizeAllocateCb)
		self.show_all()

		# break loading screen
		self.loaded = True
		self.enableNavigation()

		# add sharing
		self.maptube = None # Shared session
		self.initiating = False
		self.pservice = presenceservice.get_instance()
		owner = self.pservice.get_owner()
		self.owner = owner
		self.connect('shared', self._shared_cb)
		self.connect('joined', self._joined_cb)
		self.mediaType = "photo"

		return False

	def _received_cb(self, text):
		if(text.find(",") != -1):
			params = text.split(",")
			if(params[0] == "loc"):
				# other XO's map location has moved [lat,lng,zoom]
				self.preComet()
				self.cometLogic.handleReceivedMap(params[1],params[2],params[3])
				self.postComet()
			elif(params[0] == "mar"):
				# other XO has added or modded info marker [lat,lng,infoText,iconImg]
				if(self.cometLogic.addKMLSet == 0):
					self.preComet()
				self.cometLogic.handleAddMarker(params[1], params[2], params[3], params[4])
				self.m.setInfo(params[1],params[2],params[3],params[4])
				#self.cometLogic.handleEndKML()
				if(self.cometLogic.addKMLSet == 0):
					self.postComet()
			elif(params[0] == "del"):
				# delete a marker (not working)
				self.preComet()
				self.cometLogic.handleDelete()
				self.postComet()
			elif(params[0] == "smap"):
				# add SavedMap [lat,lng,zoom,info] + not-new reminder
				self.addSavedMap(params[1],params[2],params[3],params[4],False)
			elif(params[0] == "line"):
				# add a line
				if(self.cometLogic.addKMLSet == 0):
					self.preComet()
				self.cometLogic.handleLine(params[1],params[2],params[3],params[4])
				self.addLine(params[1],params[2],params[3],params[4],0,True)
				#self.cometLogic.handleEndKML()
				if(self.cometLogic.addKMLSet == 0):
					self.postComet()
			elif(params[0] == "endkml"):
				self.cometLogic.handleEndKML(0)
				self.postComet()
			elif(params[0] == "startkml"):
				self.preComet()
				self.cometLogic.startKML(0)

	def updateMapMetaData( self, ctrlat, ctrlng, zoom, showx, showy ):
		self.NOW_MAP_CENTER_LAT = ctrlat
		self.NOW_MAP_CENTER_LNG = ctrlng
		self.NOW_MAP_ZOOM = zoom
		# calculate where to put media overlay
		showx = int(showx) + 60
		showy = int(showy) + 425
		if(showx > 60) and (showx < 700) and (showy > 425) and (showy < 600):
			# open media overlay
			if(self.mediaType == "photo"):
				# mediaWindow contains a photo
				self.mediaWindow.show()
				self.smartMove(self.mediaWindow, self.htmlScale * showx, self.htmlScale * showy )
			else:
				# popWindow contains a video player
				self.popWindow.show()
				self.smartMove(self.popWindow, self.htmlScale * showx, self.htmlScale * showy )
				self.popWindow.hide()
				self.mediaWindow.show_all()
		else:
			self.mediaWindow.hide()
			self.popWindow.hide()
		if(self.maptube is not None):
			# update XO group location
			self.maptube.SendText("loc," + ctrlat + "," + ctrlng + "," + zoom)

	def _trayMouseCb( self, events, args):
		if (self.shownRecd != None):
			self.hideMedia()
			self.preComet()
			self.cometLogic.handleClear( )
			self.postComet()

		return True

	def _tagsBufferEditedCb(self, widget):
		if (self.shownSave != None):
			txt = self.tagsBuffer.get_text( self.tagsBuffer.get_start_iter(), self.tagsBuffer.get_end_iter() )
			if (txt != self.shownSave.notes):
				self.shownSave.notes = txt

	def _hideInfoCb( self, butt ):
		self.hideSearchResult()

	def _hideScienceCb( self, button ):
		#self.shownSave = None
		self.scienceWindow.set_property("accept-focus", False)
		self.moveWinOffscreen( self.scienceWindow )
		self.enableNavigation()

	def hideSearchResult(self):
		#self.shownSave = None
		#self.infoWindow.set_property("accept-focus", False)
		#self.moveWinOffscreen( self.infoWindow )
		self.enableNavigation()

	def showFileLoadBlocker( self, show ):
		rrr=0
		#if (show):
		#	self.smartMove( self.selectWindow, 0, 0 )
		#	self.smartResize( self.selectWindow, gtk.gdk.screen_width(), gtk.gdk.screen_height() )
		#else:
		#	self.moveWinOffscreen( self.selectWindow )


	def _sizeAllocateCb( self, widget, event ):
		self.toolbox.disconnect( self.TOOLBOX_SIZE_ALLOCATE_ID)

		self.smartMove(self.loadingWindow, 0, self.toolbox.allocation.height)
		self.loadingWindow.resize( gtk.gdk.screen_width(), gtk.gdk.screen_height()-(self.toolbox.allocation.height) )
		return False


	def remoteServerActive(self, loaded):
		if (self.loaded):
			return
		else:
			self.loaded = loaded
			#add search results from load_file
			for i in range(0, len(self.m.savedMaps)):
				smap = self.m.savedMaps[i]
				self.addThumb( smap, False )
			self.searchToolbar.set_sensitive(True)
			self.addToolbar.set_sensitive(True)
			browserW = self.browseBox.allocation.width
			browserH = self.browseBox.allocation.height
			#self.smartResize( self.infoWindow, browserW, browserH )
			self.moveWinOffscreen(self.loadingWindow)


	def addToWindowStack( self, win, parent ):
		self.windowStack.append( win )
		win.set_transient_for( parent )
		win.set_type_hint( gtk.gdk.WINDOW_TYPE_HINT_DIALOG )
		win.set_decorated( False )
		win.set_focus_on_map( False )
		win.set_property("accept-focus", False)


	def moveWinOffscreen( self, win ):
		#we move offscreen to resize or else we get flashes on screen, and setting hide() doesn't allow resize & moves
		offW = (gtk.gdk.screen_width() + 100)
		offH = (gtk.gdk.screen_height() + 100)
		self.smartMove(win, offW, offH)


	def smartMove( self, win, x, y ):
		winLoc = win.get_position()
		if ( (winLoc[0] != x) or (winLoc[1] != y) ):
			win.move( int(x), int(y) )
			return True
		else:
			return False


	def smartResize( self, win, w, h ):
		winSize = win.get_size()
		if ( (winSize[0] != w) or (winSize[1] != h) ):
			win.resize( w, h )
			return True
		else:
			return False


	def preComet(self):
		self.cond.acquire()


	def postComet(self):
		self.cond.notifyAll()
		self.cond.release()
		time.sleep(.1)


	def read_file(self, file):
		serialize.fillMediaHash(file, self.m)


	def close( self ):
		self.hide()
		activity.Activity.close( self )


	def write_file(self, file):
		dom = serialize.saveMediaHash(self.m)
		xmlFile = open( file, "w" )
		dom.writexml(xmlFile)
		xmlFile.close()

	def mapPaste(self):
		self.preComet()
		self.cometLogic.mapPaste('osm')
		self.postComet()

	def googlePaste(self):
		self.preComet()
		self.cometLogic.mapPaste('google')
		self.postComet()

	def _addressUpdateCb( self, otets, address ):
		#Special to OfflineMaps - decide the latlng of the given address
		if(address.find(',') != -1):
			if(len(address.split(',')) == 3):
				addSplit = address.split(',')
				if(addSplit[2] == 'm'):
					# add a marker at this lat,lng
					self.preComet()
					self.cometLogic.handleAddMarker(addSplit[0],addSplit[1],addSplit[0]+","+addSplit[1],"blue_map_dot.png")
					#self.cometLogic.handleEndKML()
					self.postComet()
					self.addInfoMarker(addSplit[0],addSplit[1],addSplit[0]+","+addSplit[1],"blue_map_dot.png",True)
					return
				elif((addSplit[0].find(".")!=-1) and (addSplit[1].find(".")==-1) and (addSplit[2].find(".")!=-1)):
					# go to this latmin, lngdeg, lngmin
					lat = float(addSplit[0])/60
					lng = float(addSplit[1])+float(addSplit[2])/60
					self.preComet()
					self.cometLogic.handleReceivedMap(str(lat),str(lng),"17")
					self.postComet()
					return

			elif(len(address.split(',')) == 4):
				addSplit=address.split(',')
				if(addSplit[3]=='m'):
					lat=float(addSplit[0])/60
					lng=float(addSplit[1])+float(addSplit[2])/60
					self.preComet()
					self.cometLogic.handleAddMarker(str(lat),str(lng),str(lat)+","+str(lng),"blue_map_dot.png")
					#self.cometLogic.handleEndKML()
					self.postComet()
					self.addInfoMarker(str(lat),str(lng),str(lat)+","+str(lng),"blue_map_dot.png",True)
					return
				elif(((addSplit[0]+addSplit[2]).find('.')==-1) and (addSplit[1].find('.') != -1) and (addSplit[3].find('.') != -1)):
					lat = float(addSplit[0])+float(addSplit[1])/60
					lng = float(addSplit[2])+float(addSplit[3])/60
					self.preComet()
					self.cometLogic.handleReceivedMap(str(lat),str(lng),"17")
					self.postComet()
					return
			elif(len(address.split(',')) == 5):
				addSplit=address.split(',')
				if(addSplit[4]=='m'):
					lng=float(addSplit[2])+float(addSplit[3])/60
					lat=float(addSplit[0])+float(addSplit[1])/60
					self.preComet()
					self.cometLogic.handleAddMarker(str(lat),str(lng),str(lat)+","+str(lng),"blue_map_dot.png")
					#self.cometLogic.handleEndKML()
					self.postComet()
					self.addInfoMarker(str(lat),str(lng),str(lat)+","+str(lng),"blue_map_dot.png",True)
					return
			latlng = address
		else:
			address = address.lower().replace(' ','').replace('-','')
			zoom="16"
			lat="-190"
			lng="-190"
			places = open(self.libPath + "Places.csv", 'r')
			for place in places:
				pData = place.split(',')
				pData[0] = pData[0].lower().replace(' ','').replace('-','')
				if(pData[0] == address):
					lat = pData[1]
					lng = pData[2]
					if(pData[3] != "-1"):
						zoom = pData[3]
					break
			if(lat=="-190"):
				findsrc="http://maps.googleapis.com/maps/api/geocode/json?sensor=false&address=" + urllib.quote(address)
				findAddress = urllib.urlopen(findsrc).read()
				longname=findAddress[findAddress.find('long_name')+13:len(findAddress)]
				longname=longname[0:longname.find('"')]

				findSW=findAddress[findAddress.find('southwest'):findAddress.find('northeast')].replace(" ","").replace('\n','')
				swlat=findSW[findSW.find('lat')+5:findSW.find(',')]
				swlng=findSW[findSW.find('lng')+5:findSW.find('}')]

				findNE=findAddress[findAddress.find('northeast'):len(findAddress)].replace(" ","").replace('\n','')
				nelat=findNE[findNE.find('lat')+5:findNE.find(',')]
				nelng=findNE[findNE.find('lng')+5:findNE.find('}')]

				self.proceedTxt = "moveToAddress(" + swlat + "," + swlng + "," + nelat + "," + nelng + ",'" + longname + "');"
				self.browser.load_uri("javascript:"+self.proceedTxt+";void(0);")
				return
			latlng = lat + "," + lng + "," + zoom
		self.preComet()
		self.cometLogic.handleAddressUpdate(latlng)
		self.postComet()

	def _searchUpdateCb( self, otets, tags ):
		self.NOW_MAP_TAGS = tags
		self.preComet()
		self.cometLogic.handleTagSearch(tags)
		self.postComet()

	def _zoomInCb( self, butt ):
		self.hideMedia()
		self.preComet()
		self.cometLogic.handleZoomUpdate("+")
		self.postComet()

	def _zoomOutCb( self, butt ):
		self.hideMedia()
		self.preComet()
		self.cometLogic.handleZoomUpdate("-")
		self.postComet()

	def _saveSearchCb( self, otets ):
		self._saveSearch()

	def _librarySearchCb( self, otets ):
		self.preComet()
		self.cometLogic.handleLibraryView()
		self.postComet()

	def _saveSearch( self ):
		#1st: cover up the tray when grabbing a screenshot
		#this will take a moment, so disable all buttons while we wait
		self.SAVING_SEARCH = False
		#self.SAVING_SEARCH = True
		#self.disableNavigation()
		#self.savingSearchMediaLoc = self.mediaWindow.get_position()
		#self.moveWinOffscreen( self.mediaWindow )
		#self.hideTray(True)


	def hideTray( self, hide ):
		if (hide):
			self.trayBox.set_current_page(self.fakeTrayIndex)
		else:
			self.trayBox.set_current_page(self.realTrayIndex)


	def _fakeTrayVisibleNotifyCb( self, widget, event ):
		#if (event.state == gtk.gdk.VISIBILITY_UNOBSCURED): #this is not used, bc a popup might be over it
		if (self.SAVING_SEARCH):
			gobject.idle_add( self._saveSearch2 )

	def _saveSearch2( self ):
		# add SavedMap
		window = self.canvas.window
		width, height = window.get_size()
		screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False, bits_per_sample=8, width=width, height=height)
		screenshot.get_from_drawable(window, window.get_colormap(), 0, 0, 0, 0, width, height)

		popW, popH = [self.popW+(2*self.popB), self.popH+(2*self.popB) ]
		popScreenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False, bits_per_sample=8, width=width, height=height)
		popScreenshot.get_from_drawable(self.popWindow.window, self.popWindow.window.get_colormap(), 0, 0, 0, 0, popW, popH)

		popLoc = self.popWindow.get_position()
		popLocX = popLoc[0]
		popLocY = popLoc[1] - self.toolbox.allocation.height 
		popScreenshot.composite(screenshot,
							popLocX, popLocY,		#move the actual mini-canvas (but not its internals (?))
							popW, popH,				#actual size of the mini-canvas
							popLocX, popLocY,		#offx, y of the painting (irrespective of the mini-canvas)
							1, 1,					#scalex,y
							gtk.gdk.INTERP_BILINEAR, 255)

		screenshotPath = os.path.join(Instance.instancePath, "savedMap.jpg")
		screenshotPath = utils.getUniqueFilepath(screenshotPath, 0)
		screenshot.save( screenshotPath, "jpeg", {} )

		smallHeight = 120
		smallWidth = (width*smallHeight) / height
		screenshotSmall = screenshot.scale_simple(smallWidth, smallHeight, gtk.gdk.INTERP_NEAREST)
		screenshotSmallPath = os.path.join(Instance.instancePath, "savedMapThumb.jpg")
		screenshotSmallPath = utils.getUniqueFilepath(screenshotSmallPath, 0)
		screenshotSmall.save( screenshotSmallPath, "jpeg", {} )

		sm = SavedMap( self.NOW_MAP_CENTER_LAT, self.NOW_MAP_CENTER_LNG, self.NOW_MAP_ZOOM, screenshotPath, screenshotSmallPath, "Describe the map", self.NOW_MAP_TAGS )
		if (self.shownRecd != None):
			sm.addViewedRecd(self.shownRecd.datastoreId, self.shownRecd.latitude, self.shownRecd.longitude)

		self.m.addSavedMap( sm )
		self.addThumb( sm, True )

		self.hideTray(False)
		self.enableNavigation()
		self.smartMove( self.mediaWindow, self.savingSearchMediaLoc[0], self.savingSearchMediaLoc[1] )
		
		if(self.maptube is not None):
			self.maptube.SendText("smap," + str(self.NOW_MAP_CENTER_LAT) + "," + str(self.NOW_MAP_CENTER_LNG) + "," + str(self.NOW_MAP_ZOOM) + ",Describe this map")

	def addLine(self,id,color,thickness,pts,isNew):
		self.m.setLine(id,color,thickness,pts)
		if((self.maptube is not None) and (isNew == 1)):
			self.maptube.SendText("line," + id + "," + color + "," + thickness + "," + pts)

	def addLine(self,id,color,thickness,pts,isNew,placename):
		self.m.setLine(id,color,thickness,pts)
		if((self.maptube is not None) and (isNew == 1)):
			self.maptube.SendText("line," + id + "," + color + "," + thickness + "," + pts)

	def lineMode(self,type):
		self.preComet()
		self.cometLogic.lineMode(type)
		self.postComet()

	def addSavedMap(self,lat,lng,zoom,info,isNew):
		# add SavedMap received from internet or other XO, use Google Static Maps
		window = self.canvas.window
		width, height = window.get_size()
		screenshotPath = os.path.join(Instance.instancePath, "savedMap.jpg")
		urllib.urlretrieve("http://maps.google.com/staticmap?key=ABQIAAAAxkKtrWN5q-vPTLRVmO_r6RRFDCLHCbUG3VrjXnZmMRXvQdFL3RS-b-ld9hTrkIgQlYsxPQ1kYq6y9A&size=200x120&format=jpg&center=" + str(lat) + "," + str(lng) + "&zoom=" + str(int(zoom)-1), screenshotPath)
		smallHeight = 120
		smallWidth = 200
		sm = SavedMap( lat, lng, zoom, screenshotPath, screenshotPath, info, "" )
		self.m.addSavedMap( sm )
		self.addThumb( sm, True )
		if(isNew == True):
			if(self.maptube is not None):
				# user created SaveMap, send to others
				self.maptube.SendText("smap," + lat + "," + lng + "," + zoom + "," + info)

	def addInfoMarker(self,lat,lng,info,icon,sendUpdate):
		# add/update InfoMarker in model
		self.m.setInfo(lat, lng, info, icon)
		if(sendUpdate == True):
			if(self.maptube is not None):
				# send added/updated info marker
				self.maptube.SendText("mar," + lat + "," + lng + "," + info + "," + icon)
		else:
			# put InfoMarker on own map
			self.preComet()
			self.cometLogic.handleAddMarker(lat,lng,info,icon)
			#self.cometLogic.handleEndKML()
			self.postComet()

	def joinGroup(self,groupName):
		#groupFile = urllib.urlopen("http://bluebird-science.appspot.com/group/data?name=" + groupName)
		#readError = 0
		groupData = '{}'
		#while readError == 0:
		#	try:
		#		groupData = groupData + groupFile.readline()
		#	except:
		#		readError = 1
		self.preComet()
		self.cometLogic.handleGroupData(groupData)
		self.postComet()

	def removeThumb( self, sm ):
		kids = self.tray.get_children()
		for i in range (0, len(kids)):
			if (kids[i].data == sm):
				self.tray.remove_item(kids[i])
				kids[i].cleanUp()
				kids[i].disconnect( kids[i].getButtClickedId() )
				kids[i].setButtClickedId(0)
				if (sm == self.shownSave):
					self.hideSearchResult()
		self.m.savedMaps.remove(sm)

	def addThumb( self, sm, forceScroll ):
		butt = SavedButton( self, sm )
		BUTT_CLICKED_ID = butt.connect( "clicked", self._thumbClickedCb, sm )
		butt.setButtClickedId(BUTT_CLICKED_ID)
		self.tray.add_item( butt, len(self.tray.get_children()) )
		butt.show()
		if (forceScroll):
			self.tray.scroll_to_end()

	#1 way to see a sr
	def _thumbClickedCb( self, button, smap ):
		self.showSearchResult(smap)
		self.preComet()
		self.cometLogic.handleSavedMap(smap.lat,smap.lng,smap.zoom,smap.notes)
		self.postComet()

	def showSearchResult( self, smap ):
		self.shownSave = smap
		self.updateSearchResultTags(smap)
		self.searchToolbar._setTagsString( smap.tags )

	def updateSearchResultTags( self, smap ):
		self.shownSave = smap
		self.lngValueLabel.set_text( str(smap.lng) )
		self.latValueLabel.set_text( str(smap.lat) )
		self.tagsBuffer.set_text( smap.notes )

	def showSearchResultTags( self, smap ):
		self.updateSearchResultTags( smap )

		#avoid popups lingering
		self.hideMedia()
		self.preComet()
		self.cometLogic.handleClear()
		self.postComet()
		self.disableNavigation()
		browserLoc = self.browseBox.translate_coordinates(self, 0, 0)
		#self.infoWindow.show_all()
		#self.smartMove(self.infoWindow, browserLoc[0], browserLoc[1])
		browserW = self.browseBox.allocation.width
		browserH = self.browseBox.allocation.height
		#self.smartResize(self.infoWindow, browserW, browserH)
		#self.infoWindow.set_property("accept-focus", True)

	def copyToClipboard( self, smap ):
		tmpImgPath = self.doClipboardCopyStart( smap )
		gtk.Clipboard().set_with_data( [('text/uri-list', 0, 0)], self._clipboardGetFuncCb, self._clipboardClearFuncCb, tmpImgPath )
		return True

	def doClipboardCopyStart( self, smap ):
		tmpImgPath = utils.getUniqueFilepath(smap.imgPath, 0)
		shutil.copyfile( smap.imgPath, tmpImgPath )
		return tmpImgPath

	def doClipboardCopyCopy( self, tmpImgPath, selection_data ):
		tmpImgUri = "file://" + tmpImgPath
		selection_data.set( "text/uri-list", 8, tmpImgUri )

	def doClipboardCopyFinish( self, tmpImgPath ):
		if (tmpImgPath != None):
			if (os.path.exists(tmpImgPath)):
				os.remove( tmpImgPath )
		tmpImgPath = None

	def _clipboardGetFuncCb( self, clipboard, selection_data, info, data):
		self.doClipboardCopyCopy( data, selection_data )

	def _clipboardClearFuncCb( self, clipboard, data):
		self.doClipboardCopyFinish( data )

	def _addMediaCb( self, ot, datastoreOb ):
		self.addMeToMapObj = datastoreOb
		self.hideMedia()
		self.preComet()
		self.cometLogic.handlePreAdd()
		self.postComet()

	def _addKMLCb( self, ot, datastoreOb ):
		self.readKML(open(datastoreOb.file_path, 'r'),True)
 
	def readKML(self, kml, storeObjects):
		firstLine = kml.readline()
		if(firstLine.find('<?xml version="1.0" ?><map')==0):
			# Offline Map or regular Map file without Sugar's meta-data
			self.preComet()
			self.cometLogic.startKML(1)
			xmlarray = firstLine.split('>')
			for node in xmlarray:
				if(node.find('<mapItem') == 0):
					# picture marker
					lat = node[node.find('lat="')+5:len(node)]
					lat = lat[0:lat.find('"')]
					lng = node[node.find('lng="')+5:len(node)]
					lng = lng[0:lng.find('"')]
					description = node[node.find('info="')+6:len(node)]
					description = description[0:description.find('"')]
					icon = node[node.find('icon="')+6:len(node)]
					icon = icon[0:icon.find('"')]
					self.cometLogic.handleAddMarker(lat,lng,description,icon)
					self.addInfoMarker(lat,lng,description,icon,True)
				if(node.find('<infoMarker') == 0):
					# info marker
					lat = node[node.find('lat="')+5:len(node)]
					lat = lat[0:lat.find('"')]
					lng = node[node.find('lng="')+5:len(node)]
					lng = lng[0:lng.find('"')]
					description = node[node.find('info="')+6:len(node)]
					description = description[0:description.find('"')]
					icon = node[node.find('icon="')+6:len(node)]
					icon = icon[0:icon.find('"')]
					self.cometLogic.handleAddMarker(lat,lng,description,icon)
					self.addInfoMarker(lat,lng,description,icon,True)
				elif(node.find('<line') == 0):
					# line
					lineColor = node[node.find('lcolor="')+8:len(node)]
					lineColor = lineColor[0:lineColor.find('"')]
					lineID = node[node.find('lid="')+5:len(node)]
					lineID = lineID[0:lineID.find('"')]
					ptStr = node[node.find('lpts="')+6:len(node)]
					ptStr = ptStr[0:ptStr.find('"')]
					lineThick = node[node.find('lthickness="')+12:len(node)]
					lineThick = lineThick[0:lineThick.find('"')]
					self.cometLogic.handleLine(lineID,lineColor,lineThick,ptStr,"true")
					self.addLine(lineID,lineColor,lineThick,ptStr,1)
				elif(node.find('<savedMap') == 0):
					# saved map
					lat = node[node.find('lat="')+5:len(node)]
					lat = lat[0:lat.find('"')]
					lng = node[node.find('lng="')+5:len(node)]
					lng = lng[0:lng.find('"')]			
					notes = node[node.find('notes="')+7:len(node)]
					notes = notes[0:notes.find('"')]
					zoom = node[node.find('zoom="')+6:len(node)]
					zoom = zoom[0:zoom.find('"')]
					self.addSavedMap(lat,lng,zoom,notes,True)
			self.cometLogic.handleEndKML(1)
			self.postComet()
			return
		placename = None
		description = None
		lat = None
		lng = None
		coordList = None
		placemarkType = None
		lineType = None
		stillDescribing = False
		morePts = False
		dataTable = None
		isOSM = False
		isGeoRSS = False
		self.preComet()
		self.cometLogic.startKML(1)
		styleMaps={}
		styleActuals={}
		openStyleMap=None
		openStyle=None
		openLocalStyle=None
		specialIcon = "blue_map_dot.png"
		for kmlline in kml:
			if((kmlline.find('<osm') != -1) and (lat == None) and (lng == None) and (coordList == None)):
				# jump to osm
				isOSM = True
				break
			elif((kmlline.find('georss') != -1) and (lat == None) and (lng == None) and (coordList == None)):
				# jump to GeoRSS
				isGeoRSS = True
				break
			if(kmlline.find('<Point') != -1):
				placemarkType = 'info'
			elif(kmlline.find('<LineString') != -1):
				placemarkType = 'line'
				lineType = 'line'
			elif(kmlline.find('<Polygon') != -1):
				placemarkType = 'poly'
				lineType = 'poly'
			#elif(kmlline.find('<GroundOverlay') != -1):
			#	placemarkType = 'overlay'
			if(kmlline.find('<ExtendedData') != -1):
				dataTable = '<table style="font-size:9pt;">'
			elif(kmlline.find('</ExtendedData>') != -1):
				dataTable = dataTable + '</table>'
			if(dataTable is not None):
				if(kmlline.find('<Data') != -1):
					dataTable = dataTable + '<tr>'
				if(kmlline.find('<Data name="') != -1):
					dataTable = dataTable + "<td><b>" + kmlline[kmlline.find('<Data name="')+12:kmlline.rfind('"')] + "</b></td>"
				if(kmlline.find("<Data name='") != -1):
					dataTable = dataTable + "<td><b>" + kmlline[kmlline.find("<Data name='")+12:kmlline.rfind("'")] + "</b></td>"
				if(kmlline.find('<value>') != -1):
					dataTable = dataTable + "<td>" + kmlline[kmlline.find('<value>')+7:kmlline.find('</value>')] + "</td>"
				elif(kmlline.find('</Data>') != -1):
					dataTable = dataTable + '</tr>'

			if(kmlline.find('<coordinates>') != -1):
				if(placemarkType == 'info'):
					lng = kmlline[kmlline.find('<coordinates>')+13:kmlline.find(',')]
					if(len(kmlline.split(',')) > 2):
						lat = kmlline[kmlline.find(',')+1:kmlline.rfind(',')]
					else:
						lat = kmlline[kmlline.find(',')+1:kmlline.rfind('<')]
				else:
					if(kmlline.find('</coordinates>') == -1):
						morePts = True
					kmlline = kmlline.replace('<coordinates>','').replace('</coordinates>','')
					coordList = kmlline.split(' ')
			elif(morePts == True):
				if(kmlline.find('</coordinates>') != -1):
					morePts = False
					kmlline = kmlline.replace('</coordinates>','')
				coordList.extend(kmlline.split(' '))

			if(kmlline.find('<StyleMap') != -1):
				openStyleMap=kmlline[kmlline.find('id="')+4:len(kmlline)]
				openStyleMap=openStyleMap[0:openStyleMap.find('"')].replace('#','')
			elif(openStyleMap != None):
				if(kmlline.find('<styleUrl') != -1):
					styleMaps[openStyleMap] = kmlline[kmlline.find('#')+1:kmlline.find('</styleUrl')]
				if(kmlline.find('</StyleMap') != -1):
					openStyleMap=None
			elif(kmlline.find('<Style') != -1):
				openStyle=kmlline[kmlline.find('id="')+4:len(kmlline)].replace('#','')
				openStyle=openStyle[0:openStyle.find('"')]
			elif(openStyle != None):
				if(kmlline.find('<color') != -1):
					styleActuals[openStyle]=kmlline[kmlline.find('>')+3:kmlline.find('</color')]
				if(kmlline.find('</Style') != -1):
					openStyle=None
			elif(kmlline.find('<styleUrl') != -1):
				openLocalStyle=kmlline[kmlline.find('#')+1:kmlline.find('</styleUrl')]

			if(kmlline.find('<name>') != -1):
				placename = kmlline[kmlline.find('<name>')+6:kmlline.find('</name>')]
			if(kmlline.find('<description>') != -1):
				description = kmlline[kmlline.find('<description>')+13:len(kmlline)]
				if(kmlline.find('</description>') == -1):
					# need to read in more lines
					stillDescribing = True
				else:
					description = description[0:description.find('</description')]
					if(description.find('<![CDATA[') != -1):
						description = description.replace('<![CDATA[','').replace(']]>','')
			elif(stillDescribing == True):
				description = description + kmlline
				if(kmlline.find('</description>') != -1):
					stillDescribing = False
					description = description[0:description.find('</description')]
					if(description.find('<![CDATA[') != -1):
						description = description.replace('<![CDATA[','').replace(']]>','')

			if(kmlline.find('<Icon><href>') != -1):
				specialIcon = kmlline[kmlline.find('<Icon><href>')+12:kmlline.find('</href></Icon>')]

			if((kmlline.find('</Placemark>') != -1) or (kmlline.find('<Placemark>') != -1)):
				if(placename is None):
					placename=""
				# finish this placemark
				if(lat is not None):
					if(description is None):
						description = ""
					if(dataTable is not None):
						description = dataTable.replace('<![CDATA[','').replace(']]>','') + description
					if(placename is not None):
						description = '<h3>' + placename + '</h3>' + description
					try:
						self.cometLogic.handleAddMarker(lat,lng,description,specialIcon)
						self.addInfoMarker(lat,lng,description,specialIcon,True)
					except:
						rrrr=0
				if(coordList is not None):
					ptList = []
					maxInterval = 1
					if(len(coordList) > 40):
						maxInterval = int(len(coordList) / 30)
					interval = 1
					for pt in coordList:
						ptloc = pt.split(',')
						interval = interval - 1
						if((len(ptloc) > 1) and (interval < 2)):
							ptList.append(ptloc[1]+"|"+ptloc[0])
							interval = maxInterval
					randColor=""
					if(openLocalStyle is not None):
						try:
							randColor=styleActuals[openLocalStyle]
						except:
							try:
								randColor=styleActuals[styleMaps[openLocalStyle]]
							except:
								randColor=""
					if(randColor==""):
						cchars=[0,1,2,3,4,5,6,7,8,9,'a','b','c','d','e','f']
						for r in range(0,6):
							randColor = randColor + str(cchars[random.randint(0,15)])
					try:
						if(lineType == 'line'):
							lineID = str(random.getrandbits(128))
							self.cometLogic.handleLine(lineID,randColor,"5",'|'.join(ptList),placename,"false")
							self.addLine(lineID,randColor,"5",'|'.join(ptList),1,placename)
						elif(lineType == 'poly'):
							lineID = "poly-" + str(random.getrandbits(128))
							self.cometLogic.handleLine(lineID,randColor,"5",'|'.join(ptList),placename,"false")
							self.addLine(lineID,randColor,"5",'|'.join(ptList),1,placename)
						#elif(placemarkType == 'overlay'):
					except:
						rrrr=0
				lat = None
				lng = None
				description = None
				placename = None
				placemarkType = None
				coordList = None
				dataTable = None
				openLocalStyle = None
				specialIcon = "blue_map_dot.png"
		if(isOSM == True):
			# read in an OSM style file
			osmNodes = {}
			readingInNodeID = None
			readingInWayID = None
			for osm in kml:
				if(osm.find('<node') != -1):
					# point, which may be part of a line
					nodeID = osm[osm.find('id=')+4:len(osm)]
					nodeID = nodeID[0:nodeID.find('"')]
					nodeID = nodeID[0:nodeID.find("'")]
					lat = osm[osm.find('lat=')+5:len(osm)]
					lat = lat[0:lat.find("'")]
					lat = lat[0:lat.find('"')]
					lng = osm[osm.find('lon=')+5:len(osm)]
					lng = lng[0:lng.find("'")]
					lng = lng[0:lng.find('"')]
					osmNodes[nodeID] = {"latitude":lat,"longitude":lng,"inWay":False,"isWay":False}
					if(osm.find('/>') == -1):
						readingInNodeID = nodeID
				elif(readingInNodeID is not None):
					# reading in tag-values for the point
					if(osm.find('</node>') != -1):
						readingInNodeID = None
					else:
						if(osm.find('<tag') != -1):
							tName = osm[osm.find('k=')+3:len(osm)]
							tName = tName[0:tName.find('"')]
							tName = tName[0:tName.find("'")]
							vName = osm[osm.find('v=')+3:len(osm)]
							vName = vName[0:vName.find('"')]
							vName = vName[0:vName.find("'")]
							osmNodes[readingInNodeID][tName] = vName
				elif(osm.find('<way') != -1):
					# line, composed of multiple points
					readingInWayID = osm[osm.find('id=')+4:len(osm)]
					readingInWayID = readingInWayID[0:readingInWayID.find('"')]
					readingInWayID = readingInWayID[0:readingInWayID.find("'")]
					osmNodes[readingInWayID] = {"isWay":True,"pts":[]}
				elif(readingInWayID is not None):
					# reading in node ids composing the line
					if(osm.find('</way>') != -1):
						readingInWayID = None
					else:
						if(osm.find('<nd') != -1):
							nodeRef = osm[osm.find('ref=')+5:len(osm)]
							if(nodeRef.find('"') != -1):
								nodeRef = nodeRef[0:nodeRef.find('"')]
							else:
								nodeRef = nodeRef[0:nodeRef.find("'")]
							osmNodes[readingInWayID]["pts"].append(nodeRef)
							osmNodes[nodeRef]["inWay"] = True
			# decide how to publish nodes
			for node in osmNodes:
				if(osmNodes[node]["isWay"] == True):
					# line composed of points
					ptList=[]
					for pID in osmNodes[node]["pts"]:
						ptList.append(osmNodes[pID]["latitude"]+"|"+osmNodes[pID]["longitude"])
					lineID = str(random.getrandbits(128))
					self.cometLogic.handleLine(lineID,"B22222","5",'|'.join(ptList))
					self.addLine(lineID,"B22222","5",'|'.join(ptList),1)
				elif(osmNodes[node]["inWay"] == False):
					# independent point
					description="<table>"
					for tag in osmNodes[node]:
						if(tag=="latitude"):
							continue
						elif(tag=="longitude"):
							continue
						elif(tag=="inWay"):
							continue
						elif(tag=="isWay"):
							continue
						else:
							value = osmNodes[node][tag]
							description=description+"<tr><td>"+tag+"</td><td>"+str(value)+"</td></tr>"
					description=description+"</table>"
					self.cometLogic.handleAddMarker(osmNodes[node]["latitude"],osmNodes[node]["longitude"],description,"magenta_map_dot.png")
					self.addInfoMarker(osmNodes[node]["latitude"],osmNodes[node]["longitude"],description,"magenta_map_dot.png",True)
		elif(isGeoRSS == True):
			# scan in GeoRSS
			placeLink = None
			lat = None
			lng = None
			description = None
			placename = None
			stillDescribing = False
			#self.preComet()
			for rss in kml:
				if(rss.find('<title') != -1):
					placename = rss[rss.find('>')+1:rss.find('</title>')]
				if(rss.find('<link') != -1):
					placeLink = rss[rss.find('>')+1:rss.find('</link>')]					
				if(rss.find('<georss:point') != -1):
					latlng = rss[rss.find('>')+1:rss.find('</georss:point>')].split(' ')
					lat = latlng[0]
					lng = latlng[1]
				if(rss.find('<description>') != -1):
					description = rss[rss.find('<description>')+13:len(rss)]
					if(rss.find('</description>') == -1):
						# need to read in more lines
						stillDescribing = True
					else:
						description = description[0:description.find('</description')]
				elif(stillDescribing == True):
					description = description + rss
					if(rss.find('</description>') != -1):
						stillDescribing = False
						description = description[0:description.find('</description')]
				if(rss.find('</item>') != -1):
					# publish the point
					if(lat is not None):
						if(description == None):
							description = ""
						if(placeLink is not None):
							description = placeLink + "<br/>" + description
						if(placename is not None):
							description = '<h3>' + placename + '</h3>' + description
						description=description.replace("'","\\'").replace('"','\\"')
						description=description.replace("\n","<br/>").replace("\r","<br/>")
						description=description.replace("<![CDATA[","").replace("]]>","")
						self.cometLogic.handleAddMarker(lat,lng,description,"magenta_map_dot.png")
						self.addInfoMarker(lat,lng,description,"magenta_map_dot.png",True)
						placeLink = None
						lat = None
						lng = None
						placename = None
						description = None
						stillDescribing = False
		self.cometLogic.handleEndKML(1)
		self.postComet()
		try:
			kml.close()
		except:
			rrrr=0
		self.browser.load_uri("javascript:openLayer=null;updateLines();void(0);")

	def _addInfoCb(self,ot):
		self.preComet()
		self.cometLogic.handlePreAddInfo()
		self.postComet()

	def _measureCb(self,ot):
		self.preComet()
		self.cometLogic.handleMeasure()
		self.postComet()

	def _panoramioCb(self,ot):
		self.preComet()
		self.cometLogic.handlePanoramio()
		self.postComet()

	def _localwikiCb(self,ot):
		self.preComet()
		self.cometLogic.handleLocalWiki()
		self.postComet()

	def _wikimapiaCb(self,ot):
		self.preComet()
		self.cometLogic.handleWikiMapia()
		self.postComet()

	def disableNavigation( self ):
		#disable the toolbar buttons
		self.addToolbar.set_sensitive( False )
		self.searchToolbar.set_sensitive( False )

	def enableNavigation( self ):
		#enable the toolbar buttons
		self.addToolbar.set_sensitive( True )
		self.searchToolbar.set_sensitive( True )

	def placeAddMedia( self, lat, lng ):
		self.enableNavigation()
		#append to the map
		if(self.addMeToMapObj.metadata['title'].find(".") != -1):
			latlng = self.addMeToMapObj.metadata['title'].replace("  "," ").split(" ")
			if(len(latlng) < 4):
				if(latlng[0].find(".") == -1):
					lat = int(latlng[0]) + float(latlng[1])/60
					lng = float(latlng[2])/60
				else:
					lat = float(latlng[0])/60
					lng = int(latlng[1]) + float(latlng[2])/60
			else:
				lat = int(latlng[0]) + float(latlng[1])/60
				lng = int(latlng[2]) + float(latlng[3])/60
		recd = self.m.addMedia( str(lat), str(lng), self.addMeToMapObj )
		#now show the new addition to the map
		self.preComet()
		self.cometLogic.handlePostAdd( recd )
		self.postComet()
		# send image to others
		#if(self.maptube is not None):
		#	self.maptube.SendText("mar," + lat + "," + lng + "," + utils.getStringFromPixbuf(recd.getPixBuf()) )

        def sendEndKML(self):
                self.maptube.SendText("endkml,now")

        def sendStartKML(self):
                self.maptube.SendText("startkml,now")

	def _deleteMediaCb( self, ot ):
		self.preComet()
		self.cometLogic.handleDelete()
		self.postComet()

	def showMedia(self, id, x, y, up, rt):
		x = 200
		y = 50
		recd = self.m.getMediaByThumbFilename(id)
		if (recd == None):
			return
		self.shownRecd = recd
		thumbPath = recd.getThumbPath()
		thumbPixbuf = gtk.gdk.pixbuf_new_from_file(thumbPath)
		px, py = [self.popW, self.popH]
		scl = (self.popW+0.0) / (thumbPixbuf.get_width()+0.0)
		thumbCairo = utils.generateThumbnail( thumbPixbuf, scl, px, py )
		self.popUpBg.updatePopInfo( recd.colorStroke, recd.colorFill, thumbCairo, up, rt, self.popB, self.popB, self.htmlScale )
		browserLoc = self.browseBox.translate_coordinates( self, 0, 0 )
		x = int(x) * self.htmlScale
		y = int(y) * self.htmlScale
		x = browserLoc[0]+x
		y = browserLoc[1]+y
		if (not rt):
			x = x - (self.popW + (2*self.popB))
		if (not up):
			y = y - (self.popH + (2*self.popB))
		self.smartMove( self.popWindow, x, y )
		kid = self.mediaWindow.get_child()
		if (kid != None):
			self.gplay.stop()
			self.mediaWindow.remove( kid )
		self.mediaWindow.modify_bg(gtk.STATE_NORMAL, recd.colorFill.gColor)
		if (recd.type == Constants.TYPE_PHOTO):
			self.mediaType = 'photo'
			self.popWindow.hide()
			self.mediaWindow.show()
			self.smartResize( self.mediaWindow, self.popW, self.popH )
			self.smartMove( self.mediaWindow, x+self.popB, y+self.popB)
			pbuf = recd.getPixBuf()
			img = _camera.cairo_surface_from_gdk_pixbuf(pbuf)
			self.photoCanvas.modify_bg(gtk.STATE_NORMAL, recd.colorFill.gColor)
			self.photoCanvas.set_size_request(self.popW, self.popH)
			self.photoCanvas.setImage(img)
			self.mediaWindow.add(self.photoCanvas)
			self.photoCanvas.show_all()

		elif (recd.type == Constants.TYPE_VIDEO):
			self.mediaType = 'video'
			self.popWindow.show()
			self.mediaWindow.show()
			self.smartResize( self.mediaWindow, self.popW, self.popH )
			self.smartMove( self.mediaWindow, x+self.popB, y+self.popB)
			self.smartMove( self.popWindow, x+self.popB, y+self.popB)
			self.mediaWindow.add(self.gplayWin)
			self.gplayWin.modify_bg(gtk.STATE_NORMAL, recd.colorFill.gColor)
			self.popWindow.hide()
			self.mediaWindow.show()
			self.gplayWin.show_all()
			videoUrl = "file://" + str( recd.getFilepath() )
			self.gplay.setLocation( videoUrl )
			self.gplay.play()
		self.mediaWindow.show_all()
		self.mediaWindow.set_keep_above(True)
		self.popWindow.set_keep_above(True)
		self.gplayWin.set_keep_above(True)

	def hideMedia( self ):
		self.shownRecd = None
		#self.moveWinOffscreen( self.popWindow )
		#self.moveWinOffscreen( self.mediaWindow )
		self.gplay.pause()
		self.mediaWindow.hide_all()

	def destroy(self, *args):
		self.hide_all()
		os._exit(0) #needed to kill all threads
		gtk.main_quit()

	def _shared_cb(self, activity):
		self.initiating = True
		self._sharing_setup()
		id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(SERVICE, {})

	def _sharing_setup(self):
		if self._shared_activity is None:
			return
		self.conn = self._shared_activity.telepathy_conn
		self.tubes_chan = self._shared_activity.telepathy_tubes_chan
		self.text_chan = self._shared_activity.telepathy_text_chan
		self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('NewTube', self._new_tube_cb)

	def _list_tubes_reply_cb(self, tubes):
		for tube_info in tubes:
			self._new_tube_cb(*tube_info)

	# joining a pre-existing activity
	def _joined_cb(self, activity):
		if not self._shared_activity:
			return
		self.initiating = False
		self._sharing_setup()
		self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(reply_handler=self._list_tubes_reply_cb,error_handler=self.tubes_error)

	# display error raised by XO-XO connection on map
	def tubes_error(self,e):
		self.preComet()
		self.cometLogic.handleCompassUpdate("Error: %s",e)
		self.postComet()

	def _new_tube_cb(self, id, initiator, type, service, params, state):
		if (type == telepathy.TUBE_TYPE_DBUS and service == SERVICE):
			if state == telepathy.TUBE_STATE_LOCAL_PENDING:
				self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)
			tube_conn = TubeConnection(self.conn, self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES], id, group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])
			self.maptube = TextSync(tube_conn, self.initiating, self._received_cb, self.tubes_error, self._get_buddy)

	# _get_buddy may not be necessary.  Borrowed from HelloMesh
	def _get_buddy(self, cs_handle):
		group = self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP]
		my_csh = group.GetSelfHandle()
		if my_csh == cs_handle:
			handle = self.conn.GetSelfHandle()
		elif group.GetGroupFlags() & telepathy.CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
			handle = group.GetHandleOwners([cs_handle])[0]
		else:
			handle = cs_handle
		return self.pservice.get_buddy_by_telepathy_handle(self.conn.service_name, self.conn.object_path, handle)

class TextSync(ExportedGObject):
    def __init__(self, tube, is_initiator, text_received_cb, alert, get_buddy):
        super(TextSync, self).__init__(tube, PATH)
        self.tube = tube
        self.is_initiator = is_initiator
        self.text_received_cb = text_received_cb
        self._alert = alert
        self.entered = False  # Have we set up the tube?
        self.text = '' # State that gets sent or received
        self._get_buddy = get_buddy  # Converts handle to Buddy object
        self.tube.watch_participants(self.participant_change_cb)

    def participant_change_cb(self, added, removed):
        for handle, bus_name in added:
            buddy = self._get_buddy(handle)
        for handle in removed:
            buddy = self._get_buddy(handle)
        if not self.entered:
            if self.is_initiator:
                self.add_hello_handler()
            else:
                self.Hello()
        self.entered = True

    @signal(dbus_interface=IFACE, signature='')
    def Hello(self):
		self.bogus = 1

    @method(dbus_interface=IFACE, in_signature='s', out_signature='')
    def World(self, text):
        if not self.text:
            self.text = text
            self.text_received_cb(text)
            self.add_hello_handler()

    def add_hello_handler(self):
        self.tube.add_signal_receiver(self.hello_cb, 'Hello', IFACE,
            path=PATH, sender_keyword='sender')
        self.tube.add_signal_receiver(self.sendtext_cb, 'SendText', IFACE,
            path=PATH, sender_keyword='sender')

    def hello_cb(self, sender=None):
        if sender == self.tube.get_unique_name():
            return
        self.tube.get_object(sender, PATH).World(self.text,
                                                 dbus_interface=IFACE)

    def sendtext_cb(self, text, sender=None):
        if sender == self.tube.get_unique_name():
            return
        self.text = text
        self.text_received_cb(text)

    @signal(dbus_interface=IFACE, signature='s')
    def SendText(self, text):
        self.text = text

class SearchToolbar(gtk.Toolbar):

	__gsignals__ = {
		'address-update': (gobject.SIGNAL_RUN_FIRST, None, [object]),
		'search': (gobject.SIGNAL_RUN_FIRST, None, [object]),
		'zoom-in': (gobject.SIGNAL_RUN_FIRST, None, []),
		'zoom-out': (gobject.SIGNAL_RUN_FIRST, None, []),
		'save-search': (gobject.SIGNAL_RUN_FIRST, None, []),
		'library-search': (gobject.SIGNAL_RUN_FIRST, None, []),
		'search-update': (gobject.SIGNAL_RUN_FIRST, None, [object])
	}

	def __init__(self, pc):
		gtk.Toolbar.__init__(self)
		self.ca = pc

		addressLabel = gtk.Label( Constants.istrSearchAddress )
		addressLabel.show()
		toolAddressLabel = gtk.ToolItem()
		toolAddressLabel.add(addressLabel)
		self.insert(toolAddressLabel, -1)
		toolAddressLabel.show()

		self._insertSep()

		self.addressField = gtk.Entry()
		self.addressField.connect('activate', self._addressActivateCb)
		addressItem = gtk.ToolItem()
		addressItem.set_expand(True)
		addressItem.add(self.addressField)
		self.addressField.show()
		self.insert( addressItem, -1 )
		addressItem.show()

		self._insertSep()

		searchLabel = gtk.Label( Constants.istrSearchMedia )
		searchLabel.show()
		toolSearchLabel = gtk.ToolItem()
		toolSearchLabel.add(searchLabel)
		self.insert(toolSearchLabel, -1)
		toolSearchLabel.show()

		self._insertSep()

		self.searchField = gtk.Entry()
		self.searchField.connect('activate', self._searchActivateCb)
		searchItem = gtk.ToolItem()
		searchItem.set_expand(True)
		searchItem.add(self.searchField)
		self.searchField.show()
		self.insert( searchItem, -1 )
		searchItem.show()

		self._insertSep()

		saveButt = ToolButton("save-search")
		saveButt.set_tooltip(Constants.istrLibrary)
		saveButt.connect('clicked', self._saveCb)
		self.insert(saveButt, -1)
		saveButt.show()

	def _setTagsString( self, tags ):
		self.searchField.set_text(tags)

	def _insertSep( self ):
		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)
		separator.set_expand(False)
		separator.set_size_request(Constants.ui_dim_INSET, -1)
		self.insert( separator, -1 )

	def _addressActivateCb(self, widget):
		address = widget.props.text
		self.emit('address-update', address)

	def _saveCb(self, widget):
		self.emit('library-search')
		#self.emit('save-search')

	def _searchActivateCb(self, widget):
		search = widget.props.text
		self.emit('search-update', search)


	def _zoomInCb(self, button):
		self.emit('zoom-in')

	def _zoomOutCb(self, button):
		self.emit('zoom-out')

class PopUpP5(P5):
	def __init__(self):
		P5.__init__(self)
		self.fill = None
		self.stroke = None
		self.previewCairoImg = None
		self.up = None
		self.rt = None
		self.scale = None
		self.insetX = 0
		self.insetY = 0

	def updatePopInfo(self, stroke, fill, cairoThumb, up, rt, insetX, insetY, scale):
		self.fill = fill
		self.stroke = stroke
		self.previewCairoImg = cairoThumb
		self.up = up
		self.rt = rt
		self.scale = scale
		self.insetX = insetX
		self.insetY = insetY
		self.queue_draw()


	def draw(self, ctx, w, h):
		#for stroking
		self.fillRect( ctx, self.fill, w, h )

		lw = 5
		hlw = lw/2
		ctx.set_line_width( lw*self.scale )
		ctx.rectangle(0, 0, w, h)
		self.setColor(ctx, self.stroke)
		ctx.stroke()

		#for the popup bubble's handle
		if (not self.up):
			ctx.translate(0, h-(3*self.scale))
		if (not self.rt):
			ctx.translate(w-((hlw+21)*self.scale), 0)
		else:
			ctx.translate(hlw*self.scale, 0)

		ctx.rectangle(0, 0, 21*self.scale, 3*self.scale)
		self.setColor(ctx, self.fill)
		ctx.fill()

		ctx.identity_matrix()
		ctx.set_source_surface(self.previewCairoImg, self.insetX, self.insetY)
		ctx.paint()


class AddToolbar(gtk.Toolbar):
	__gsignals__ = {
		'add-media': (gobject.SIGNAL_RUN_FIRST, None, [object]),
		'add-kml': (gobject.SIGNAL_RUN_FIRST, None, [object]),
		'delete-media': (gobject.SIGNAL_RUN_FIRST, None, []),
		'measure': (gobject.SIGNAL_RUN_FIRST, None, []),
		'add-info': (gobject.SIGNAL_RUN_FIRST, None, [])
	}

	def __init__(self, pc):
		gtk.Toolbar.__init__(self)
		self.ca = pc

		self.addButt = ToolButton('add-icon')
		self.addButt.set_tooltip(Constants.istrAddMedia)
		self.insert(self.addButt, -1)
		self.addButt.connect('clicked', self._addCb)
		
		infoButt = ToolButton('corner-info')
		infoButt.set_tooltip(Constants.istrAddInfo)
		self.insert(infoButt, -1)
		infoButt.connect('clicked', self._addInfoCb)
		
		self._insertSep()

		delButt = ToolButton('delete-icon')
		delButt.set_tooltip(Constants.istrDeleteMedia)
		self.insert(delButt, -1)
		delButt.connect('clicked', self._delCb)
		
		self._insertSep()
		self._insertSep()
		self._insertSep()
		self._insertSep()
		
		# add line tools
		lineButt = ToolButton('tool-shape-line')
		lineButt.set_tooltip(Constants.LineButton)
		self.insert(lineButt, -1)
		lineButt.connect('clicked', self._lineCb)
		polyButt = ToolButton('tool-polygon')
		polyButt.set_tooltip(Constants.PolyButton)
		self.insert(polyButt,-1)
		polyButt.connect('clicked', self._polyCb)
		
		self._insertSep()
		self._insertSep()
		self._insertSep()
		
		
		measButt = ToolButton('measure-icon')
		measButt.set_tooltip(Constants.istrMeasure)
		self.insert(measButt, -1)
		measButt.connect('clicked', self._measCb)

		self._insertSep()
		self._insertSep()
		self._insertSep()

	def _insertSep( self ):
		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)
		separator.set_expand(False)
		separator.set_size_request(25 + Constants.ui_dim_INSET, -1)
		self.insert( separator, -1 )

	def _addCb(self, button):
		self.ca.showFileLoadBlocker(True)

		fp = FilePicker()
		dOb = fp.show()
		if (dOb != None):
			if (dOb.file_path != None):
				if(dOb.metadata['mime_type']=="video/ogg") or (dOb.metadata['mime_type']=="image/jpeg"):
					self.emit("add-media", dOb)
				elif(dOb.metadata['mime_type']=="audio/ogg"):
					self.emit("add-media", dOb)
				else:
					self.emit("add-kml", dOb)
				#else:
				#	self.emit("add-info")

		self.ca.showFileLoadBlocker(False)

	def _addInfoCb(self, button):
		self.emit("add-info")

	def _delCb(self, button):
		self.emit("delete-media")

	def _measCb(self, button):
		# start a measure tool (rect area or polyline) - calculation handled in HTML/JavaScript
		self.emit("measure")
	
	def _lineCb(self, button):
		self.ca.lineMode('line')

	def _polyCb(self, button):
		self.ca.lineMode('polygon')

class dlToolbar(gtk.Toolbar):
	__gsignals__ = {
		'web-media': (gobject.SIGNAL_RUN_FIRST, None, []),
		'panoramio':(gobject.SIGNAL_RUN_FIRST, None, []),
		'local-wiki':(gobject.SIGNAL_RUN_FIRST, None, []),
		'wikimapia':(gobject.SIGNAL_RUN_FIRST, None, [])
	}

	def __init__(self, pc):
		gtk.Toolbar.__init__(self)
		self.ca = pc

		# OpenStreetMap paste
		webButt = ToolButton('static-icon')
		webButt.set_tooltip(Constants.istrWebMedia)
		self.insert(webButt, -1)
		webButt.connect('clicked', self._webCb)

		self._insertSep()
		
		# Google Paste
		staticButt = ToolButton('web-icon')
		staticButt.set_tooltip(Constants.istrStaticMaps)
		self.insert(staticButt, -1)
		staticButt.connect('clicked', self._toStaticCb)

		self._insertSep()
		self._insertSep()
		self._insertSep()


		panorButt = ToolButton('panoramio')
		panorButt.set_tooltip(Constants.istrPanoramio)
		self.insert(panorButt,-1)
		panorButt.connect('clicked', self._toPanoramioCb)

		self._insertSep()

		lwButt = ToolButton('localwiki')
		lwButt.set_tooltip(Constants.istrLocalWiki)
		self.insert(lwButt,-1)
		lwButt.connect('clicked', self._toLocalWikiCb)

	def _insertSep( self ):
		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)
		separator.set_expand(False)
		separator.set_size_request(25 + Constants.ui_dim_INSET, -1)
		self.insert( separator, -1 )

	def _webCb(self, button):
		#self.ca.browser.load_uri("http://maptonomy.appspot.com/maps4xo?ajaxPort=" + str(self.ca.__class__.ajaxPort) + "&cometPort=" + str(self.ca.__class__.cometPort) + "&xo=true&lat=" + str(self.ca.NOW_MAP_CENTER_LAT) + "&lng=" + str(self.ca.NOW_MAP_CENTER_LNG) + "&z=" + str(self.ca.NOW_MAP_ZOOM)  )
		self.ca.mapPaste()

	def _toPanoramioCb(self, button):
		self.emit("panoramio")

	def _toLocalWikiCb(self, button):
		self.emit("local-wiki")

	def _toWikiMapiaCb(self, button):
		self.emit("wikimapia")

	def _toStaticCb(self, button):
		#self.ca.browser.load_uri("http://maptonomy.appspot.com/ourmap.html?ajaxPort=" + str(self.ca.__class__.ajaxPort) + "&cometPort=" + str(self.ca.__class__.cometPort) + "&xo=true&lat=" + str(self.ca.NOW_MAP_CENTER_LAT) + "&lng=" + str(self.ca.NOW_MAP_CENTER_LNG) + "&zoom=" + str(self.ca.NOW_MAP_ZOOM)  )
		self.ca.googlePaste()

class ServerThread(threading.Thread):
	def __init__(self, port, logic):
		threading.Thread.__init__(self)
		self.server = Server( ("127.0.0.1", port), logic)

	def run(self):
		try:
			self.server.serve_forever()
		except:
			self.run()
