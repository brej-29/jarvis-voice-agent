import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/logger.dart';
import 'features/assistant/assistant_controller.dart';
import 'features/assistant/assistant_screen.dart';
import 'features/settings/settings_controller.dart';
import 'features/settings/settings_screen.dart';

class JarvisApp extends StatelessWidget {
  const JarvisApp({super.key});

  @override
  Widget build(BuildContext context) {
    Log.info('Starting JarvisApp', tag: 'App');

    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AssistantController()),
        ChangeNotifierProvider(create: (_) => SettingsController()),
      ],
      child: MaterialApp(
        title: 'Jarvis Voice Agent',
        theme: ThemeData(
          brightness: Brightness.dark,
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blueAccent,
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        home: const AssistantScreen(),
        routes: {
          SettingsScreen.routeName: (_) => const SettingsScreen(),
        },
      ),
    );
  }
}