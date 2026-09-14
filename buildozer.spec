[app]
title = Music Player
package.name = musicplayer
package.domain = org.app
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,ogg,ttf
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,pygame,mutagen,yt-dlp,urllib3,requests,certifi,sqlite3
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
