import os
from kivy.utils import platform

if platform == 'android':
    from jnius import PythonJavaClass, java_method, autoclass  # type: ignore

    class MediaSessionCallback(PythonJavaClass):
        __javainterfaces__ = ['android/media/session/MediaSession$Callback']
        __javacontext__ = 'app'

        def __init__(self, toggle_cb, next_cb, prev_cb):
            super().__init__()
            self.toggle_cb = toggle_cb
            self.next_cb = next_cb
            self.prev_cb = prev_cb

        @java_method('()V')
        def onPlay(self):
            if self.toggle_cb:
                self.toggle_cb()

        @java_method('()V')
        def onPause(self):
            if self.toggle_cb:
                self.toggle_cb()

        @java_method('()V')
        def onSkipToNext(self):
            if self.next_cb:
                self.next_cb()

        @java_method('()V')
        def onSkipToPrevious(self):
            if self.prev_cb:
                self.prev_cb()


class PlaybackNotificationManager:
    CHANNEL_ID = "music_player_channel"
    NOTIFICATION_ID = 1001

    ACTION_PREV = "org.app.sonora.ACTION_PREV"
    ACTION_TOGGLE = "org.app.sonora.ACTION_TOGGLE"
    ACTION_NEXT = "org.app.sonora.ACTION_NEXT"

    def __init__(self, on_toggle=None, on_next=None, on_prev=None):
        self.manager = None
        self.activity = None
        self.media_session = None
        self.session_callback = None
        self.available = False
        self.current_artwork_path = None

        self.on_toggle = on_toggle
        self.on_next = on_next
        self.on_prev = on_prev

        self._try_init()

    def _try_init(self) -> bool:
        if self.available and self.manager and self.activity:
            return True

        if platform != 'android':
            return False

        try:
            from jnius import autoclass, cast  # type: ignore

            self.autoclass = autoclass
            self.cast = cast

            self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
            self.Context = autoclass('android.content.Context')
            self.Intent = autoclass('android.content.Intent')
            self.PendingIntent = autoclass('android.app.PendingIntent')
            self.NotificationManager = autoclass('android.app.NotificationManager')
            self.NotificationChannel = autoclass('android.app.NotificationChannel')
            self.Notification = autoclass('android.app.Notification')
            self.NotificationBuilder = autoclass('android.app.Notification$Builder')
            self.MediaStyle = autoclass('android.app.Notification$MediaStyle')
            self.MediaSession = autoclass('android.media.session.MediaSession')
            self.MediaMetadata = autoclass('android.media.MediaMetadata')
            self.MediaMetadataBuilder = autoclass('android.media.MediaMetadata$Builder')
            self.PlaybackStateBuilder = autoclass('android.media.session.PlaybackState$Builder')
            self.PlaybackState = autoclass('android.media.session.PlaybackState')
            self.BitmapFactory = autoclass('android.graphics.BitmapFactory')
            self.R_drawable = autoclass('android.R$drawable')
            self.String = autoclass('java.lang.String')

            self.activity = self.PythonActivity.mActivity
            if self.activity:
                self.manager = self.activity.getSystemService(self.Context.NOTIFICATION_SERVICE)
                self._create_channel()

                if not self.media_session:
                    self.media_session = self.MediaSession(self.activity, self.String("SonoraSession"))
                    self.session_callback = MediaSessionCallback(self.on_toggle, self.on_next, self.on_prev)
                    self.media_session.setCallback(self.session_callback)
                    
                    # Crucial for Mini Capsule / Fluid Cloud: Links the session to your UI activity
                    self.media_session.setSessionActivity(self._get_content_pi())
                    self.media_session.setActive(True)

                self.available = True
                return True
        except Exception as err:
            print(f"[MediaSession / Notification Init Error] {err}")

        return False

    def _create_channel(self):
        try:
            j_channel_id = self.String(self.CHANNEL_ID)
            name = self.cast('java.lang.CharSequence', self.String("Playback Controls"))
            channel = self.NotificationChannel(j_channel_id, name, self.NotificationManager.IMPORTANCE_LOW)
            channel.setDescription(self.String("Shows active music controls on lock screen"))
            channel.setLockscreenVisibility(self.Notification.VISIBILITY_PUBLIC)
            self.manager.createNotificationChannel(channel)
        except Exception as e:
            print(f"[Notification Channel Error] {e}")

    def _update_playback_state(self, is_playing: bool, position_sec: float = 0.0):
        if not self.media_session:
            return
        try:
            state_builder = self.PlaybackStateBuilder()
            actions = (
                self.PlaybackState.ACTION_PLAY |
                self.PlaybackState.ACTION_PAUSE |
                self.PlaybackState.ACTION_PLAY_PAUSE |
                self.PlaybackState.ACTION_SKIP_TO_NEXT |
                self.PlaybackState.ACTION_SKIP_TO_PREVIOUS |
                self.PlaybackState.ACTION_SEEK_TO |
                self.PlaybackState.ACTION_STOP
            )
            state_builder.setActions(actions)
            state = self.PlaybackState.STATE_PLAYING if is_playing else self.PlaybackState.STATE_PAUSED
            state_builder.setState(state, int(position_sec * 1000), 1.0)
            self.media_session.setPlaybackState(state_builder.build())
        except Exception as e:
            print(f"[PlaybackState Error] {e}")

    def _update_media_metadata(self, title: str, artist: str, duration_sec: float, bitmap=None):
        """Pushes song metadata to Android MediaSession for Mini Capsule & Status Bar."""
        if not self.media_session:
            return
        try:
            builder = self.MediaMetadataBuilder()
            builder.putString(self.MediaMetadata.METADATA_KEY_TITLE, self.String(str(title or "Unknown Title")))
            builder.putString(self.MediaMetadata.METADATA_KEY_ARTIST, self.String(str(artist or "Unknown Artist")))
            builder.putString(self.MediaMetadata.METADATA_KEY_ALBUM, self.String("Sonora"))

            if duration_sec > 0:
                builder.putLong(self.MediaMetadata.METADATA_KEY_DURATION, int(duration_sec * 1000))

            if bitmap:
                builder.putBitmap(self.MediaMetadata.METADATA_KEY_ALBUM_ART, bitmap)

            self.media_session.setMetadata(builder.build())
        except Exception as e:
            print(f"[MediaMetadata Update Error] {e}")

    def _get_broadcast_pi(self, action_name: str, req_code: int):
        intent = self.Intent(action_name)
        intent.setPackage(self.activity.getPackageName())
        flags = 134217728 | 67108864
        return self.PendingIntent.getBroadcast(self.activity, req_code, intent, flags)

    def _get_content_pi(self):
        intent = self.Intent(self.activity, self.activity.getClass())
        intent.setFlags(self.Intent.FLAG_ACTIVITY_SINGLE_TOP)
        flags = 134217728 | 67108864
        return self.PendingIntent.getActivity(self.activity, 0, intent, flags)

    def show(self, title: str, artist: str, is_playing: bool = True, artwork_path: str = None, position_sec: float = 0.0, duration_sec: float = 0.0):
        if not self._try_init():
            return

        if artwork_path:
            self.current_artwork_path = artwork_path

        # 1. Update Playback State
        self._update_playback_state(is_playing, position_sec)

        # 2. Decode Bitmap (if present) and push full MediaMetadata
        decoded_bitmap = None
        if self.current_artwork_path and os.path.exists(self.current_artwork_path):
            try:
                decoded_bitmap = self.BitmapFactory.decodeFile(self.current_artwork_path)
            except Exception:
                decoded_bitmap = None

        self._update_media_metadata(title, artist, duration_sec, decoded_bitmap)

        # 3. Render System Notification
        try:
            builder = self.NotificationBuilder(self.activity, self.String(self.CHANNEL_ID))
            t_str = self.cast('java.lang.CharSequence', self.String(str(title or "Unknown Title")))
            a_str = self.cast('java.lang.CharSequence', self.String(str(artist or "Unknown Artist")))

            builder.setContentTitle(t_str)
            builder.setContentText(a_str)

            app_icon = self.activity.getApplicationInfo().icon
            builder.setSmallIcon(app_icon)

            if decoded_bitmap:
                builder.setLargeIcon(decoded_bitmap)

            builder.setContentIntent(self._get_content_pi())
            builder.setVisibility(self.Notification.VISIBILITY_PUBLIC)
            builder.setOngoing(is_playing)

            try:
                prev_icon = self.R_drawable.ic_media_previous
                toggle_icon = self.R_drawable.ic_media_pause if is_playing else self.R_drawable.ic_media_play
                next_icon = self.R_drawable.ic_media_next
            except Exception:
                prev_icon = app_icon
                toggle_icon = app_icon
                next_icon = app_icon

            builder.addAction(prev_icon, self.cast('java.lang.CharSequence', self.String("Previous")), self._get_broadcast_pi(self.ACTION_PREV, 1))
            builder.addAction(toggle_icon, self.cast('java.lang.CharSequence', self.String("Pause" if is_playing else "Play")), self._get_broadcast_pi(self.ACTION_TOGGLE, 2))
            builder.addAction(next_icon, self.cast('java.lang.CharSequence', self.String("Next")), self._get_broadcast_pi(self.ACTION_NEXT, 3))

            media_style = self.MediaStyle()
            if self.media_session:
                media_style.setMediaSession(self.media_session.getSessionToken())

            try:
                from jnius import jarray  # type: ignore
                media_style.setShowActionsInCompactView(jarray('i')([0, 1, 2]))
            except Exception:
                media_style.setShowActionsInCompactView([0, 1, 2])

            builder.setStyle(media_style)
            self.manager.notify(self.NOTIFICATION_ID, builder.build())
        except Exception as e:
            print(f"[MediaStyle Notification Error] {e}")

    def cancel(self):
        if self.available and self.manager:
            try:
                self.manager.cancel(self.NOTIFICATION_ID)
            except Exception:
                pass
        if self.media_session:
            try:
                self.media_session.setActive(False)
            except Exception:
                pass

    def release(self):
        self.cancel()
        if self.media_session:
            try:
                self.media_session.release()
                self.media_session = None
            except Exception:
                pass