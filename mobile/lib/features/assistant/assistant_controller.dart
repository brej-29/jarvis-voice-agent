import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';

import '../../core/errors.dart';
import '../../core/logger.dart';
import 'assistant_models.dart';
import 'assistant_service.dart';

class AssistantController extends ChangeNotifier {
  AssistantController({
    stt.SpeechToText? speechToText,
    FlutterTts? flutterTts,
    AssistantService? service,
  })  : _speechToText = speechToText ?? stt.SpeechToText(),
        _flutterTts = flutterTts ?? FlutterTts(),
        _service = service ?? AssistantService();

  final stt.SpeechToText _speechToText;
  final FlutterTts _flutterTts;
  final AssistantService _service;

  AssistantStatus status = AssistantStatus.idle;
  ResponseStyle responseStyle = ResponseStyle.normal;

  String currentTranscript = '';
  String lastResponse = '';
  String? errorMessage;

  final List<AssistantMessage> _messages = <AssistantMessage>[];

  List<AssistantMessage> get messages => List.unmodifiable(_messages);

  double _ttsRate = 0.5;

  Future<void> initialize() async {
    try {
      await _flutterTts.setSpeechRate(_ttsRate);
    } catch (e, stackTrace) {
      Log.error(
        'Failed to initialize TTS',
        tag: 'AssistantController',
        error: e,
        stackTrace: stackTrace,
      );
    }
  }

  Future<void> onMicPressed() async {
    switch (status) {
      case AssistantStatus.listening:
        await _stopListeningAndSend();
        break;
      case AssistantStatus.idle:
      case AssistantStatus.thinking:
      case AssistantStatus.speaking:
      case AssistantStatus.error:
        await _startListening();
        break;
    }
  }

  Future<void> _startListening() async {
    Log.info('Starting STT listening', tag: 'AssistantController');
    errorMessage = null;

    final micStatus = await Permission.microphone.request();
    if (!micStatus.isGranted) {
      _setError(PermissionDeniedException('Microphone permission is required.'));
      return;
    }

    try {
      final available = await _speechToText.initialize(
        onError: _onSttError,
        onStatus: _onSttStatus,
      );

      if (!available) {
        _setError(SttException('Speech recognition not available on this device.'));
        return;
      }

      status = AssistantStatus.listening;
      currentTranscript = '';
      notifyListeners();

      await _speechToText.listen(
        onResult: _onSttResult,
        listenMode: ListenMode.dictation,
      );
    } catch (e, stackTrace) {
      Log.error(
        'Error starting speech recognition',
        tag: 'AssistantController',
        error: e,
        stackTrace: stackTrace,
      );
      _setError(SttException('Unable to start speech recognition.'));
    }
  }

  Future<void> _stopListeningAndSend() async {
    Log.info('Stopping STT and sending to backend', tag: 'AssistantController');
    try {
      await _speechToText.stop();
    } catch (e, stackTrace) {
      Log.error(
        'Error stopping speech recognition',
        tag: 'AssistantController',
        error: e,
        stackTrace: stackTrace,
      );
    }

    final text = currentTranscript.trim();
    if (text.isEmpty) {
      _setError(SttException('No speech detected. Please try again.'));
      status = AssistantStatus.idle;
      notifyListeners();
      return;
    }

    _messages.add(AssistantMessage.user(text));
    status = AssistantStatus.thinking;
    notifyListeners();

    try {
      final reply = await _service.sendChat(
        sessionId: 'local-session',
        history: _messages,
        responseStyle: responseStyle,
      );
      lastResponse = reply;
      _messages.add(AssistantMessage.assistant(reply));
      status = AssistantStatus.speaking;
      notifyListeners();

      await _speak(reply);
      status = AssistantStatus.idle;
      notifyListeners();
    } on AppException catch (e) {
      _setError(e);
      status = AssistantStatus.error;
      notifyListeners();
    }
  }

  void _onSttResult(SpeechRecognitionResult result) {
    currentTranscript = result.recognizedWords;
    notifyListeners();
  }

  void _onSttError(stt.SpeechRecognitionError error) {
    Log.error(
      'STT error: ${error.errorMsg}',
      tag: 'AssistantController',
    );
    _setError(SttException('Speech recognition error: ${error.errorMsg}'));
  }

  void _onSttStatus(String statusText) {
    Log.info('STT status: $statusText', tag: 'AssistantController');
  }

  Future<void> _speak(String text) async {
    try {
      await _flutterTts.stop();
      await _flutterTts.setSpeechRate(_ttsRate);
      await _flutterTts.speak(text);
    } catch (e, stackTrace) {
      Log.error(
        'Error during TTS',
        tag: 'AssistantController',
        error: e,
        stackTrace: stackTrace,
      );
      _setError(TtsException('Unable to speak the response.'));
    }
  }

  void updateResponseStyle(ResponseStyle style) {
    responseStyle = style;
    notifyListeners();
  }

  Future<void> updateTtsRate(double rate) async {
    _ttsRate = rate;
    try {
      await _flutterTts.setSpeechRate(_ttsRate);
    } catch (e, stackTrace) {
      Log.error(
        'Failed to update TTS rate',
        tag: 'AssistantController',
        error: e,
        stackTrace: stackTrace,
      );
      _setError(TtsException('Unable to update TTS rate.'));
    }
  }

  void clearError() {
    errorMessage = null;
    notifyListeners();
  }

  void _setError(AppException exception) {
    errorMessage = exception.message;
    Log.warn('User-facing error: ${exception.message}', tag: 'AssistantController');
    notifyListeners();
  }

  @override
  void dispose() {
    _service.dispose();
    _speechToText.stop();
    _flutterTts.stop();
    super.dispose();
  }
}