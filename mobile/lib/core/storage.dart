import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';

import '../features/assistant/assistant_models.dart';
import 'logger.dart';

class Storage {
  Storage._();

  static const String _conversationsBoxName = 'conversations';
  static const String _notesBoxName = 'notes';

  static late Box<String> _conversationsBox;
  static late Box<String> _notesBox;

  static Future<void> init() async {
    await Hive.initFlutter();
    _conversationsBox = await Hive.openBox<String>(_conversationsBoxName);
    _notesBox = await Hive.openBox<String>(_notesBoxName);
    Log.info('Hive storage initialized', tag: 'Storage');
  }

  /// Persist the full conversation history for a session as JSON.
  static Future<void> saveConversation(
    String sessionId,
    List<AssistantMessage> messages,
  ) async {
    final jsonList = messages
        .map(
          (m) => <String, dynamic>{
            'role': m.role,
            'content': m.content,
            'ts': m.timestamp.toIso8601String(),
          },
        )
        .toList();
    await _conversationsBox.put(sessionId, jsonEncode(jsonList));
  }

  static List<AssistantMessage> loadConversation(String sessionId) {
    final raw = _conversationsBox.get(sessionId);
    if (raw == null) {
      return <AssistantMessage>[];
    }
    try {
      final List<dynamic> decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .map(
            (item) => AssistantMessage(
              role: item['role'] as String,
              content: item['content'] as String,
              timestamp: DateTime.parse(item['ts'] as String),
            ),
          )
          .toList();
    } catch (e) {
      Log.error(
        'Failed to decode conversation for $sessionId',
        tag: 'Storage',
        error: e,
      );
      return <AssistantMessage>[];
    }
  }

  /// Save a note record as JSON.
  static Future<void> saveNote(Map<String, dynamic> note) async {
    final id = DateTime.now().toIso8601String();
    await _notesBox.put(id, jsonEncode(note));
  }

  static List<Map<String, dynamic>> loadNotes() {
    final List<Map<String, dynamic>> notes = <Map<String, dynamic>>[];
    for (final value in _notesBox.values) {
      try {
        final decoded = jsonDecode(value) as Map<String, dynamic>;
        notes.add(decoded);
      } catch (e) {
        Log.error(
          'Failed to decode note',
          tag: 'Storage',
          error: e,
        );
      }
    }
    notes.sort((a, b) {
      final tsA = DateTime.tryParse(a['created_at'] as String? ?? '');
      final tsB = DateTime.tryParse(b['created_at'] as String? ?? '');
      if (tsA == null || tsB == null) {
        return 0;
      }
      return tsB.compareTo(tsA);
    });
    return notes;
  }

  static String exportConversationJson(String sessionId) {
    final raw = _conversationsBox.get(sessionId);
    return raw ?? '[]';
  }
}