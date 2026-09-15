import os
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    Intent = autoclass('android.content.Intent')
    PendingIntent = autoclass('android.app.PendingIntent')
    NotificationManager = autoclass('android.app.NotificationManager')
    NotificationChannel = autoclass('android.app.NotificationChannel')
    Notification = autoclass('android.app.Notification')
    NotificationBuilder = autoclass('android.app.Notification$Builder')
    R_drawable = autoclass('android.R$drawable')
else:
    PythonActivity = None


class PlaybackNotificationManager:
    CHANNEL_ID = "music_player_channel"
    NOTIFICATION_ID = 1001

    ACTION_PREV = "org.app.sonora.ACTION_PREV"
    ACTION_TOGGLE = "org.app.sonora.ACTION_TOGGLE"
    ACTION_NEXT = "org.app.sonora.ACTION_NEXT"

    def __init__(self):
        self.manager = None
        self.activity = None
        if platform == 'android':
            self.activity = PythonActivity.mActivity
            self.manager = self.activity.getSystemService(Context.NOTIFICATION_SERVICE)
            self._create_channel()

    def _create_channel(self):
        try:
            # Importance LOW (2) ensures controls appear without an intrusive sound on each track change
            channel = NotificationChannel(
                self.CHANNEL_ID,
                "Playback Controls",
                NotificationManager.IMPORTANCE_LOW
            )
            channel.setDescription("Shows active music controls on lock screen")
            channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC)
            self.manager.createNotificationChannel(channel)
        except Exception as e:
            print(f"[Notification Channel Error] {e}")

    def _get_broadcast_pi(self, action_name: str, req_code: int):
        intent = Intent(action_name)
        intent.setPackage(self.activity.getPackageName())
        # FLAG_UPDATE_CURRENT (134217728) | FLAG_IMMUTABLE (67108864) for Android 12+
        flags = 134217728 | 67108864
        return PendingIntent.getBroadcast(self.activity, req_code, intent, flags)

    def _get_content_pi(self):
        # Tapping the notification body brings the app back to the foreground
        intent = Intent(self.activity, PythonActivity)
        intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        flags = 134217728 | 67108864
        return PendingIntent.getActivity(self.activity, 0, intent, flags)

    def show(self, title: str, artist: str, is_playing: bool = True):
        if platform != 'android' or not self.manager:
            return

        try:
            builder = NotificationBuilder(self.activity, self.CHANNEL_ID)
            builder.setContentTitle(str(title or "Unknown Title"))
            builder.setContentText(str(artist or "Unknown Artist"))
            builder.setSmallIcon(R_drawable.ic_media_play)
            builder.setContentIntent(self._get_content_pi())
            
            # VISIBILITY_PUBLIC (1) shows song title and controls on the lockscreen
            builder.setVisibility(Notification.VISIBILITY_PUBLIC)
            builder.setOngoing(is_playing)

            # 1. Previous Button
            builder.addAction(
                R_drawable.ic_media_previous,
                "Previous",
                self._get_broadcast_pi(self.ACTION_PREV, 1)
            )

            # 2. Play / Pause Button
            toggle_icon = R_drawable.ic_media_pause if is_playing else R_drawable.ic_media_play
            toggle_text = "Pause" if is_playing else "Play"
            builder.addAction(
                toggle_icon,
                toggle_text,
                self._get_broadcast_pi(self.ACTION_TOGGLE, 2)
            )

            # 3. Next Button
            builder.addAction(
                R_drawable.ic_media_next,
                "Next",
                self._get_broadcast_pi(self.ACTION_NEXT, 3)
            )

            self.manager.notify(self.NOTIFICATION_ID, builder.build())
        except Exception as e:
            print(f"[Notification Show Error] {e}")

    def cancel(self):
        if platform == 'android' and self.manager:
            try:
                self.manager.cancel(self.NOTIFICATION_ID)
            except Exception:
                pass