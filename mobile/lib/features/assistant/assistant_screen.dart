import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/logger.dart';
import '../settings/settings_screen.dart';
import 'assistant_controller.dart';
import 'assistant_models.dart';

class AssistantScreen extends StatelessWidget {
  const AssistantScreen({super.key});

  String _statusLabel(AssistantStatus status) {
    switch (status) {
      case AssistantStatus.idle:
        return 'Idle';
      case AssistantStatus.listening:
        return 'Listening...';
      case AssistantStatus.thinking:
        return 'Thinking...';
      case AssistantStatus.speaking:
        return 'Speaking...';
      case AssistantStatus.error:
        return 'Error';
    }
  }

  Color _statusColor(AssistantStatus status, BuildContext context) {
    switch (status) {
      case AssistantStatus.idle:
        return Colors.grey;
      case AssistantStatus.listening:
        return Colors.greenAccent;
      case AssistantStatus.thinking:
        return Colors.blueAccent;
      case AssistantStatus.speaking:
        return Colors.purpleAccent;
      case AssistantStatus.error:
        return Theme.of(context).colorScheme.error;
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AssistantController>();

    // Surface user-facing errors via SnackBar.
    if (controller.errorMessage != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        final message = controller.errorMessage;
        if (message == null) {
          return;
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
        controller.clearError();
      });
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Jarvis Voice Assistant'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Log.info('Navigating to settings', tag: 'AssistantScreen');
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _buildStatusRow(context, controller),
              const SizedBox(height: 16),
              _buildTranscriptCard(controller),
              const SizedBox(height: 16),
              _buildResponseCard(controller),
              const SizedBox(height: 16),
              Expanded(child: _buildHistoryList(controller)),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.large(
        onPressed: () => context.read<AssistantController>().onMicPressed(),
        child: Icon(
          controller.status == AssistantStatus.listening
              ? Icons.stop
              : Icons.mic,
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }

  Widget _buildStatusRow(
    BuildContext context,
    AssistantController controller,
  ) {
    final label = _statusLabel(controller.status);
    final color = _statusColor(controller.status, context);

    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: Theme.of(context).textTheme.titleMedium,
        ),
      ],
    );
  }

  Widget _buildTranscriptCard(AssistantController controller) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'You said',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              controller.currentTranscript.isEmpty
                  ? 'Tap the mic and start speaking.'
                  : controller.currentTranscript,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResponseCard(AssistantController controller) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Jarvis',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              controller.lastResponse.isEmpty
                  ? 'I\'ll respond here after you speak.'
                  : controller.lastResponse,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryList(AssistantController controller) {
    final messages = controller.messages;
    if (messages.isEmpty) {
      return const Center(
        child: Text(
          'Your conversation history for this session will appear here.',
          textAlign: TextAlign.center,
        ),
      );
    }

    return ListView.builder(
      itemCount: messages.length,
      itemBuilder: (context, index) {
        final msg = messages[index];
        final isUser = msg.role == 'user';
        final alignment =
            isUser ? Alignment.centerRight : Alignment.centerLeft;
        final color =
            isUser ? Colors.blue.withOpacity(0.2) : Colors.grey.withOpacity(0.2);

        return Align(
          alignment: alignment,
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(msg.content),
          ),
        );
      },
    );
  }
}