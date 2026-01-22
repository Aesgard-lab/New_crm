class Gym {
  final int id;
  final String name;
  final String city;
  final String address;
  final String brandColor;
  final String logoUrl;

  Gym({
    required this.id,
    required this.name,
    required this.city,
    required this.address,
    required this.brandColor,
    this.logoUrl = '',
  });

  factory Gym.fromJson(Map<String, dynamic> json) {
    return Gym(
      id: json['id'],
      name: json['name'],
      city: json['city'] ?? '',
      address: json['address'] ?? '',

      brandColor: json['brand_color'] ?? '#000000',
      logoUrl: json['logo'] ?? '',
    );
  }
}

class Client {
  final int id;
  final String firstName;
  final String lastName;
  final String email;
  final String phone;
  final String dni;
  final String birthDate;
  final String address;
  final String clientType;
  final String gymName;
  final String photo;
  final String accessCode;
  final Map<String, dynamic>? activeMembership;
  final Map<String, dynamic>? stats;
  final List<dynamic>? nextBookings;

  Client({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.phone,
    required this.dni,
    required this.birthDate,
    required this.address,
    required this.clientType,
    required this.gymName,
    required this.photo,
    required this.accessCode,
    this.activeMembership,
    this.stats,
    this.nextBookings,
  });

  factory Client.fromJson(Map<String, dynamic> json) {
    return Client(
      id: json['id'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      email: json['email'] ?? '',
      phone: json['phone'] ?? '',
      dni: json['dni'] ?? '',
      birthDate: json['birth_date_formatted'] ?? '',
      address: json['address'] ?? '',
      clientType: json['client_type_display'] ?? '',
      gymName: json['gym_name'],
      photo: json['photo'] ?? '',
      accessCode: json['access_code'] ?? '',
      activeMembership: json['active_membership'],
      stats: json['stats'],
      nextBookings: json['next_bookings'],
    );
  }
  
  String get fullName => '$firstName $lastName';
}

