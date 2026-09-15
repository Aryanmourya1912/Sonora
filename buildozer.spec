[app]
title = Music Player
package.name = musicplayer
package.domain = org.app
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,ogg,ttf
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,mutagen,yt-dlp,urllib3,requests,certifi,sqlite3
android.permissions = IN[app]

# (str) Title of your application
title = Music Player

# (str) Package name
package.name = musicplayer

# (str) Package domain (unique package identifier)
package.domain = org.app

# (str) Application versioning
version = 0.3

# (str) Source code directory
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,db,ogg,ttf

# (list) Application requirements (without pygame)
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,mutagen,yt-dlp,urllib3,requests,certifi,sqlite3,pyjnius

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# (int) Target Android API
android.api = 33

# (int) Minimum API supported
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) Supported orientation
orientation = portrait

# (list) The Android archs to build for
android.archs = arm64-v8a

# (bool) Accept SDK license automatically
android.accept_sdk_license = TrueTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True