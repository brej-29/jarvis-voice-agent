import 'package:flutter/material.dart';

import 'app.dart';
import 'core/config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  Config.init();
  runApp(const JarvisApp());
}