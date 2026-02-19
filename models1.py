from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    
    # Type of client: 'person' or 'company'
    type_client = db.Column(db.String(10), nullable=False, default='person')
    
    # Common fields
    nom = db.Column(db.String(100), nullable=False)  # Nom or Raison sociale
    
    # Physical person specific
    prenom = db.Column(db.String(100))  # Only for physical person
    
    # Company specific fields (all optional for physical person)
    quartier = db.Column(db.String(100))
    avenue = db.Column(db.String(100))
    numero = db.Column(db.String(20))
    nif = db.Column(db.String(50))  # Numéro d'Identification Fiscale
    
    # Optional contact fields for both
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    
    # Timestamp
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    factures = db.relationship('Facture', backref='client', lazy=True)
    
    @property
    def display_name(self):
        """Return appropriate display name based on client type"""
        if self.type_client == 'person':
            return f"{self.nom} {self.prenom or ''}".strip()
        else:
            return self.nom  # Raison sociale
    
    def __repr__(self):
        return f'<Client {self.display_name}>'
    

class UniteMesure(db.Model):
    __tablename__ = 'unites_mesure'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    symbole = db.Column(db.String(10))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))
    
    # Relationship to Produit (optional, since backref creates it)
    produits = db.relationship('Produit', backref='unite_mesure_ref', lazy=True)  # Alternative name

class Categorie(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))
    
    # Relationship to Produit (optional, since backref creates it)
    produits = db.relationship('Produit', backref='categorie_ref', lazy=True)  # Alternative name


class Produit(db.Model):
    __tablename__ = 'produits'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
   
    # Foreign keys
    unite_mesure_id = db.Column(db.Integer, db.ForeignKey('unites_mesure.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    # ADD THESE RELATIONSHIPS
    unite_mesure = db.relationship('UniteMesure')
    categorie = db.relationship('Categorie')

    tva = db.Column(db.Float, nullable=False, default=0.0)
    tc = db.Column(db.String(100), nullable=False, default='OUI')
    pf = db.Column(db.String(100), nullable=False, default='OUI')
    article_stockable = db.Column(db.Boolean, default=True)
    pv_ttc = db.Column(db.Float, nullable=False, default=0.0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    lignes_facture = db.relationship('LigneFacture', backref='produit_ref', lazy=True)

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