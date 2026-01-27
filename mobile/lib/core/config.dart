import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Global configuration for the mobile app.
///
/// For V1 this focuses on determining the backend base URL for local
/// development and emulators. A simple static approach is used here, but this
/// can later be extended to load from persistent storage or remote config.
class Config {
  Config._();

  static const String _androidEmulatorBaseUrl = 'http://10.0.2.2:8000';
  static const String _iosSimulatorBaseUrl = 'http://localhost:8000';

  static late String _baseUrl;

  static String get baseUrl => _baseUrl;

  /// Initialize configuration based on the current platform.
  ///
  /// This should be called before [runApp] in `main.dart`.
  static void init() {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.iOS) {
      _baseUrl = _iosSimulatorBaseUrl;
    } else {
      _baseUrl = _androidEmulatorBaseUrl;
    }
  }

  /// Update the backend base URL at runtime (e.g., from SettingsScreen).
  static void updateBaseUrl(String url) {
    if (url.isEmpty) {
      return;
    }
    _baseUrl = url;
  }
}