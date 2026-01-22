/// Models for Workout Routines
/// Used by the mobile app to display assigned routines and exercises

class Routine {
  final int id;
  final int assignmentId;
  final String name;
  final String description;
  final String goal;
  final String goalDisplay;
  final String difficulty;
  final String difficultyDisplay;
  final int daysCount;
  final int exercisesCount;
  final DateTime? startDate;
  final DateTime? endDate;
  final List<RoutineDay>? days;

  Routine({
    required this.id,
    required this.assignmentId,
    required this.name,
    required this.description,
    required this.goal,
    required this.goalDisplay,
    required this.difficulty,
    required this.difficultyDisplay,
    required this.daysCount,
    required this.exercisesCount,
    this.startDate,
    this.endDate,
    this.days,
  });

  factory Routine.fromJson(Map<String, dynamic> json) {
    return Routine(
      id: json['id'],
      assignmentId: json['assignment_id'] ?? json['assignment']?['id'] ?? 0,
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      goal: json['goal'] ?? '',
      goalDisplay: json['goal_display'] ?? json['goal'] ?? '',
      difficulty: json['difficulty'] ?? '',
      difficultyDisplay: json['difficulty_display'] ?? json['difficulty'] ?? '',
      daysCount: json['days_count'] ?? 0,
      exercisesCount: json['exercises_count'] ?? 0,
      startDate: json['start_date'] != null ? DateTime.parse(json['start_date']) : null,
      endDate: json['end_date'] != null ? DateTime.parse(json['end_date']) : null,
      days: json['days'] != null
          ? (json['days'] as List).map((d) => RoutineDay.fromJson(d)).toList()
          : null,
    );
  }
}

class RoutineDay {
  final int id;
  final String name;
  final int order;
  final int exercisesCount;
  final List<RoutineExercise> exercises;

  RoutineDay({
    required this.id,
    required this.name,
    required this.order,
    required this.exercisesCount,
    required this.exercises,
  });

  factory RoutineDay.fromJson(Map<String, dynamic> json) {
    return RoutineDay(
      id: json['id'],
      name: json['name'] ?? '',
      order: json['order'] ?? 0,
      exercisesCount: json['exercises_count'] ?? 0,
      exercises: json['exercises'] != null
          ? (json['exercises'] as List).map((e) => RoutineExercise.fromJson(e)).toList()
          : [],
    );
  }
}

class RoutineExercise {
  final int id;
  final int exerciseId;
  final String name;
  final String description;
  final String muscleGroup;
  final String muscleGroupDisplay;
  final String? videoUrl;
  final String sets;
  final String reps;
  final String rest;
  final String notes;
  final int order;

  RoutineExercise({
    required this.id,
    required this.exerciseId,
    required this.name,
    required this.description,
    required this.muscleGroup,
    required this.muscleGroupDisplay,
    this.videoUrl,
    required this.sets,
    required this.reps,
    required this.rest,
    required this.notes,
    required this.order,
  });

  factory RoutineExercise.fromJson(Map<String, dynamic> json) {
    return RoutineExercise(
      id: json['id'],
      exerciseId: json['exercise_id'] ?? 0,
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      muscleGroup: json['muscle_group'] ?? '',
      muscleGroupDisplay: json['muscle_group_display'] ?? json['muscle_group'] ?? '',
      videoUrl: json['video_url'],
      sets: json['sets'] ?? '',
      reps: json['reps'] ?? '',
      rest: json['rest'] ?? '',
      notes: json['notes'] ?? '',
      order: json['order'] ?? 0,
    );
  }

  /// Get the muscle group color for UI
  int get muscleGroupColor {
    switch (muscleGroup) {
      case 'CHEST':
        return 0xFFE53935; // Red
      case 'BACK':
        return 0xFF1E88E5; // Blue
      case 'LEGS':
        return 0xFF43A047; // Green
      case 'ARMS':
        return 0xFFFF9800; // Orange
      case 'SHOULDERS':
        return 0xFF9C27B0; // Purple
      case 'CORE':
        return 0xFFFFEB3B; // Yellow
      case 'CARDIO':
        return 0xFFE91E63; // Pink
      case 'FULL_BODY':
        return 0xFF607D8B; // Blue Grey
      default:
        return 0xFF9E9E9E; // Grey
    }
  }

  /// Get the muscle group icon name
  String get muscleGroupIcon {
    switch (muscleGroup) {
      case 'CHEST':
        return '💪';
      case 'BACK':
        return '🔙';
      case 'LEGS':
        return '🦵';
      case 'ARMS':
        return '💪';
      case 'SHOULDERS':
        return '🏋️';
      case 'CORE':
        return '🎯';
      case 'CARDIO':
        return '❤️';
      case 'FULL_BODY':
        return '🏃';
      default:
        return '💪';
    }
  }
}

class Exercise {
  final int id;
  final String name;
  final String description;
  final String muscleGroup;
  final String muscleGroupDisplay;
  final String? videoUrl;
  final List<String> tags;

  Exercise({
    required this.id,
    required this.name,
    required this.description,
    required this.muscleGroup,
    required this.muscleGroupDisplay,
    this.videoUrl,
    required this.tags,
  });

  factory Exercise.fromJson(Map<String, dynamic> json) {
    return Exercise(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      muscleGroup: json['muscle_group'] ?? '',
      muscleGroupDisplay: json['muscle_group_display'] ?? json['muscle_group'] ?? '',
      videoUrl: json['video_url'],
      tags: json['tags'] != null ? List<String>.from(json['tags']) : [],
    );
  }
}
