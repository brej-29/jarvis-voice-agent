import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'logger.dart';

class NotificationService {
  NotificationService._();

  static final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  static Future<void> init() async {
    const AndroidInitializationSettings androidInitSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const InitializationSettings initSettings = InitializationSettings(
      android: androidInitSettings,
    );

    await _plugin.initialize(initSettings);
    Log.info('Local notifications initialized', tag: 'Notifications');
  }

  static Future<void> scheduleNotification({
    required String title,
    required String body,
    required DateTime scheduledFor,
  }) async {
    try {
      final details = NotificationDetails(
        android: AndroidNotificationDetails(
          'jarvis_reminders',
          'Jarvis Reminders',
          channelDescription: 'Local reminders scheduled by Jarvis.',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
        ),
      );

      await _plugin.zonedSchedule(
        scheduledFor.millisecondsSinceEpoch ~/ 1000,
        title,
        body,
        scheduledFor.toLocal().toUtc(),
        details,
        androidAllowWhileIdle: true,
        uiLocalNotificationDateInterpretation:
            UILocalNotificationDateInterpretation.absoluteTime,
        matchDateTimeComponents: DateTimeComponents.dateAndTime,
      );
    } catch (e, stackTrace) {
      Log.error(
        'Failed to schedule local notification',
        tag: 'Notifications',
        error: e,
        stackTrace: stackTrace,
      );
    }
  }
}