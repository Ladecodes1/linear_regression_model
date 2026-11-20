
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const String apiUrl = 'https://maize-yield-api-93ln.onrender.com/predict';

void main() {
  runApp(const MaizeApp());
}

class FieldSpec {
  final String key;
  final String label;
  final String hint;
  final bool numeric;
  const FieldSpec(this.key, this.label, this.hint, {this.numeric = true});
}

const List<FieldSpec> fields = [
  FieldSpec('country', 'Country',
      'kenya, tanzania, rwanda, burundi, zambia, uganda or nigeria',
      numeric: false),
  FieldSpec('elev', 'Elevation (metres)', 'Between 0 and 3000'),
  FieldSpec('pl_m2', 'Plants per square metre', 'Between 0 and 15'),
  FieldSpec('hybrid', 'Hybrid seed (1 = yes, 0 = no)', 'Enter 0 or 1'),
  FieldSpec('N_kg_ha', 'Nitrogen applied (kg per hectare)', 'Between 0 and 350'),
  FieldSpec('P_kg_ha', 'Phosphorus applied (kg per hectare)', 'Between 0 and 120'),
  FieldSpec('season_prec', 'Season rainfall (mm)', 'Between 200 and 2500'),
];

class MaizeApp extends StatelessWidget {
  const MaizeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Maize Yield Predictor',
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      home: const PredictPage(),
    );
  }
}

class PredictPage extends StatefulWidget {
  const PredictPage({super.key});

  @override
  State<PredictPage> createState() => _PredictPageState();
}

class _PredictPageState extends State<PredictPage> {
  late final Map<String, TextEditingController> _controllers = {
    for (final f in fields) f.key: TextEditingController(),
  };

  bool _loading = false;
  bool _isError = false;
  String _message = 'Enter the farm details and tap Predict.';

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  String _readableErrors(String responseBody) {
    try {
      final data = jsonDecode(responseBody);
      final details = data['detail'] as List;
      final lines = details.map((d) {
        final loc = d['loc'] as List;
        final field = loc.isNotEmpty ? loc.last.toString() : 'input';
        return '- $field: ${d['msg']}';
      }).toList();
      final text = lines.join('\n');
      return 'Please fix these values:\n$text';
    } catch (_) {
      return 'Some values are not valid. Please check each field.';
    }
  }

  Future<void> _predict() async {
    // 1. Missing values
    final missing = fields
        .where((f) => _controllers[f.key]!.text.trim().isEmpty)
        .map((f) => f.label)
        .toList();
    if (missing.isNotEmpty) {
      setState(() {
        _isError = true;
        _message = 'Missing value: please fill in ${missing.join(', ')}.';
      });
      return;
    }

    // 2. Build the request. Text that is not a number is sent as it is,
    //    so the API reports the wrong type.
    final body = <String, dynamic>{};
    for (final f in fields) {
      final text = _controllers[f.key]!.text.trim();
      if (!f.numeric) {
        body[f.key] = text.toLowerCase();
      } else if (f.key == 'hybrid') {
        body[f.key] = int.tryParse(text) ?? text;
      } else {
        body[f.key] = double.tryParse(text) ?? text;
      }
    }

    setState(() {
      _loading = true;
      _isError = false;
      _message =
          'Predicting... the first request can take up to a minute while the server wakes up.';
    });

    // 3. Call the API
    try {
      final response = await http
          .post(
            Uri.parse(apiUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 90));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final value = (data['predicted_yield_kg_ha'] as num).toStringAsFixed(1);
        setState(() {
          _isError = false;
          _message = 'Predicted maize yield: $value kg per hectare';
        });
      } else if (response.statusCode == 422) {
        setState(() {
          _isError = true;
          _message = _readableErrors(response.body);
        });
      } else {
        setState(() {
          _isError = true;
          _message =
              'The server returned an error (code ${response.statusCode}). Please try again.';
        });
      }
    } on TimeoutException {
      setState(() {
        _isError = true;
        _message = 'The server took too long to answer. Please try again.';
      });
    } catch (_) {
      setState(() {
        _isError = true;
        _message =
            'Could not reach the server. Check your internet connection and try again.';
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Maize Yield Predictor')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text(
              'Enter your farm details to predict maize yield (kg per hectare).',
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 16),
            for (final f in fields) ...[
              TextField(
                controller: _controllers[f.key],
                keyboardType: f.numeric
                    ? const TextInputType.numberWithOptions(decimal: true)
                    : TextInputType.text,
                decoration: InputDecoration(
                  labelText: f.label,
                  helperText: f.hint,
                  helperMaxLines: 2,
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
            ],
            SizedBox(
              height: 48,
              child: ElevatedButton(
                onPressed: _loading ? null : _predict,
                child: const Text('Predict'),
              ),
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: _isError ? Colors.red.shade50 : Colors.green.shade50,
                border: Border.all(color: _isError ? Colors.red : Colors.green),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _message,
                style: TextStyle(
                  fontSize: 16,
                  color: _isError ? Colors.red.shade900 : Colors.green.shade900,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}