from rapidfuzz import fuzz
from clients.models import Client


def find_potential_duplicates(threshold=85):
    """
    Busca posibles clientes duplicados por nombre y apellidos (fuzzy) y teléfono exacto.
    Devuelve una lista de tuplas: (cliente1, cliente2, score, motivo)
    """
    clients = list(Client.objects.all())
    duplicates = []
    checked = set()
    for i, c1 in enumerate(clients):
        for j, c2 in enumerate(clients):
            if i >= j:
                continue
            key = tuple(sorted([c1.id, c2.id]))
            if key in checked:
                continue
            checked.add(key)
            # Comparar por teléfono exacto
            if c1.phone_number and c2.phone_number and c1.phone_number == c2.phone_number:
                duplicates.append((c1, c2, 100, 'Teléfono igual'))
                continue
            # Comparar por nombre+apellidos fuzzy
            name1 = f"{c1.first_name} {c1.last_name}".strip().lower()
            name2 = f"{c2.first_name} {c2.last_name}".strip().lower()
            score = fuzz.token_sort_ratio(name1, name2)
            if score >= threshold:
                duplicates.append((c1, c2, score, 'Nombre y apellidos similares'))
    return duplicates
