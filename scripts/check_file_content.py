with open('config/urls.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
print("="*60)
print("CONTENIDO DEL ARCHIVO config/urls.py:")
print("="*60)
print(content)
print("="*60)
print(f"Total caracteres: {len(content)}")
print(f"Contiene 'public/'? {('public/' in content)}")
print(f"Contiene 'embed/'? {('embed/' in content)}")
