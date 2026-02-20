from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Categorie(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # produits = db.relationship('Produit', backref='categorie_ref', lazy=True)

    def __repr__(self):
        return f'<Categorie {self.nom}>'

class UniteMesure(db.Model):
    __tablename__ = 'unites_mesure'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)
    symbole = db.Column(db.String(10))
    description = db.Column(db.String(200))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # produits = db.relationship('Produit', backref='unite_mesure_ref', lazy=True)
    
    def __repr__(self):
        return f'<UniteMesure {self.nom}>'

class Produit(db.Model):
    __tablename__ = 'produits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    
    # Foreign keys
    unite_mesure_id = db.Column(db.Integer, db.ForeignKey('unites_mesure.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    # ADD THESE RELATIONSHIPS
    unite_mesure = db.relationship('UniteMesure', backref='produits')
    categorie = db.relationship('Categorie', backref='produits')
    
    # Tax fields
    tva = db.Column(db.Float, nullable=False, default=0.0)
    tc = db.Column(db.String(5), nullable=False)
    pf = db.Column(db.String(5), nullable=False)
    article_stockable = db.Column(db.String(5), nullable=False)
    pv_ttc = db.Column(db.Float, nullable=False, default=0.0)
    stock_actuel = db.Column(db.Integer, default=0)  # Current stock (calculated)
    stock_minimum = db.Column(db.Integer, default=0)  # Alert threshold
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    lignes_facture = db.relationship('LigneFacture', backref='produit_ref', lazy=True)
    mouvements_stock = db.relationship('MouvementStock', backref='produit', lazy=True, cascade='all, delete-orphan')

    @property
    def valeur_stock(self):
        """Calculate total stock value"""
        return self.stock_actuel * self.pv_ttc

    def __repr__(self):
        return f'<Produit {self.nom}>'

class MouvementStock(db.Model):
    __tablename__ = 'mouvements_stock'
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    
    # Type de mouvement
    TYPE_ENTREE = 'entree'
    TYPE_SORTIE = 'sortie'
    TYPE_AJUSTEMENT = 'ajustement'
    
    type_mouvement = db.Column(db.String(20), nullable=False)  # entree, sortie, ajustement
    
    # Quantité
    quantite = db.Column(db.Integer, nullable=False)
    stock_avant = db.Column(db.Integer, nullable=False)
    stock_apres = db.Column(db.Integer, nullable=False)
    
    # Référence
    reference_type = db.Column(db.String(50))  # 'facture', 'approvisionnement', 'ajustement'
    reference_id = db.Column(db.Integer)  # ID de la facture ou de l'approvisionnement
    
    # Informations
    commentaire = db.Column(db.String(200))
    date_mouvement = db.Column(db.DateTime, default=datetime.utcnow)
    utilisateur = db.Column(db.String(100))  # Qui a fait le mouvement
    
    def __repr__(self):
        return f'<MouvementStock {self.type_mouvement} {self.quantite}>'

class Approvisionnement(db.Model):
    __tablename__ = 'approvisionnements'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    date_approvisionnement = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Fournisseur (optionnel)
    fournisseur = db.Column(db.String(200))
    reference_fournisseur = db.Column(db.String(100))
    
    # Statut
    STATUT_EN_ATTENTE = 'en_attente'
    STATUT_RECU = 'recu'
    STATUT_ANNULE = 'annule'
    
    statut = db.Column(db.String(20), default=STATUT_EN_ATTENTE)
    
    # Total
    total_ht = db.Column(db.Float, default=0.0)
    total_ttc = db.Column(db.Float, default=0.0)
    
    # Notes
    notes = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    lignes = db.relationship('LigneApprovisionnement', backref='approvisionnement', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Approvisionnement {self.numero}>'

class LigneApprovisionnement(db.Model):
    __tablename__ = 'lignes_approvisionnement'
    id = db.Column(db.Integer, primary_key=True)
    approvisionnement_id = db.Column(db.Integer, db.ForeignKey('approvisionnements.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire_ht = db.Column(db.Float, nullable=False)
    prix_unitaire_ttc = db.Column(db.Float, nullable=False)
    
    # Taxes appliquées
    tva = db.Column(db.Float, nullable=False)
    
    produit = db.relationship('Produit')
    
    @property
    def total_ht(self):
        return self.quantite * self.prix_unitaire_ht
    
    @property
    def total_ttc(self):
        return self.quantite * self.prix_unitaire_ttc
    
    def __repr__(self):
        return f'<LigneApprovisionnement {self.produit_id} x{self.quantite}>'

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    type_client = db.Column(db.String(10), nullable=False, default='person')
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))
    quartier = db.Column(db.String(100))
    avenue = db.Column(db.String(100))
    numero = db.Column(db.String(20))
    nif = db.Column(db.String(50))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    factures = db.relationship('Facture', backref='client', lazy=True)
    
    @property
    def display_name(self):
        if self.type_client == 'person':
            return f"{self.nom} {self.prenom or ''}".strip()
        else:
            return self.nom
    
    def __repr__(self):
        return f'<Client {self.display_name}>'

class Facture(db.Model):
    __tablename__ = 'factures'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    total = db.Column(db.Float, default=0.0)
    paiement = db.Column(db.String(50))
    etat = db.Column(db.String(20), default='En attente')
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

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