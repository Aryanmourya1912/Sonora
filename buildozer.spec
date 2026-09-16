[app]

# (str) Title of your application
title = Sonora

# (str) Package name (lowercase, no spaces)
package.name = sonora

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Presplash of the application
presplash.filename = %(source.dir)s/splash.png

# (str) Package domain (unique package identifier)
package.domain = org.app

# (str) Application versioning
version = 0.15

# (str) Source code directory
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,db,ogg,ttf

# (list) Application requirements
requirements = python3,kivy==2.2.1,kivymd==1.2.0,pillow,mutagen,yt-dlp,urllib3,requests,certifi,sqlite3,pyjnius

# (str) Supported orientation (locks 9:16 vertical display)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,WAKE_LOCK,POST_NOTIFICATIONS

# (int) Target Android API
android.api = 33

# (int) Minimum API supported
android.minapi = 21

# (int) Android NDK API to use (should match android.minapi)
android.ndk_api = 21

# (str) Android NDK version to use
android.ndk = 25b

# (list) The Android archs to build for
android.archs = arm64-v8a

# (bool) Accept SDK license automatically
android.accept_sdk_license = True

# (str) Lock python-for-android to stable release (prevents broken Python 3.14 build)
p4a.branch = v2024.01.21

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug with command output)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1