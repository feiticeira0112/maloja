from ..globalconf import data_dir, malojaconfig
from .. import thirdparty

from doreah import caching
from doreah.logging import log

import itertools
import os
import urllib
import random
import base64
from threading import Thread, Timer
import re
import datetime





### Caches

cacheage = malojaconfig["CACHE_EXPIRE_POSITIVE"] * 24 * 3600
cacheage_neg = malojaconfig["CACHE_EXPIRE_NEGATIVE"] * 24 * 3600

artist_cache = caching.Cache(name="imgcache_artists",maxage=cacheage,maxage_negative=cacheage_neg,persistent=True)
track_cache = caching.Cache(name="imgcache_tracks",maxage=cacheage,maxage_negative=cacheage_neg,persistent=True)


# removes emojis and weird shit from names
def clean(name):
	return "".join(c for c in name if c.isalnum() or c in []).strip()

def get_all_possible_filenames(artist=None,artists=None,title=None):
	# check if we're dealing with a track or artist, then clean up names
	# (only remove non-alphanumeric, allow korean and stuff)

	if title is not None and artists is not None:
		track = True
		title, artists = clean(title), [clean(a) for a in artists]
	elif artist is not None:
		track = False
		artist = clean(artist)
	else: return []


	superfolder = "tracks/" if track else "artists/"

	filenames = []

	if track:
		#unsafeartists = [artist.translate(None,"-_./\\") for artist in artists]
		safeartists = [re.sub("[^a-zA-Z0-9]","",artist) for artist in artists]
		#unsafetitle = title.translate(None,"-_./\\")
		safetitle = re.sub("[^a-zA-Z0-9]","",title)

		if len(artists) < 4:
			unsafeperms = itertools.permutations(artists)
			safeperms = itertools.permutations(safeartists)
		else:
			unsafeperms = [sorted(artists)]
			safeperms = [sorted(safeartists)]


		for unsafeartistlist in unsafeperms:
			filename = "-".join(unsafeartistlist) + "_" + title
			if filename != "":
				filenames.append(filename)
				filenames.append(filename.lower())
		for safeartistlist in safeperms:
			filename = "-".join(safeartistlist) + "_" + safetitle
			if filename != "":
				filenames.append(filename)
				filenames.append(filename.lower())
		filenames = list(set(filenames))
		if len(filenames) == 0: filenames.append(str(hash((frozenset(artists),title))))
	else:
		#unsafeartist = artist.translate(None,"-_./\\")
		safeartist = re.sub("[^a-zA-Z0-9]","",artist)

		filename = artist
		if filename != "":
			filenames.append(filename)
			filenames.append(filename.lower())
		filename = safeartist
		if filename != "":
			filenames.append(filename)
			filenames.append(filename.lower())

		filenames = list(set(filenames))
		if len(filenames) == 0: filenames.append(str(hash(artist)))

	return [superfolder + name for name in filenames]

def local_files(artist=None,artists=None,title=None):


	filenames = get_all_possible_filenames(artist,artists,title)

	images = []

	for purename in filenames:
		# direct files
		for ext in ["png","jpg","jpeg","gif"]:
			#for num in [""] + [str(n) for n in range(0,10)]:
			if os.path.exists(data_dir['images'](purename + "." + ext)):
				images.append("/images/" + purename + "." + ext)

		# folder
		try:
			for f in os.listdir(data_dir['images'](purename)):
				if f.split(".")[-1] in ["png","jpg","jpeg","gif"]:
					images.append("/images/" + purename + "/" + f)
		except:
			pass

	return images



# these caches are there so we don't check all files every time, but return the same one
local_cache_age = malojaconfig["LOCAL_IMAGE_ROTATE"]
local_artist_cache = caching.Cache(maxage=local_cache_age)
local_track_cache = caching.Cache(maxage=local_cache_age)

def getTrackImage(artists,title,fast=False):

	hashable_track = (frozenset(artists),title)

	# Prio 1: Local image
	if malojaconfig["USE_LOCAL_IMAGES"]:
		try:
			return local_track_cache.get(hashable_track)
		except:
			images = local_files(artists=artists,title=title)
			if len(images) != 0:
				res = random.choice(images)
				local_track_cache.add(hashable_track,res)
				return urllib.parse.quote(res)


	# Prio 2: Cached remote link
	try:
		result = track_cache.get(hashable_track)
		if result is not None: return result
		# if we have cached the nonexistence of that image, we immediately return
		# the redirect to the artist and let the resolver handle it
		# (even if we're not in a fast lookup right now)
		for a in artists:
			res = getArtistImage(artist=a,fast=True)
			if res != "": return res
		return ""
	except:
		pass


	# fast request will not go further than this, but now generate redirect link
	if fast:
		return ("/image?title=" + urllib.parse.quote(title) + "&" + "&".join(
		    "artist=" + urllib.parse.quote(a) for a in artists))


	# Prio 3 (only non-fast lookup): actually call third parties
	result = thirdparty.get_image_track_all((artists,title))
	# cache results (even negative ones)
	track_cache.add(hashable_track,result)
	# return either result or redirect to artist
	if result is not None: return result
	for a in artists:
		res = getArtistImage(artist=a,fast=False)
		if res != "": return res
	return ""


def getArtistImage(artist,fast=False):

	# Prio 1: Local image
	if malojaconfig["USE_LOCAL_IMAGES"]:
		try:
			return local_artist_cache.get(artist)
		except:
			images = local_files(artist=artist)
			if len(images) != 0:
				res = random.choice(images)
				local_artist_cache.add(artist,res)
				return urllib.parse.quote(res)


	# Prio 2: Cached remote link
	try:
		result = artist_cache.get(artist)
		if result is not None: return result
		else: return ""
		# none means non-existence is cached, return empty
	except:
		pass
		# no cache entry, go on


	# fast request will not go further than this, but now generate redirect link
	if fast: return "/image?artist=" + urllib.parse.quote(artist)


	# Prio 3 (only non-fast lookup): actually call third parties
	result = thirdparty.get_image_artist_all(artist)
	# cache results (even negative ones)
	artist_cache.add(artist,result) #cache_artist(artist,result)
	if result is not None: return result
	else: return ""

def getTrackImages(trackobjectlist,fast=False):

	threads = []

	for track in trackobjectlist:
		t = Thread(target=getTrackImage,args=(track["artists"],track["title"],),kwargs={"fast":fast})
		t.start()
		threads.append(t)

	for t in threads:
		t.join()


	return [getTrackImage(t["artists"],t["title"]) for t in trackobjectlist]

def getArtistImages(artistlist,fast=False):

	threads = []

	for artist in artistlist:
		t = Thread(target=getArtistImage,args=(artist,),kwargs={"fast":fast})
		t.start()
		threads.append(t)

	for t in threads:
		t.join()

	# async calls only cached results, now we need to get them
	return [getArtistImage(a) for a in artistlist]



# new way of serving images
# instead always generate a link locally, but redirect that on the fly
# this way the page can load faster and images will trickle in without having to resort to XHTTP requests

def resolveImage(artist=None,track=None):
	if track is not None:
		return getTrackImage(track["artists"],track["title"])
	elif artist is not None:
		return getArtistImage(artist)







def set_image(b64,**keys):
	track = "title" in keys

	log("Trying to set image, b64 string: " + str(b64[:30] + "..."),module="debug")

	regex = r"data:image/(\w+);base64,(.+)"
	type,b64 = re.fullmatch(regex,b64).groups()
	b64 = base64.b64decode(b64)
	filename = "webupload" + str(int(datetime.datetime.now().timestamp())) + "." + type
	for folder in get_all_possible_filenames(**keys):
		if os.path.exists(data_dir['images'](folder)):
			with open(data_dir['images'](folder,filename),"wb") as f:
				f.write(b64)
			break
	else:
		folder = get_all_possible_filenames(**keys)[0]
		os.makedirs(data_dir['images'](folder))
		with open(data_dir['images'](folder,filename),"wb") as f:
			f.write(b64)

	log("Saved image as " + data_dir['images'](folder,filename),module="debug")

	# set as current picture in rotation
	if track: local_track_cache.add((frozenset(keys["artists"]),keys["title"]),os.path.join("/images",folder,filename))
	else: local_artist_cache.add(keys["artist"],os.path.join("/images",folder,filename))
