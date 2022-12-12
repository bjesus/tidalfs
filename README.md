# Tidal File System

TidalFS is a FUSE based file system that mounts the Tidal music streaming service as a local directory. All songs appear as local music files, and you can use any music player application to play them.

### Features

- [x] Search by artist, album, or track title
- [x] Favorites
- [x] Artist Top Tracks
- [x] Artist Radio
- [x] Similar Artists
- [ ] Playlists
- [ ] Recent searches
- [ ] Search using `mkdir`
- [ ] Mark as favorite (using `chmod`?)

## Using TidalFS

1. Clone it: `git clone` this repo
2. Install deps: `pip install -r requirements.txt`
3. Mount it: `python.py tidalfs.py /path/to/your/dir`

## Why?

I originally created TidalFS so I can use it inside [Home Assistant] Media Browser, since it only supports local files. However, you can use TidalFS to make any application able to use Tidal. You can also use it together with `rsync` to maintain a local backup of your favorite albums.
