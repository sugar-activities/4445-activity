# Copyright (c) 2008, Media Modifications Ltd.

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


from result import ServerResult
from constants import Constants
from instance import Instance

from threading import Thread
import threading
import os
import gobject
import time
import gtk
import urllib

class ServerLogic:
	def __init__(self, ca):
		self.ca = ca
		self.proceedTxt = ""
		self.proceedHeaders = []
		self.cond = ca.cond
		self.addKMLSet=0

	def doServerLogic(self, url, path, params):
		self.ca.remoteServerActive( True )
		r = ServerResult()
		fileName = path[len(path)-1]

		if (fileName == "comet.js"):

			#clear...
			self.proceedHeaders = []
			self.proceedTxt = ""

			#wait...
			self.cond.acquire()
			self.cond.wait()
			self.cond.release()

			#prep response...
			for h in range( len(self.proceedHeaders) ):
				r.headers.append( self.proceedHeaders[h] )
			r.txt = ""  #+self.proceedTxt

		else:
			kickThroughComet = True

			if (fileName =="mediaQuery.js"):
				
				self.proceedTxt = self.ca.m.getMediaResponse( params[0][1], params[1][1], params[2][1], params[3][1] )
				time.sleep(1)
				gobject.idle_add(self.ca.browser.load_uri,"javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

			elif (fileName == "showMedia.js"):
				id = params[0][1]
				locX = params[1][1]
				locY = params[2][1]
				up = params[3][1]
				rt = params[4][1]
				gobject.idle_add(self.ca.showMedia, id, locX, locY, up=='true', rt=='true')
				self.proceedHeaders.append( ("Content-type", "text/javascript") )

			elif (fileName == "placeAddMedia.js"):
				lat = params[0][1]
				lng = params[1][1]
				gobject.idle_add(self.ca.placeAddMedia, lat, lng)
				self.proceedHeaders.append( ("Content-type", "text/javascript") )
				kickThroughComet = False

			elif (fileName == "hideMedia.js"):
				gobject.idle_add(self.ca.hideMedia)

			elif (fileName == "loadLibMap.js"):
				id = params[0][1]
				# match id to KML link
				kmlfiles = {"0":"/home/olpc/Activities/OfflineMaps.activity/MapPack/kml/UY-Departamentos.kml","1":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/UY-hydro.kml","2":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/Guarani.kml","3":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/lobosmarinos.kml","4":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/CiudadVieja.kml","5":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/IslaDelCoco.kml","6":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/AreasProtegidas.kml","7":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/UNEP-enviro.kml","8":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/Surui.kml","9":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/Petrobras-BioMap.kml","10":None,"11":"file:///home/olpc/Activities/OfflineMaps.activity/MapPack/kml/TradeMap.kml","12":None}
				if(kmlfiles[id] is not None):
					# send this file to KML parser
					gobject.idle_add(self.ca.readKML,open(kmlfiles[id].replace('file://',''),'r'),False)

			elif (fileName == "getImage.js"):
				localfile = open(os.path.join(Instance.instancePath, params[0][1]), 'r')
				localdata = localfile.read()
				localfile.close()

				#one day we might need to kick you through comet as a base64'd image.
				r.txt = localdata
				r.headers.append( ("Content-type", "image/jpeg") )
				kickThroughComet = False

			elif (fileName == "updateLocation.js"):
				lat = params[0][1]
				lng = params[1][1]
				zoom = params[2][1]
				x = params[3][1]
				y = params[4][1]
				gobject.idle_add(self.ca.updateMapMetaData,lat,lng,zoom,x,y)

			elif (fileName == "addSavedMap.js"):
				# allow internet to send an array of SavedMaps back to map.py
				latitudes = params[0][1]
				longitudes = params[1][1]
				zooms = params[2][1]
				notes = params[3][1]
				gobject.idle_add(self.ca.addSavedMap,latitudes,longitudes,zooms,urllib.unquote(notes),True)

			elif (fileName == "addInfoMarker.js"):
				lat = params[0][1]
				lng = params[1][1]
				info = params[2][1]
				icon = params[3][1]
				if(params[4][1] == "True"):
					isNew = True
				else:
					isNew = False
				gobject.idle_add(self.ca.addInfoMarker,lat,lng,info,icon,isNew)
			
			elif (fileName == "addLine.js"):
				id = params[0][1]
				color = params[1][1]
				thickness = params[2][1]
				pts = params[3][1]  # send pts separated with | instead of ,
				gobject.idle_add(self.ca.addLine,id,color,thickness,pts,1)
			
			elif (fileName == "joinGroup.js"):
				groupName = params[0][1]
				groupFile = urllib.urlopen("http://bluebird-science.appspot.com/group/data?name=" + groupName)
				self.ca.preComet()
				self.handleGroupData(groupFile.readline())
				self.ca.postComet()
			
			elif (fileName == "promptSearch.js"):
				address = params[0][1]
				time.sleep(0.5)
				self.ca.preComet()
				self.handleAddressUpdate(address+"+")
				self.ca.postComet()

			#elif (fileName == "gotoMapV3.js"):
				# button on static maps links to mapv3
				#self.ca.loadMapV3()

			if (kickThroughComet):
				#not sure how & why this goes out, but it does.
				self.cond.acquire()
				self.cond.notifyAll()
				self.cond.release()
				time.sleep(.1)

		return r

	def handleAddressUpdate( self, address ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "moveTo(" + address + ");"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")
	
	def handleGroupData( self, groupData ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "joinThisGroup(" + groupData + ");"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleCompassUpdate( self, dir ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )

		if (dir == "e"):
			self.proceedTxt = "dirEast();"
		elif (dir == "w"):
			self.proceedTxt = "dirWest();"
		elif (dir == "n"):
			self.proceedTxt = "dirNorth();"
		elif (dir == "s"):
			self.proceedTxt = "dirSouth();"
		else:
			# use this as a print warning window
			self.proceedTxt = 'showInfo("' + dir + '");'
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleLibraryView( self ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.ca.browser.load_uri("javascript:showLibrary();void(0);")

	def handleZoomUpdate( self, dir ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		if (dir == "+"):
			self.proceedTxt = "zoomIn();"
		elif (dir == "-"):
			self.proceedTxt = "zoomOut();"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleClear( self ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "clear();"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handlePreAdd( self ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "preAddMedia();"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handlePreAddInfo( self ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "preAddInfo();"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handlePostAdd( self, rec  ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "postAddMedia(" + rec.latitude + ", " + rec.longitude + ", '" + rec.getThumbUrl() + "', '" + rec.getThumbBasename() + "', '" + rec.tags + "');"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleDelete( self ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "deleteMedia();"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	# handle a map that was sent to us
	def handleReceivedMap( self, lat, lng, zoom):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "moveTo(" + lat + "," + lng + "," + zoom + ");"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleSavedMap( self, lat, lng, zoom, info ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		if(info.find("Describe the map") != 0):
			self.proceedTxt = "setMap2(" + lat + "," + lng + "," + zoom + ",'" + urllib.quote(info) + "');"
		else:
			self.proceedTxt = "setMap2(" + lat + "," + lng + "," + zoom + ",'');"			
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	# handle a marker that was sent to us
	def handleAddMarker( self, lat, lng, pixString, icon ):
		if(self.addKMLSet < 1):
			self.proceedHeaders.append( ("Content-type", "text/javascript") )
			self.proceedTxt = ""
                        if(self.addKMLSet == -1):
				self.addKMLSet = 1
		self.proceedTxt = self.proceedTxt + "addPt(" + lat + ", " + lng + ", '" + pixString.decode('utf-8').replace("'","\\'") + "', '" + icon + "',false);"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt+";void(0);")

	def mapPaste( self, type ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "mapPaste('" + type + "');"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def startKML( self, tellOthers ):
		self.addKMLSet = -1
		if((self.ca.maptube is not None) and (tellOthers == 1)):
			self.ca.sendStartKML()
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleEndKML( self, tellOthers ):
		self.addKMLSet = 0
		if((self.ca.maptube is not None) and (tellOthers == 1)):
			self.ca.sendEndKML()
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def lineMode(self, type):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "lineMode('" + type + "',true);"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handlePanoramio(self):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = 'panoramio();'
		self.ca.browser.load_uri("javascript:"+self.proceedTxt+";void(0);")

	def handleLocalWiki(self):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = 'wikiloc();'
		self.ca.browser.load_uri("javascript:"+self.proceedTxt+";void(0);")

	def handleWikiMapia(self):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = 'wikimapia();'
		self.ca.browser.load_uri("javascript:"+self.proceedTxt+";void(0);")

	def handleLine(self,id,color,thickness,pts,drawNow):
		if(self.addKMLSet < 1):
			self.proceedHeaders.append( ("Content-type", "text/javascript") )
			self.proceedTxt = ""
			if(self.addKMLSet == -1):
				self.addKMLSet = 1
		self.proceedTxt = self.proceedTxt + "addLine('" + id + "','" + color + "','" + thickness + "','" + pts + "'," + drawNow + ");"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleLine(self,id,color,thickness,pts,placename,drawNow):
		if(self.addKMLSet < 1):
			self.proceedHeaders.append( ("Content-type", "text/javascript") )
			self.proceedTxt = ""
			if(self.addKMLSet == -1):
				self.addKMLSet = 1
		self.proceedTxt = self.proceedTxt + "addNamedLine('" + id + "','" + color + "','" + thickness + "','" + pts + "','"+placename.replace('"','\\"')+"',"+drawNow+");"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	# handle start of measure tool
	def handleMeasure(self):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "measure();"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")

	def handleTagSearch( self, tags ):
		self.proceedHeaders.append( ("Content-type", "text/javascript") )
		self.proceedTxt = "filterTags('" + tags + "');"
		self.ca.browser.load_uri("javascript:"+self.proceedTxt.decode('utf-8')+";void(0);")
