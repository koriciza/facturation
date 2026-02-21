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

    # Relationships
    unite_mesure = db.relationship('UniteMesure', backref='produits')
    categorie = db.relationship('Categorie', backref='produits')
    
    # Tax fields
    tva = db.Column(db.Float, nullable=False, default=0.0)
    tc = db.Column(db.String(5), nullable=False)
    pf = db.Column(db.String(5), nullable=False)
    article_stockable = db.Column(db.String(5), nullable=False)
    pv_ttc = db.Column(db.Float, nullable=False, default=0.0)
    
    # New stock fields
    quantite_initiale = db.Column(db.Float, default=0.0)  # Initial quantity
    stock_minimum = db.Column(db.Float, default=0.0)  # Alert threshold
    pru = db.Column(db.Float, default=0.0)  # Prix de revient unitaire
    stock_actuel = db.Column(db.Float, default=0.0)  # Current stock (calculated from movements)
    
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    lignes_facture = db.relationship('LigneFacture', backref='produit_ref', lazy=True)
    mouvements_stock = db.relationship('MouvementStock', backref='produit', lazy=True, cascade='all, delete-orphan')

    """ 
        Add a stock movement and update current stock
    """

    def ajouter_mouvement_stock(self, type_mouvement, quantite, reference_type=None, 
                                reference_id=None, commentaire=None, utilisateur=None):
        
        stock_avant = self.stock_actuel or 0
        
        if type_mouvement == MouvementStock.TYPE_ENTREE:
            self.stock_actuel = stock_avant + quantite
        elif type_mouvement == MouvementStock.TYPE_SORTIE:
            self.stock_actuel = max(0, stock_avant - quantite)  # Prevent negative stock
        elif type_mouvement == MouvementStock.TYPE_AJUSTEMENT:
            self.stock_actuel = quantite  # Direct adjustment
        
        stock_apres = self.stock_actuel
        
        mouvement = MouvementStock(
            produit_id=self.id,
            type_mouvement=type_mouvement,
            quantite=quantite,
            stock_avant=stock_avant,
            stock_apres=stock_apres,
            reference_type=reference_type,
            reference_id=reference_id,
            commentaire=commentaire,
            date_mouvement=datetime.utcnow(),
            utilisateur=utilisateur
        )
        
        return mouvement

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
    quantite = db.Column(db.Float, nullable=False)
    stock_avant = db.Column(db.Float, nullable=False)
    stock_apres = db.Column(db.Float, nullable=False)

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
    
    # Changement 1: Utilisation de back_populates au lieu de backref
    factures = db.relationship('Facture', back_populates='client', lazy=True)
    
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
    numero = db.Column(db.String(20), unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Type de document (facture ou avoir)
    type_document = db.Column(db.String(20), default='facture')
    
    # Lien vers la facture d'origine (pour les avoirs)
    facture_originale_id = db.Column(db.Integer, db.ForeignKey('factures.id'), nullable=True)
    facture_originale = db.relationship('Facture', remote_side=[id], backref='avoirs')
    
    # Devise pour paiement en espèces
    devise = db.Column(db.String(10), nullable=True)
    
    # Champs existants
    paiement = db.Column(db.String(50))
    etat = db.Column(db.String(50), default='En attente')
    total = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    
    # Changement 2: Utilisation de back_populates au lieu de backref='factures'
    client = db.relationship('Client', back_populates='factures')
    lignes = db.relationship('LigneFacture', backref='facture', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Facture {self.numero}>'
    

class LigneFacture(db.Model):
    __tablename__ = 'lignes_facture'
    
    id = db.Column(db.Integer, primary_key=True)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    
    quantite = db.Column(db.Float, nullable=False)  # Changé de Integer à Float
    prix_unitaire = db.Column(db.Float, nullable=False)
    tva = db.Column(db.Float, default=0)  # NOUVEAU : TVA par ligne
    
    # Relations
    produit = db.relationship('Produit')
    
    @property
    def total_ht(self):
        return self.quantite * self.prix_unitaire
    
    @property
    def total_ttc(self):
        return self.total_ht * (1 + self.tva/100)