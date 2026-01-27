import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../assistant/assistant_controller.dart';
import '../assistant/assistant_models.dart';
import 'settings_controller.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const String routeName = '/settings';

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsController>();
    final assistant = context.read<AssistantController>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _buildResponseStyleSection(settings, assistant),
            const SizedBox(height: 24),
            _buildTtsRateSection(settings, assistant),
            const SizedBox(height: 24),
            _buildBackendUrlSection(settings),
          ],
        ),
      ),
    );
  }

  Widget _buildResponseStyleSection(
    SettingsController settings,
    AssistantController assistant,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Response style',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        DropdownButton<ResponseStyle>(
          value: settings.responseStyle,
          items: ResponseStyle.values
              .map(
                (style) => DropdownMenuItem<ResponseStyle>(
                  value: style,
                  child: Text(style.name),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value == null) {
              return;
            }
            settings.setResponseStyle(value);
            assistant.updateResponseStyle(value);
          },
        ),
      ],
    );
  }

  Widget _buildTtsRateSection(
    SettingsController settings,
    AssistantController assistant,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'TTS rate',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        Slider(
          value: settings.ttsRate,
          min: 0.3,
          max: 1.0,
          divisions: 7,
          label: settings.ttsRate.toStringAsFixed(2),
          onChanged: (value) {
            settings.setTtsRate(value);
            assistant.updateTtsRate(value);
          },
        ),
      ],
    );
  }

  Widget _buildBackendUrlSection(SettingsController settings) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Backend base URL',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: settings.backendBaseUrl,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: 'http://10.0.2.2:8000',
          ),
          keyboardType: TextInputType.url,
          onFieldSubmitted: settings.setBackendBaseUrl,
        ),
        const SizedBox(height: 8),
        const Text(
          'For Android emulators, the default is http://10.0.2.2:8000. '
          'For iOS simulators or desktop, http://localhost:8000 is typical.',
          style: TextStyle(fontSize: 12),
        ),
      ],
    );
  }
}