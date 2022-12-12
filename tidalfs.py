#!/usr/bin/env python
# from __future__ import print_function, absolute_import, division
import tidalapi
import requests
import pickle
import tempfile
import threading
import os
import re
from pathlib import Path
from time import sleep
import logging
import stat

# from errno import ENOENT

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

SESSION_DATA_FILENAME = "session.data"
BASE_DIRS = ['.', '..']
ABC = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K','L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V','W', 'X', 'Y', 'Z']
CACHE_DIR = tempfile.TemporaryDirectory()
TRACKS_CACHE = {}
ALBUMS_CACHE = {}
DIRS_CACHE = {}
LINKS_CACHE = {}

def get_track_by_id(session, id, track_path):
    logging.info('get_track_by_id: id is '+ id)
    if os.path.exists(track_path):
        logging.debug("Already downloading it - not making another request")
        return
    else:
        logging.debug("Mark "+id+" as being downloaded")
        Path(track_path).touch()
    try:
        if int(id) in TRACKS_CACHE:
            track = TRACKS_CACHE[int(id)]
        else:
            track = session.track(track_id=id)
            TRACKS_CACHE[int(id)] = track
        url = track.get_url()
        logging.debug("download track")
        with requests.get(url, stream=True) as r:
            with open(track_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.debug("Done downloading track "+id)
        Path(track_path+".done").touch()
    except Exception as error:
        logging.error(error)
        os.remove(track_path)

def get_entries_for_path(path, session, ROOT_DIR):
    logging.info('get_entries_for_path:'+ path)

    if path == '/':
        return BASE_DIRS + ['Artist', 'Album', 'Track', 'Favorites', 'Searches', 'Last played']

    elif path == '/Favorites':
        return BASE_DIRS + ['Artists', 'Albums', 'Tracks']

    elif path == '/Favorites/Artists':
        dirs = []
        artists = tidalapi.user.Favorites(session, session.user.id).artists()
        for artist in artists:
            dir_name = artist.name.replace("/", "-")
            LINKS_CACHE[path+"/"+dir_name] = ROOT_DIR+"/.artists/"+str(artist.id)
            dirs.append(dir_name)
        return BASE_DIRS + dirs

    elif path == '/Favorites/Albums':
        dirs = []
        albums = tidalapi.user.Favorites(session, session.user.id).albums()
        for album in albums:
            dir_name = album.name.replace("/", "-")
            LINKS_CACHE[path+"/"+dir_name] = ROOT_DIR+"/.albums/"+str(album.id)
            dirs.append(dir_name)
        return BASE_DIRS + dirs

    elif path == '/Favorites/Tracks':
        files = []
        tracks = tidalapi.user.Favorites(session, session.user.id).tracks()
        for track in tracks:
            filename = track.name.replace("/", "-")+" ("+track.artist.name+").m4a"
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.trakcs/"+str(track.id)
            files.append(filename)
        return BASE_DIRS + files


 
    elif path in ['/Artist', '/Album', '/Track']:
        return BASE_DIRS + ABC
    elif path.endswith('/Search'):
        term = "".join(path.split('/')[2:-1]).replace("Space", " ").lower()
        logging.debug("Searching for "+term)

       
        search_types = {
                "Artist": tidalapi.artist.Artist,
                "Album": tidalapi.album.Album,
                "Track": tidalapi.Track
                }
        entity = path.split("/")[1]
        results = session.search(term, models=[search_types[entity]])
        logging.debug(results['albums'])
    
        dirs = []
        if entity == 'Artist':
            for artist in results['artists']:
                dir_name = artist.name.replace("/", "-")
                LINKS_CACHE[path+"/"+dir_name] = ROOT_DIR+"/.artists/"+str(artist.id)
                dirs.append(dir_name)
        if entity == 'Album':
            for album in results['albums']:
                dir_name = (album.name + " (" + album.artist.name +")").replace("/", "-")
                LINKS_CACHE[path+"/"+dir_name] = ROOT_DIR+"/.albums/"+str(album.id)
                dirs.append(dir_name)
        return BASE_DIRS + dirs

    elif path.startswith('/Album/') and ' - ' in path:
        id = path.split(" - ")[-1]
        album = session.album(album_id=id)
        tracks = album.tracks()
        for track in tracks:
            TRACKS_CACHE[track.id] = track

        return BASE_DIRS + [track.name +" (" +track.artist.name + ") - " + str(track.id)+".m4a"
        for track in tracks]

    elif any(p in path for p in ['/Artist/', '/Album/', '/Track/']):
        return BASE_DIRS + ["Search", 'Space'] +ABC

    elif path.startswith('/.albums/'):
        id = path.split("/")[-1]
        album = session.album(album_id=id)
        tracks = album.tracks()
        filenames = []
        for index, track in enumerate(tracks):
            filename = str(index+1).zfill(2)+" - " + track.name.replace("/", "-") +".m4a"
            TRACKS_CACHE[track.id] = track
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.tracks/"+str(track.id)+".m4a"
            filenames.append(filename)
        return BASE_DIRS + filenames

    elif re.match('/\.artists/\d+$', path):
        artist_options = ['Albums', 'EPs', 'Radio', 'Top Tracks', 'Similar Artists']
        return BASE_DIRS + artist_options

    elif re.match('^/\.artists/\d+/Albums$', path):
        id = path.split("/")[2]
        artist = session.artist(artist_id=id)
        albums = artist.get_albums()
        filenames = []
        for album in albums:
            filename = str(album.year)+" - "+album.name.replace("/", "-")
            ALBUMS_CACHE[album.id] = album
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.albums/"+str(album.id)
            filenames.append(filename)
        return BASE_DIRS + filenames

    elif re.match('^/\.artists/\d+/Albums$', path):
        id = path.split("/")[2]
        artist = session.artist(artist_id=id)
        albums = artist.get_albums_ep_singles()
        filenames = []
        for album in albums:
            filename = str(album.year)+" - "+album.name.replace("/", "-")
            ALBUMS_CACHE[album.id] = album
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.albums/"+str(album.id)
            filenames.append(filename)
        return BASE_DIRS + filenames

    elif re.match('^/\.artists/\d+/Top Tracks$', path):
        id = path.split("/")[2]
        artist = session.artist(artist_id=id)
        tracks = artist.get_top_tracks(limit=100)
        filenames = []
        for index, track in enumerate(tracks):
            filename = str(index+1).zfill(2)+". "+track.name.replace("/", "-") +".m4a"
            TRACKS_CACHE[track.id] = track
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.tracks/"+str(track.id)+".m4a"
            filenames.append(filename)
        return BASE_DIRS + filenames

    elif re.match('^/\.artists/\d+/Radio$', path):
        id = path.split("/")[2]
        artist = session.artist(artist_id=id)
        tracks = artist.get_radio()
        filenames = []
        for index, track in enumerate(tracks):
            filename = str(index+1).zfill(2)+ ". " + track.name.replace("/", "-") +" ("+track.artist.name+").m4a"
            TRACKS_CACHE[track.id] = track
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.tracks/"+str(track.id)+".m4a"
            filenames.append(filename)
        return BASE_DIRS + filenames

    elif re.match('^/\.artists/\d+/Similar Artists$', path):
        id = path.split("/")[2]
        artist = session.artist(artist_id=id)
        similar = artist.get_similar()
        filenames = []
        for index, artist in enumerate(similar):
            filename = artist.name.replace("/", "-")
            LINKS_CACHE[path+"/"+filename] = ROOT_DIR+"/.artists/"+str(artist.id)
            filenames.append(filename)
        return BASE_DIRS + filenames

    return BASE_DIRS



class Tidal(LoggingMixIn, Operations):
    '''
    A Tidal File System
    '''

    def __init__(self, root):
        self.ROOT_DIR = os.path.abspath(root)
        session = tidalapi.Session()
        try:
            with open(SESSION_DATA_FILENAME, 'rb') as out:
                data = pickle.load(out)
                logging.debug(data)
                logged_in = session.load_oauth_session(data['token_type'], data['access_token'], data['refresh_token'], data['expiry_time'])
                assert logged_in == True
        except:
            logging.warning("Old login data is invalid. Attempting to re-login.")
            session.login_oauth_simple()
            token_type = session.token_type
            access_token = session.access_token
            refresh_token = session.refresh_token # Not needed if you don't care about refreshing
            expiry_time = session.expiry_time
            with open(SESSION_DATA_FILENAME, 'wb') as out:
                pickle.dump({"token_type": token_type, "access_token": access_token, "refresh_token": refresh_token, "expiry_time":  expiry_time}, out)
        logging.debug("Current session is valid: "+str(session.check_login()))
        self.session = session

    def getattr(self, path, fh=None):
        base = {'st_atime': 1, 'st_gid': 1, 'st_mode': 16676, 'st_mtime': 1, 'st_size': 4096123, 'st_uid':1000 }

        if path.endswith('m4a'):
            if path.startswith('/.tracks/'):
                base['st_mode'] = 33060
            else:
                base['st_mode'] = stat.S_IFLNK

        if '/Search/' in path or path in LINKS_CACHE:
            base['st_mode'] = stat.S_IFLNK
       
        # else:
        #     return -errno.ENOENT
        # return st
        # # try:
        # #     st = self.sftp.lstat(path)
        # # except IOError:
        # #     raise FuseOSError(ENOENT)
        return base

    def read(self, path, size, offset, fh):
        if path[-3:] != 'm4a':
            return ''
        logging.info("read: "+path)
        id = path.split("/")[-1][:-4]
        track_path = CACHE_DIR.name+"/"+id+".m4a"
        t  = threading.Thread(target=get_track_by_id, args=(self.session, id, track_path,))
        t.start()
        while os.path.exists(track_path) == False:
            logging.debug('file does not exist: '+ track_path)
            sleep(0.01)

        with open(track_path, "rb") as infile:
            logging.debug("file is opened!")
            data = b''
            done = False
            while len(data) < size and done == False:
                sleep(0.01)
                logging.debug('Reading attempt: '+ id + " size: "+ str(size)+" offset: "+str(offset))
                infile.seek(offset)
                data = infile.read(size)
                if os.path.exists(track_path+".done"):
                    done = True
            logging.debug("got all the data i wanted")
            return data

    def readdir(self, path, fh):
        if path in DIRS_CACHE:
            entries = DIRS_CACHE[path]
        else:
            entries = get_entries_for_path(path, self.session, self.ROOT_DIR)
            DIRS_CACHE[path] = entries
        return entries

    def readlink(self, path):
        return LINKS_CACHE[path]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    fuse = FUSE(
        Tidal(args.mount),
        args.mount,
        foreground=True,
        nothreads=True)

