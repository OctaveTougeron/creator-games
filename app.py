from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw
import os
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Page d'accueil
@app.route('/')
def index():
    return render_template('index.html')

# Page du générateur de Dobble
@app.route('/dobble')
def dobble():
    return render_template('dobble.html')

# Génération des cartes Dobble
@app.route('/generate_dobble', methods=['POST'])
def generate_dobble():
    if 'images' not in request.files:
        return "Aucune image téléversée", 400
    
    files = request.files.getlist('images')
    if len(files) != 57:
        return "Vous devez téléverser exactement 57 images", 400
    
    images = []
    for idx, file in enumerate(files):
        image_path = os.path.join(UPLOAD_FOLDER, f"{idx + 1}.png")
        file.save(image_path)
        img = Image.open(image_path)
        images.append(img)

    # Générer les faces Dobble
    faces = generate_dobble_faces(images)

    # Créer un PDF avec les faces générées
    pdf = create_pdf_from_faces(faces)

    return send_file(pdf, as_attachment=True, download_name='dobble.pdf')

def generate_dobble_faces(images, num_symbols=57):
    p = 7
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
    faces = cards * 2
    assert len(faces) == 110, f"Le nombre de faces générées est incorrect : {len(faces)}"

    positions = [
        (255, 105), (380, 155), (130, 155),
        (105, 280), (405, 280),
        (155, 405), (355, 405), (255, 330)
    ]

    face_images = []
    for face in faces:
        # Créer une image avec fond blanc (pas de transparence)
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

def create_pdf_from_faces(faces):
    pdf_buffer = BytesIO()
    c_width, c_height = 2480, 3508  # Taille d'une page A4 en pixels à 300 DPI
    card_size = 800  # Augmenter la taille des cartes à 800 pixels
    pages = []
    current_page = Image.new('RGB', (c_width, c_height), (255, 255, 255))

    # Ajustement des positions pour 2 images par ligne et des images plus grandes
    positions = [
        (80, 80), (c_width - card_size - 80, 80),  # Ligne du haut
        (80, 1000), (c_width - card_size - 80, 1000),  # Ligne du milieu
        (80, 1920), (c_width - card_size - 80, 1920)  # Ligne du bas
    ]
    
    for idx, face in enumerate(faces):
        # Redimensionner l'image avant de dessiner le cercle noir
        resized_face = face.resize((card_size, card_size))
        
        # Placer la face sur la page PDF
        pos = positions[idx % 6]
        current_page.paste(resized_face, pos)

        if (idx + 1) % 6 == 0:
            pages.append(current_page)
            current_page = Image.new('RGB', (c_width, c_height), (255, 255, 255))

    # Ajouter la dernière page si elle n'est pas complète
    if idx % 6 != 5:
        pages.append(current_page)

    # Sauvegarder toutes les pages dans un PDF
    first_page = pages[0]
    other_pages = pages[1:]
    first_page.save(pdf_buffer, format='PDF', save_all=True, append_images=other_pages, resolution=300)
    
    pdf_buffer.seek(0)
    return pdf_buffer

if __name__ == '__main__':
    app.run(debug=True)
