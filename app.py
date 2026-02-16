import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Client, Produit, Facture, LigneFacture
from datetime import datetime

app = Flask(__name__)

# ===== DATABASE CONFIGURATION =====
basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'database')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'facturier.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'votre-cle-secrete-changez-moi'

db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    # Add sample products if none exist
    if Produit.query.count() == 0:
        sample_products = [
            Produit(nom='Ordinateur Portable', prix=850.0),
            Produit(nom='Souris Sans Fil', prix=25.0),
            Produit(nom='Clavier Mécanique', prix=75.0),
            Produit(nom='Écran 24"', prix=200.0),
            Produit(nom='Disque Dur 1To', prix=65.0),
        ]
        db.session.add_all(sample_products)
        db.session.commit()
        print("✓ Produits exemple ajoutés")

# Helper function to serialize products
def serialize_produits(produits):
    return [{'id': p.id, 'nom': p.nom, 'prix': p.prix} for p in produits]

# ---------- Client Routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clients')
def clients_list():
    clients = Client.query.all()
    return render_template('clients_list.html', clients=clients)

@app.route('/client/<int:id>')
def client_detail(id):
    client = Client.query.get_or_404(id)
    return render_template('client.html', client=client)

@app.route('/client/new', methods=['GET', 'POST'])
def client_new():
    if request.method == 'POST':
        client = Client(
            nom=request.form['nom'],
            prenom=request.form['prenom'],
            adresse=request.form['adresse'],
            ville=request.form['ville'],
            pays=request.form['pays'],
            telephone=request.form['telephone'],
            email=request.form['email']
        )
        db.session.add(client)
        db.session.commit()
        flash('Client créé avec succès', 'success')
        return redirect(url_for('clients_list'))
    return render_template('client_form.html')

@app.route('/client/<int:id>/edit', methods=['GET', 'POST'])
def client_edit(id):
    client = Client.query.get_or_404(id)
    if request.method == 'POST':
        client.nom = request.form['nom']
        client.prenom = request.form['prenom']
        client.adresse = request.form['adresse']
        client.ville = request.form['ville']
        client.pays = request.form['pays']
        client.telephone = request.form['telephone']
        client.email = request.form['email']
        db.session.commit()
        flash('Client modifié avec succès', 'success')
        return redirect(url_for('client_detail', id=client.id))
    return render_template('client_form.html', client=client)

# ---------- Facture Routes ----------
@app.route('/factures')
def factures_list():
    factures = Facture.query.all()
    return render_template('factures_list.html', factures=factures)

@app.route('/facture/<int:id>')
def facture_detail(id):
    facture = Facture.query.get_or_404(id)
    return render_template('facture.html', facture=facture)

@app.route('/facture/new', methods=['GET', 'POST'])
def facture_new():
    if request.method == 'POST':
        # Generate invoice number
        last_facture = Facture.query.order_by(Facture.id.desc()).first()
        if last_facture:
            new_num = f'F{last_facture.id + 1:04d}'
        else:
            new_num = 'F0001'

        facture = Facture(
            numero=new_num,
            client_id=request.form['client_id'],
            paiement=request.form.get('paiement', ''),
            etat=request.form.get('etat', 'En attente')
        )
        db.session.add(facture)
        db.session.flush()

        # Process product lines
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')

        total = 0.0
        for i in range(len(produits_ids)):
            if produits_ids[i] and quantites[i] and prix_unitaires[i]:
                ligne = LigneFacture(
                    facture_id=facture.id,
                    produit_id=int(produits_ids[i]),
                    quantite=int(quantites[i]),
                    prix_unitaire=float(prix_unitaires[i])
                )
                db.session.add(ligne)
                total += ligne.total

        facture.total = total
        db.session.commit()
        flash('Facture créée avec succès', 'success')
        return redirect(url_for('facture_detail', id=facture.id))

    clients = Client.query.all()
    produits = Produit.query.all()
    produits_serialized = serialize_produits(produits)
    return render_template('facture_form.html', clients=clients, produits=produits_serialized)

@app.route('/facture/<int:id>/edit', methods=['GET', 'POST'])
def facture_edit(id):
    facture = Facture.query.get_or_404(id)
    if request.method == 'POST':
        facture.client_id = request.form['client_id']
        facture.paiement = request.form.get('paiement', '')
        facture.etat = request.form.get('etat', 'En attente')

        # Delete old lines
        LigneFacture.query.filter_by(facture_id=facture.id).delete()

        # Add new lines
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')

        total = 0.0
        for i in range(len(produits_ids)):
            if produits_ids[i] and quantites[i] and prix_unitaires[i]:
                ligne = LigneFacture(
                    facture_id=facture.id,
                    produit_id=int(produits_ids[i]),
                    quantite=int(quantites[i]),
                    prix_unitaire=float(prix_unitaires[i])
                )
                db.session.add(ligne)
                total += ligne.total

        facture.total = total
        db.session.commit()
        flash('Facture modifiée avec succès', 'success')
        return redirect(url_for('facture_detail', id=facture.id))

    clients = Client.query.all()
    produits = Produit.query.all()
    produits_serialized = serialize_produits(produits)
    return render_template('facture_form.html', facture=facture, clients=clients, produits=produits_serialized)

if __name__ == '__main__':
    app.run(debug=True)