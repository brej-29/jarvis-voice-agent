import 'package:flutter/material.dart';

import '../../core/config.dart';
import '../../core/logger.dart';
import '../assistant/assistant_models.dart';

class SettingsController extends ChangeNotifier {
  ResponseStyle responseStyle = ResponseStyle.normal;
  double ttsRate = 0.5;
  String backendBaseUrl = Config.baseUrl;

  void setResponseStyle(ResponseStyle style) {
    responseStyle = style;
    Log.info('Response style updated to ${style.name}', tag: 'SettingsController');
    notifyListeners();
  }

  void setTtsRate(double rate) {
    ttsRate = rate;
    Log.info('TTS rate updated to $rate', tag: 'SettingsController');
    notifyListeners();
  }

  void setBackendBaseUrl(String url) {
    if (url.isEmpty) {
      return;
    }
    backendBaseUrl = url;
    Config.updateBaseUrl(url);
    Log.info('Backend base URL updated to $url', tag: 'SettingsController');
    notifyListeners();
  }
}