/// Base application exception used for user-friendly error handling.
class AppException implements Exception {
  AppException(this.message);

  final String message;

  @override
  String toString() => message;
}

class PermissionDeniedException extends AppException {
  PermissionDeniedException(String message) : super(message);
}

class NetworkException extends AppException {
  NetworkException(String message) : super(message);
}

class SttException extends AppException {
  SttException(String message) : super(message);
}

class TtsException extends AppException {
  TtsException(String message) : super(message);
}