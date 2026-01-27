import 'package:flutter/material.dart';

import 'app.dart';
import 'core/config.dart';
import 'core/notifications.dart';
import 'core/storage.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  Config.init();
  await Storage.init();
  await NotificationService.init();
  runApp(const JarvisApp());
}