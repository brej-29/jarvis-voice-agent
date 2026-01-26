import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/config.dart';
import '../../core/errors.dart';
import '../../core/logger.dart';
import 'assistant_models.dart';

class AssistantService {
  AssistantService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<String> sendChat({
    required String sessionId,
    required List<AssistantMessage> history,
    required ResponseStyle responseStyle,
  }) async {
    final uri = Uri.parse('${Config.baseUrl}/chat');

    final payload = <String, dynamic>{
      'session_id': sessionId,
      'messages': history.map((m) => m.toJson()).toList(),
      'client': <String, dynamic>{
        'platform': 'android', // Adjusted by platform if needed in future
        'app_version': '0.1.0',
      },
      'settings': <String, dynamic>{
        'response_style': responseStyle.name,
      },
    };

    try {
      Log.info('Sending /chat request to ${Config.baseUrl}', tag: 'AssistantService');
      final response = await _client.post(
        uri,
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );

      if (response.statusCode != 200) {
        throw NetworkException(
          'Backend returned status ${response.statusCode}',
        );
      }

      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      final replyText = decoded['reply_text'] as String?;
      if (replyText == null || replyText.isEmpty) {
        throw NetworkException('Invalid response from backend (missing reply_text)');
      }

      return replyText;
    } catch (e, stackTrace) {
      Log.error(
        'Failed to call backend /chat',
        tag: 'AssistantService',
        error: e,
        stackTrace: stackTrace,
      );
      if (e is AppException) {
        rethrow;
      }
      throw NetworkException('Unable to reach backend. Please try again.');
    }
  }

  void dispose() {
    _client.close();
  }
}