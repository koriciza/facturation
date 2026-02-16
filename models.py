from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    ville = db.Column(db.String(100), nullable=False)
    pays = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)

    factures = db.relationship('Facture', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.nom} {self.prenom}>'

class Produit(db.Model):
    __tablename__ = 'produits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prix = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Produit {self.nom}>'

class Facture(db.Model):
    __tablename__ = 'factures'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    total = db.Column(db.Float, default=0.0)
    paiement = db.Column(db.String(50))
    etat = db.Column(db.String(20), default='En attente')

    lignes = db.relationship('LigneFacture', backref='facture', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Facture {self.numero}>'

class LigneFacture(db.Model):
    __tablename__ = 'lignes_facture'
    id = db.Column(db.Integer, primary_key=True)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)

    produit = db.relationship('Produit')

    @property
    def total(self):
        return self.quantite * self.prix_unitaire