import 'dart:developer' as developer;

/// Simple tagged logger wrapper for the mobile app.
///
/// This keeps logging consistent and easy to swap for a more advanced solution
/// later without touching call sites.
class Log {
  Log._();

  static void info(String message, {String tag = 'Jarvis'}) {
    developer.log(message, name: tag, level: 800);
  }

  static void warn(String message, {String tag = 'Jarvis'}) {
    developer.log(message, name: tag, level: 900);
  }

  static void error(
    String message, {
    String tag = 'Jarvis',
    Object? error,
    StackTrace? stackTrace,
  }) {
    developer.log(
      message,
      name: tag,
      error: error,
      stackTrace: stackTrace,
      level: 1000,
    );
  }
}