from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw
import os
from io import BytesIO
import uuid

app = Flask(__name__)

# Configurer les répertoires pour les téléversements
DOBBLE_UPLOAD_FOLDER = 'uploads/dobble'
MEMORY_UPLOAD_FOLDER = 'uploads/memory'

os.makedirs(DOBBLE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MEMORY_UPLOAD_FOLDER, exist_ok=True)

# Configurer la limite de taille de fichier (16 Mo)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Page d'accueil
@app.route('/')
def index():
    return render_template('index.html')

# Page du générateur de Dobble
@app.route('/dobble')
def dobble():
    return render_template('dobble.html')

# Page du générateur de Memory
@app.route('/memory')
def memory():
    return render_template('memory.html')

# Génération des cartes Dobble
@app.route('/generate_dobble', methods=['POST'])
def generate_dobble():
    if 'images' not in request.files:
        return "Aucune image téléversée", 400
    
    files = request.files.getlist('images')
    
    if len(files) != 57:
        return "Vous devez téléverser exactement 57 images", 400
    
    # Charger les images pour Dobble
    images = []
    for idx, file in enumerate(files):
        # Générer un nom unique pour chaque fichier
        image_path = os.path.join(DOBBLE_UPLOAD_FOLDER, f"dobble_{uuid.uuid4().hex}.png")
        file.save(image_path)
        img = Image.open(image_path)
        images.append(img)

    # Générer les cartes Dobble
    faces = generate_dobble_faces(images)
    pdf = create_dobble_pdf(faces)

    return send_file(pdf, as_attachment=True, download_name='dobble.pdf')

# Génération des cartes Memory
@app.route('/generate_memory', methods=['POST'])
def generate_memory():
    if 'images' not in request.files:
        return "Aucune image téléversée", 400
    
    files = request.files.getlist('images')
    
    if len(files) > 50:
        return "Vous pouvez téléverser un maximum de 50 images", 400

    # Charger les images pour Memory
    images = []
    for idx, file in enumerate(files):
        # Générer un nom unique pour chaque fichier
        image_path = os.path.join(MEMORY_UPLOAD_FOLDER, f"memory_{uuid.uuid4().hex}.png")
        file.save(image_path)
        img = Image.open(image_path)
        images.append(img)

    # Générer les paires de cartes Memory
    pairs = images * 2  # Duplique les images pour créer les paires
    pairs = pairs[:100]  # Limiter à 50 paires (100 cartes)
    pdf = create_memory_pdf(pairs)

    return send_file(pdf, as_attachment=True, download_name='memory.pdf')

# Fonction pour générer les faces Dobble
def generate_dobble_faces(images, num_symbols=57):
    p = 7  # Utiliser le nombre de symboles par carte pour Dobble
    cards = []
    for i in range(p + 1):
        for j in range(p):
            card = [(i * p + k) % (p * p) + 1 for k in range(p)]
            card.append(p * p + j + 1)
            if len(cards) < 55:
                cards.append(card)
    for i in range(p):
        card = [p * p + 1 + i]
        for j in range(p):
            card.append(j * p + (i + j) % p + 1)
        if len(cards) < 55:
            cards.append(card)
    cards = cards[:55]
    faces = cards * 2  # Dupliquer les cartes pour obtenir 110 faces

    # Positions des symboles sur la carte Dobble
    positions = [
        (255, 105), (380, 155), (130, 155),
        (105, 280), (405, 280),
        (155, 405), (355, 405), (255, 330)
    ]

    face_images = []
    for face in faces:
        face_img = Image.new('RGB', (600, 600), (255, 255, 255))  # Fond blanc
        draw = ImageDraw.Draw(face_img)
        draw.ellipse([(50, 50), (550, 550)], outline=(0, 0, 0), width=10)
        for i, symbol_idx in enumerate(face[:8]):
            if symbol_idx <= num_symbols:
                symbol_img = images[symbol_idx - 1].resize((100, 100), Image.ANTIALIAS)
                pos = positions[i % len(positions)]
                face_img.paste(symbol_img, pos, symbol_img)
        face_images.append(face_img)

    return face_images

# Fonction pour créer un PDF avec les cartes Dobble
def create_dobble_pdf(faces):
    pdf_buffer = BytesIO()
    c_width, c_height = 2480, 3508  # Taille d'une page A4 en pixels à 300 DPI
    card_size = 800  # Taille des cartes Dobble (800x800 pixels)
    pages = []
    current_page = Image.new('RGB', (c_width, c_height), (255, 255, 255))

    # Positions pour 2 images par ligne, 3 lignes par page (6 cartes par page)
    positions = [
        (80, 80), (c_width - card_size - 80, 80),  # Ligne 1
        (80, 1000), (c_width - card_size - 80, 1000),  # Ligne 2
        (80, 1920), (c_width - card_size - 80, 1920)  # Ligne 3
    ]
    
    for idx, face in enumerate(faces):
        pos = positions[idx % 6]
        resized_face = face.resize((card_size, card_size))
        current_page.paste(resized_face, pos)

        if (idx + 1) % 6 == 0:
            pages.append(current_page)
            current_page = Image.new('RGB', (c_width, c_height), (255, 255, 255))

    if idx % 6 != 5:
        pages.append(current_page)

    first_page = pages[0]
    other_pages = pages[1:]
    first_page.save(pdf_buffer, format='PDF', save_all=True, append_images=other_pages, resolution=300)
    
    pdf_buffer.seek(0)
    return pdf_buffer

# Fonction pour créer un PDF avec les cartes Memory
def create_memory_pdf(pairs):
    pdf_buffer = BytesIO()
    c_width, c_height = 2480, 3508  # Taille d'une page A4 en pixels à 300 DPI
    card_size = 400  # Taille des cartes mémoire (400x400 pixels)
    pages = []
    current_page = Image.new('RGB', (c_width, c_height), (255, 255, 255))  # Fond blanc

    # Positions pour 4 paires (8 images) par ligne, 5 lignes par page (20 paires par page)
    positions = [
        (80, 80), (640, 80), (1200, 80), (1760, 80),   # Ligne 1 (Première image de chaque paire)
        (80, 640), (640, 640), (1200, 640), (1760, 640), # Ligne 2 (Deuxième image de chaque paire)
        (80, 1200), (640, 1200), (1200, 1200), (1760, 1200),  # Ligne 3
        (80, 1760), (640, 1760), (1200, 1760), (1760, 1760),  # Ligne 4
        (80, 2320), (640, 2320), (1200, 2320), (1760, 2320)   # Ligne 5
    ]
    
    for idx in range(0, len(pairs), 2):
        # Disposer chaque paire côte à côte
        pos1 = positions[(idx // 2) % 20]  # Position de la première image de la paire
        pos2 = positions[((idx // 2) % 20) + 1]  # Position de la deuxième image de la paire

        resized_pair1 = pairs[idx].resize((card_size, card_size))
        resized_pair2 = pairs[idx + 1].resize((card_size, card_size))

        # Coller les images sur la page courante
        current_page.paste(resized_pair1, pos1)
        current_page.paste(resized_pair2, pos2)

        # Si 20 paires (40 cartes) sont atteintes, ajouter la page et en créer une nouvelle
        if (idx + 2) % 40 == 0:
            pages.append(current_page)
            current_page = Image.new('RGB', (c_width, c_height), (255, 255, 255))  # Nouvelle page avec fond blanc

    # Ajouter la dernière page si elle n'est pas complète
    if (idx + 2) % 40 != 0:
        pages.append(current_page)

    # Sauvegarder toutes les pages dans un PDF
    first_page = pages[0]
    other_pages = pages[1:]
    first_page.save(pdf_buffer, format='PDF', save_all=True, append_images=other_pages, resolution=300)
    
    pdf_buffer.seek(0)
    return pdf_buffer


if __name__ == '__main__':
    app.run(debug=True)
