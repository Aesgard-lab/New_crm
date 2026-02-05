import 'package:flutter/material.dart';

class SpotData {
  final int number;
  final double x;
  final double y;
  final String status; // 'available', 'occupied', 'mine'

  SpotData({
    required this.number,
    required this.x,
    required this.y,
    required this.status,
  });

  factory SpotData.fromJson(Map<String, dynamic> json) {
    return SpotData(
      number: json['number'] ?? 0,
      x: (json['x'] ?? 0).toDouble(),
      y: (json['y'] ?? 0).toDouble(),
      status: json['status'] ?? 'available',
    );
  }
}

class ObstacleData {
  final double x;
  final double y;

  ObstacleData({required this.x, required this.y});

  factory ObstacleData.fromJson(Map<String, dynamic> json) {
    return ObstacleData(
      x: (json['x'] ?? 0).toDouble(),
      y: (json['y'] ?? 0).toDouble(),
    );
  }
}

class SpotSelectorWidget extends StatefulWidget {
  final List<SpotData> spots;
  final List<ObstacleData> obstacles;
  final double layoutWidth;
  final double layoutHeight;
  final int? selectedSpot;
  final int? mySpot;
  final Function(int) onSpotSelected;
  final Color brandColor;

  const SpotSelectorWidget({
    super.key,
    required this.spots,
    required this.obstacles,
    required this.layoutWidth,
    required this.layoutHeight,
    this.selectedSpot,
    this.mySpot,
    required this.onSpotSelected,
    this.brandColor = Colors.indigo,
  });

  @override
  State<SpotSelectorWidget> createState() => _SpotSelectorWidgetState();
}

class _SpotSelectorWidgetState extends State<SpotSelectorWidget> {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            Icon(Icons.event_seat, color: widget.brandColor),
            const SizedBox(width: 8),
            const Text(
              'Selecciona tu puesto',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Spacer(),
            if (widget.selectedSpot != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: widget.brandColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'Puesto #${widget.selectedSpot}',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: widget.brandColor,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),

        // Layout grid
        LayoutBuilder(
          builder: (context, constraints) {
            final containerWidth = constraints.maxWidth;
            final scale = containerWidth / widget.layoutWidth;
            final containerHeight = widget.layoutHeight * scale;

            return Container(
              height: containerHeight.clamp(150.0, 300.0),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey[300]!),
              ),
              child: Stack(
                children: [
                  // Obstacles
                  ...widget.obstacles.map((obs) => Positioned(
                    left: obs.x * scale,
                    top: obs.y * scale,
                    child: Container(
                      width: 40 * scale,
                      height: 40 * scale,
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: Colors.grey[400]!),
                      ),
                    ),
                  )),

                  // Spots
                  ...widget.spots.map((spot) {
                    final isSelected = widget.selectedSpot == spot.number;
                    final isMine = widget.mySpot == spot.number;
                    final isAvailable = spot.status == 'available';
                    final isOccupied = spot.status == 'occupied' && !isMine;

                    Color bgColor;
                    if (isSelected || isMine) {
                      bgColor = widget.brandColor;
                    } else if (isOccupied) {
                      bgColor = Colors.grey[400]!;
                    } else {
                      bgColor = Colors.green;
                    }

                    return Positioned(
                      left: spot.x * scale,
                      top: spot.y * scale,
                      child: GestureDetector(
                        onTap: isAvailable && !isMine
                            ? () => widget.onSpotSelected(spot.number)
                            : null,
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          width: 40 * scale,
                          height: 40 * scale,
                          decoration: BoxDecoration(
                            color: bgColor,
                            borderRadius: BorderRadius.circular(8 * scale),
                            boxShadow: (isSelected || isMine)
                                ? [
                                    BoxShadow(
                                      color: widget.brandColor.withOpacity(0.4),
                                      blurRadius: 8,
                                      spreadRadius: 2,
                                    )
                                  ]
                                : null,
                          ),
                          child: Center(
                            child: Text(
                              '${spot.number}',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 12 * scale,
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 8),

        // Legend
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildLegendItem(Colors.green, 'Disponible'),
            const SizedBox(width: 16),
            _buildLegendItem(Colors.grey[400]!, 'Ocupado'),
            const SizedBox(width: 16),
            _buildLegendItem(widget.brandColor, 'Tu selección'),
          ],
        ),
      ],
    );
  }

  Widget _buildLegendItem(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}

/// Dialog for selecting a spot before booking
class SpotSelectionDialog extends StatefulWidget {
  final Map<String, dynamic> spotsData;
  final Color brandColor;

  const SpotSelectionDialog({
    super.key,
    required this.spotsData,
    this.brandColor = Colors.indigo,
  });

  @override
  State<SpotSelectionDialog> createState() => _SpotSelectionDialogState();
}

class _SpotSelectionDialogState extends State<SpotSelectionDialog> {
  int? _selectedSpot;

  @override
  void initState() {
    super.initState();
    // Pre-select user's spot if they have one
    _selectedSpot = widget.spotsData['my_spot'];
  }

  @override
  Widget build(BuildContext context) {
    final spots = (widget.spotsData['spots'] as List? ?? [])
        .map((s) => SpotData.fromJson(s))
        .toList();
    final obstacles = (widget.spotsData['obstacles'] as List? ?? [])
        .map((o) => ObstacleData.fromJson(o))
        .toList();
    final layout = widget.spotsData['layout'] ?? {'width': 400, 'height': 300};
    final roomName = widget.spotsData['room_name'] ?? 'Sala';
    final availableSpots = widget.spotsData['available_spots'] ?? 0;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        roomName,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        '$availableSpots puestos disponibles',
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Spot selector
            SpotSelectorWidget(
              spots: spots,
              obstacles: obstacles,
              layoutWidth: (layout['width'] ?? 400).toDouble(),
              layoutHeight: (layout['height'] ?? 300).toDouble(),
              selectedSpot: _selectedSpot,
              mySpot: widget.spotsData['my_spot'],
              onSpotSelected: (spotNumber) {
                setState(() {
                  _selectedSpot = spotNumber;
                });
              },
              brandColor: widget.brandColor,
            ),
            const SizedBox(height: 20),

            // Buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('Cancelar'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _selectedSpot != null
                        ? () => Navigator.pop(context, _selectedSpot)
                        : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: widget.brandColor,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text(
                      'Confirmar',
                      style: TextStyle(color: Colors.white),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
