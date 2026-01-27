enum AssistantStatus {
  idle,
  listening,
  thinking,
  speaking,
  error,
}

enum ResponseStyle {
  concise,
  normal,
  detailed,
}

class AssistantMessage {
  AssistantMessage({
    required this.role,
    required this.content,
    required this.timestamp,
  });

  final String role; // "user" | "assistant" | "system"
  final String content;
  final DateTime timestamp;

  factory AssistantMessage.user(String content) {
    return AssistantMessage(
      role: 'user',
      content: content,
      timestamp: DateTime.now().toUtc(),
    );
  }

  factory AssistantMessage.assistant(String content) {
    return AssistantMessage(
      role: 'assistant',
      content: content,
      timestamp: DateTime.now().toUtc(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'role': role,
      'content': content,
      'ts': timestamp.toIso8601String(),
    };
  }
}

class AssistantAction {
  AssistantAction({
    required this.type,
    required this.payload,
  });

  final String type;
  final Map<String, dynamic> payload;

  factory AssistantAction.fromJson(Map<String, dynamic> json) {
    return AssistantAction(
      type: json['type'] as String,
      payload: Map<String, dynamic>.from(json)..remove('type'),
    );
  }
}