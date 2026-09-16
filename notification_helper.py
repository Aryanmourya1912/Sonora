import os
from kivy.utils import platform


class PlaybackNotificationManager:
    CHANNEL_ID = "music_player_channel"
    NOTIFICATION_ID = 1001

    ACTION_PREV = "org.app.sonora.ACTION_PREV"
    ACTION_TOGGLE = "org.app.sonora.ACTION_TOGGLE"
    ACTION_NEXT = "org.app.sonora.ACTION_NEXT"

    def __init__(self):
        self.manager = None
        self.activity = None
        self.available = False
        self._try_init()

    def _try_init(self) -> bool:
        """Initializes or re-binds to Android system services when Activity is ready."""
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
            self.R_drawable = autoclass('android.R$drawable')
            self.String = autoclass('java.lang.String')

            self.activity = self.PythonActivity.mActivity
            if self.activity:
                self.manager = self.activity.getSystemService(self.Context.NOTIFICATION_SERVICE)
                self._create_channel()
                self.available = True
                return True
        except Exception as err:
            print(f"[Notification Init Error] {err}")

        return False

    def _create_channel(self):
        try:
            j_channel_id = self.String(self.CHANNEL_ID)
            name = self.cast('java.lang.CharSequence', self.String("Playback Controls"))
            channel = self.NotificationChannel(
                j_channel_id,
                name,
                self.NotificationManager.IMPORTANCE_LOW
            )
            channel.setDescription(self.String("Shows active music controls on lock screen"))
            channel.setLockscreenVisibility(self.Notification.VISIBILITY_PUBLIC)
            self.manager.createNotificationChannel(channel)
        except Exception as e:
            print(f"[Notification Channel Error] {e}")

    def _get_broadcast_pi(self, action_name: str, req_code: int):
        intent = self.Intent(action_name)
        intent.setPackage(self.activity.getPackageName())
        # FLAG_UPDATE_CURRENT (134217728) | FLAG_IMMUTABLE (67108864) for Android 12+
        flags = 134217728 | 67108864
        return self.PendingIntent.getBroadcast(self.activity, req_code, intent, flags)

    def _get_content_pi(self):
        intent = self.Intent(self.activity, self.activity.getClass())
        intent.setFlags(self.Intent.FLAG_ACTIVITY_SINGLE_TOP)
        flags = 134217728 | 67108864
        return self.PendingIntent.getActivity(self.activity, 0, intent, flags)

    def show(self, title: str, artist: str, is_playing: bool = True):
        if not self._try_init():
            return

        try:
            builder = self.NotificationBuilder(self.activity, self.String(self.CHANNEL_ID))

            t_str = self.cast('java.lang.CharSequence', self.String(str(title or "Unknown Title")))
            a_str = self.cast('java.lang.CharSequence', self.String(str(artist or "Unknown Artist")))

            builder.setContentTitle(t_str)
            builder.setContentText(a_str)

            # Using app's own icon guarantees Android won't drop the notification
            app_icon = self.activity.getApplicationInfo().icon
            builder.setSmallIcon(app_icon)

            builder.setContentIntent(self._get_content_pi())
            builder.setVisibility(self.Notification.VISIBILITY_PUBLIC)
            builder.setOngoing(is_playing)

            # Resolve playback icons with safe fallback
            try:
                prev_icon = self.R_drawable.ic_media_previous
                toggle_icon = self.R_drawable.ic_media_pause if is_playing else self.R_drawable.ic_media_play
                next_icon = self.R_drawable.ic_media_next
            except Exception:
                prev_icon = app_icon
                toggle_icon = app_icon
                next_icon = app_icon

            # 1. Previous Button
            prev_label = self.cast('java.lang.CharSequence', self.String("Previous"))
            builder.addAction(prev_icon, prev_label, self._get_broadcast_pi(self.ACTION_PREV, 1))

            # 2. Play / Pause Button
            toggle_label = self.cast('java.lang.CharSequence', self.String("Pause" if is_playing else "Play"))
            builder.addAction(toggle_icon, toggle_label, self._get_broadcast_pi(self.ACTION_TOGGLE, 2))

            # 3. Next Button
            next_label = self.cast('java.lang.CharSequence', self.String("Next"))
            builder.addAction(next_icon, next_label, self._get_broadcast_pi(self.ACTION_NEXT, 3))

            self.manager.notify(self.NOTIFICATION_ID, builder.build())
        except Exception as e:
            print(f"[Notification Show Error] {e}")

    def cancel(self):
        if self.available and self.manager:
            try:
                self.manager.cancel(self.NOTIFICATION_ID)
            except Exception:
                pass