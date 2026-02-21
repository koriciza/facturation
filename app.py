import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import Approvisionnement, db, Client, Produit, Facture, LigneFacture, Categorie, UniteMesure, MouvementStock, LigneApprovisionnement
from datetime import datetime
from flask import request, jsonify
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func



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

migrate = Migrate(app, db)

# Create tables
with app.app_context():
    db.create_all()
    
# Helper function to serialize products - FIXED: changed 'prix' to 'pv_ttc'
#def serialize_produits(produits):
    #return [{'id': p.id, 'nom': p.nom, 'prix': p.pv_ttc} for p in produits]

def serialize_produits(produits):
    """Convertir les produits en format JSON-friendly"""
    produits_serialized = []
    for p in produits:
        produits_serialized.append({
            'id': p.id,
            'nom': p.nom,
            'code': p.code,
            'pv_ttc': p.pv_ttc,
            'tva': p.tva,
            'unite_mesure': p.unite_mesure.nom if p.unite_mesure else ''
        })
    return produits_serialized

@app.template_filter('format_number')
def format_number(value):
    try:
        if value is None:
            return "0"
        return f"{float(value):,.0f}".replace(",", " ")
    except:
        return "0"

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
        # Get form data
        type_client = request.form['type_client']
        
        # Common fields
        client_data = {
            'type_client': type_client,
            'nom': request.form['nom'],
            'telephone': request.form.get('telephone', ''),
            'email': request.form.get('email', '')
        }
        
        # Add fields based on client type
        if type_client == 'person':
            client_data['prenom'] = request.form.get('prenom', '')
            # Company fields are null for physical person
            client_data['quartier'] = request.form.get('quartier', '')
            client_data['avenue'] = request.form.get('avenue', '')
            client_data['numero'] = request.form.get('prenom', '')
            client_data['nif'] = None
        else:  # company
            client_data['prenom'] = None
            client_data['quartier'] = request.form.get('quartier', '')
            client_data['avenue'] = request.form.get('avenue', '')
            client_data['numero'] = request.form.get('numero', '')
            client_data['nif'] = request.form.get('nif', '')
        
        client = Client(**client_data)
        db.session.add(client)
        db.session.commit()
        flash('Client créé avec succès', 'success')
        return redirect(url_for('clients_list'))
    
    return render_template('client_form.html')

@app.route('/client/<int:id>/edit', methods=['GET', 'POST'])
def client_edit(id):
    client = Client.query.get_or_404(id)
    if request.method == 'POST':
        # Update common fields
        client.type_client = request.form['type_client']
        client.nom = request.form['nom']
        client.telephone = request.form.get('telephone', '')
        client.email = request.form.get('email', '')
        
        # Update fields based on client type
        if client.type_client == 'person':
            client.prenom = request.form.get('prenom', '')
            # Clear company fields
            client.quartier = None
            client.avenue = None
            client.numero = None
            client.nif = None
        else:  # company
            client.prenom = None
            client.quartier = request.form.get('quartier', '')
            client.avenue = request.form.get('avenue', '')
            client.numero = request.form.get('numero', '')
            client.nif = request.form.get('nif', '')
        
        db.session.commit()
        flash('Client modifié avec succès', 'success')
        return redirect(url_for('client_detail', id=client.id))
    
    return render_template('client_form.html', client=client)
# ---------- Facture Routes ----------

@app.route('/factures')
def factures_list():
    # Récupérer les paramètres de filtre depuis l'URL
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    search = request.args.get('search', '').strip()
    type_doc = request.args.get('type', '')
    etat = request.args.get('etat', '')
    paiement = request.args.get('paiement', '')
    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')
    
    # Construire la requête de base
    query = Facture.query
    
    # Appliquer les filtres
    if search:
        query = query.join(Client).filter(
            db.or_(
                Facture.numero.ilike(f'%{search}%'),
                Client.nom.ilike(f'%{search}%'),
                Client.prenom.ilike(f'%{search}%')
            )
        )
    
    if type_doc:
        query = query.filter(Facture.type_document == type_doc)
    
    if etat:
        query = query.filter(Facture.etat == etat)
    
    if paiement:
        query = query.filter(Facture.paiement == paiement)
    
    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d')
            query = query.filter(Facture.date_creation >= date_debut_obj)
        except ValueError:
            pass
    
    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = query.filter(Facture.date_creation <= date_fin_obj)
        except ValueError:
            pass
    
    # Pagination
    pagination = query.order_by(Facture.date_creation.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    factures = pagination.items
    
    # Calculer les statistiques
    all_factures = Facture.query.all()
    stats = {
        'total_facture': sum(f.total for f in all_factures if f.type_document == 'facture'),
        'total_avoir': sum(f.total for f in all_factures if f.type_document == 'avoir'),
        'total_net': sum(f.total for f in all_factures if f.type_document == 'facture') - 
                     sum(f.total for f in all_factures if f.type_document == 'avoir'),
        'total_impaye': sum(f.total for f in all_factures if f.etat == 'En attente' and f.type_document == 'facture'),
        'nb_factures': Facture.query.filter_by(type_document='facture').count(),
        'nb_avoirs': Facture.query.filter_by(type_document='avoir').count(),
        'nb_impaye': Facture.query.filter_by(etat='En attente', type_document='facture').count()
    }
    
    return render_template(
        'factures_list.html',
        factures=factures,
        pagination=pagination,
        stats=stats,
        search_term=search,
        selected_type=type_doc,
        selected_etat=etat,
        selected_paiement=paiement,
        date_debut=date_debut,
        date_fin=date_fin,
        per_page=per_page
    )


@app.route('/facture/<int:id>')
def facture_detail(id):
    facture = Facture.query.get_or_404(id)
    return render_template('facture.html', facture=facture)


@app.route('/facture/new')
@app.route('/facture/new/<string:type>', methods=['GET', 'POST'])
def facture_new(type='facture'):
    # Récupérer l'ID de la facture d'origine si présent dans l'URL
    facture_originale_id = request.args.get('originale', type=int)
    facture_originale = None
    
    if facture_originale_id:
        facture_originale = Facture.query.get_or_404(facture_originale_id)
        # Vérifier que c'est bien une facture (pas un avoir)
        if facture_originale.type_document != 'facture':
            flash('La facture d\'origine doit être une facture, pas un avoir', 'error')
            return redirect(url_for('factures_list'))
    
    if request.method == 'POST':
        # Générer le numéro
        last_facture = Facture.query.order_by(Facture.id.desc()).first()
        prefix = 'A' if type == 'avoir' else 'F'
        if last_facture:
            new_num = f'{prefix}{last_facture.id + 1:04d}'
        else:
            new_num = f'{prefix}0001'

        # Récupérer les données du formulaire
        client_id = request.form.get('client_id')
        paiement = request.form.get('paiement')
        etat = request.form.get('etat', 'En attente')
        notes = request.form.get('notes', '')
        
        # Pour les avoirs, récupérer la facture d'origine
        facture_originale_id = request.form.get('facture_originale_id') or None
        
        # Pour les paiements en espèces, récupérer la devise
        devise = None
        if paiement == 'espèces':
            devise = request.form.get('devise')
        
        # Créer l'avoir
        facture = Facture(
            numero=new_num,
            client_id=client_id,
            type_document=type,
            facture_originale_id=facture_originale_id,
            paiement=paiement,
            devise=devise,
            etat=etat,
            notes=notes
        )
        
        db.session.add(facture)
        db.session.flush()

        # Traiter les lignes de produits
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')
        tva_values = request.form.getlist('tva[]')

        total = 0.0
        for i in range(len(produits_ids)):
            if produits_ids[i] and quantites[i] and prix_unitaires[i]:
                quantite = float(quantites[i])
                
                ligne = LigneFacture(
                    facture_id=facture.id,
                    produit_id=int(produits_ids[i]),
                    quantite=quantite,
                    prix_unitaire=float(prix_unitaires[i]),
                    tva=float(tva_values[i]) if tva_values and i < len(tva_values) else 0
                )
                db.session.add(ligne)
                total += ligne.total_ttc if hasattr(ligne, 'total_ttc') else ligne.total_ht

        facture.total = total
        db.session.commit()
        
        flash(f'{ "Avoir" if type == "avoir" else "Facture" } créé(e) avec succès', 'success')
        return redirect(url_for('facture_detail', id=facture.id))

    # GET request - afficher le formulaire
    clients = Client.query.all()
    
    # Pour les avoirs, récupérer les factures disponibles
    factures = []
    produits_disponibles = []
    
    if type == 'avoir':
        # Si on a une facture d'origine spécifique, ne montrer que celle-là
        if facture_originale:
            factures = [facture_originale]
            # Récupérer uniquement les produits de cette facture
            produits_disponibles = [ligne.produit for ligne in facture_originale.lignes]
            # Supprimer les doublons (si un produit apparaît plusieurs fois)
            produits_disponibles = list({p.id: p for p in produits_disponibles}.values())
        else:
            factures = Facture.query.filter_by(type_document='facture').all()
            produits_disponibles = Produit.query.all()
    else:
        produits_disponibles = Produit.query.all()
    
    produits_serialized = serialize_produits(produits_disponibles)
    
    return render_template('facture_form.html', 
                         clients=clients, 
                         produits=produits_disponibles,
                         produits_serialized=produits_serialized,
                         factures=factures,
                         facture_originale=facture_originale,
                         type_document=type,
                         facture=None)

@app.route('/facture/<int:id>/edit', methods=['GET', 'POST'])
def facture_edit(id):
    facture = Facture.query.get_or_404(id)
    
    if request.method == 'POST':
        facture.client_id = request.form.get('client_id')
        facture.paiement = request.form.get('paiement')
        facture.etat = request.form.get('etat', 'En attente')
        facture.notes = request.form.get('notes', '')
        
        # Mettre à jour la devise si nécessaire
        if facture.paiement == 'espèces':
            facture.devise = request.form.get('devise')
        else:
            facture.devise = None
        
        # Pour les avoirs, mettre à jour la facture d'origine
        if facture.type_document == 'avoir':
            facture.facture_originale_id = request.form.get('facture_originale_id') or None

        # Supprimer les anciennes lignes
        LigneFacture.query.filter_by(facture_id=facture.id).delete()

        # Ajouter les nouvelles lignes
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')
        tva_values = request.form.getlist('tva[]')

        total = 0.0
        for i in range(len(produits_ids)):
            if produits_ids[i] and quantites[i] and prix_unitaires[i]:
                quantite = float(quantites[i])
                # Pour les avoirs, garder les quantités négatives si elles existent
                
                ligne = LigneFacture(
                    facture_id=facture.id,
                    produit_id=int(produits_ids[i]),
                    quantite=quantite,
                    prix_unitaire=float(prix_unitaires[i]),
                    tva=float(tva_values[i]) if tva_values and i < len(tva_values) else 0
                )
                db.session.add(ligne)
                total += ligne.total_ttc

        facture.total = total
        db.session.commit()
        
        flash('Document modifié avec succès', 'success')
        return redirect(url_for('facture_detail', id=facture.id))

    # GET request - afficher le formulaire avec les données existantes
    clients = Client.query.all()
    produits = Produit.query.all()
    produits_serialized = serialize_produits(produits)

    # Récupérer les produits bruts POUR LES TEMPLATES
    produits_bruts = Produit.query.all()
    
    # Sérialiser les produits POUR LE JAVASCRIPT
    produits_serialized = serialize_produits(produits_bruts)
    
    # Pour les avoirs, lister les factures disponibles (sauf celle-ci)
    factures = []
    if facture.type_document == 'avoir':
        factures = Facture.query.filter_by(type_document='facture')\
                               .filter(Facture.id != facture.id)\
                               .all()
    
    return render_template('facture_form.html', 
                         facture=facture,
                         clients=clients, 
                         produits=produits_bruts,  # ← Pour les boucles Jinja
                         produits_serialized =produits_serialized,
                         factures=factures,
                         type_document=facture.type_document)

@app.route('/facture/<int:id>/convertir_en_avoir', methods=['POST'])
def convertir_en_avoir(id):
    """Convertir une facture en avoir"""
    facture_originale = Facture.query.get_or_404(id)
    
    # Vérifier que c'est bien une facture
    if facture_originale.type_document != 'facture':
        flash('Seules les factures peuvent être converties en avoirs', 'error')
        return redirect(url_for('facture_detail', id=id))
    
    # Générer un numéro pour l'avoir
    last_facture = Facture.query.order_by(Facture.id.desc()).first()
    new_num = f'A{last_facture.id + 1:04d}' if last_facture else 'A0001'
    
    # Créer l'avoir
    avoir = Facture(
        numero=new_num,
        client_id=facture_originale.client_id,
        type_document='avoir',
        facture_originale_id=facture_originale.id,
        notes=f"Avoir pour facture {facture_originale.numero}",
        etat='En attente'
    )
    
    db.session.add(avoir)
    db.session.flush()
    
    # Copier les lignes avec des quantités négatives
    for ligne in facture_originale.lignes:
        ligne_avoir = LigneFacture(
            facture_id=avoir.id,
            produit_id=ligne.produit_id,
            quantite=-ligne.quantite,  # Négatif pour l'avoir
            prix_unitaire=ligne.prix_unitaire,
            tva=ligne.tva
        )
        db.session.add(ligne_avoir)
    
    # Calculer le total
    avoir.total = sum(l.total_ttc for l in avoir.lignes)
    
    db.session.commit()
    flash('Avoir créé avec succès', 'success')
    return redirect(url_for('facture_edit', id=avoir.id))

# ---------- Product Routes ----------
@app.route('/produits')
def produits_list():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Filter parameters
    search = request.args.get('search', '').strip()
    categorie_id = request.args.get('categorie_id', type=int)
    unite_id = request.args.get('unite_id', type=int)
    tc_filter = request.args.get('tc', '')
    pf_filter = request.args.get('pf', '')
    stockable_filter = request.args.get('stockable', '')
    
    # Build base query with eager loading for relationships
    # IMPORTANT: Use the RELATIONSHIP names, not the foreign key columns
    query = Produit.query.options(
        joinedload(Produit.unite_mesure),  # This is the relationship
        joinedload(Produit.categorie)      # This is the relationship
    )
    
    # Apply filters - here we use the COLUMN names (with _id suffix)
    if search:
        query = query.filter(
            or_(
                Produit.nom.ilike(f'%{search}%'),
                Produit.code.ilike(f'%{search}%')
            )
        )
    
    if categorie_id:
        query = query.filter(Produit.categorie_id == categorie_id)  # Column name
    
    if unite_id:
        query = query.filter(Produit.unite_mesure_id == unite_id)  # Column name
    
    if tc_filter:
        query = query.filter(Produit.tc == tc_filter)
    
    if pf_filter:
        query = query.filter(Produit.pf == pf_filter)
    
    if stockable_filter == 'true':
        query = query.filter(Produit.article_stockable == True)
    elif stockable_filter == 'false':
        query = query.filter(Produit.article_stockable == False)
    
    # Order by
    sort_by = request.args.get('sort_by', 'nom')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Handle sorting for relationship fields
    if sort_by == 'categorie':
        # If sorting by category name
        if sort_order == 'asc':
            query = query.join(Produit.categorie).order_by(Categorie.nom.asc())
        else:
            query = query.join(Produit.categorie).order_by(Categorie.nom.desc())
    elif sort_by == 'unite_mesure':
        # If sorting by unit name
        if sort_order == 'asc':
            query = query.join(Produit.unite_mesure).order_by(UniteMesure.nom.asc())
        else:
            query = query.join(Produit.unite_mesure).order_by(UniteMesure.nom.desc())
    else:
        # Regular column sorting
        if sort_order == 'asc':
            query = query.order_by(getattr(Produit, sort_by))
        else:
            query = query.order_by(getattr(Produit, sort_by).desc())
    
    # Get paginated results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    produits = pagination.items
    
    # Get filter options (for dropdowns)
    categories = Categorie.query.order_by(Categorie.nom).all()
    unites = UniteMesure.query.order_by(UniteMesure.nom).all()
    
    return render_template('produits_list.html',
                         produits=produits,
                         pagination=pagination,
                         categories=categories,
                         unites=unites,
                         search_term=search,
                         selected_categorie=categorie_id,
                         selected_unite=unite_id,
                         selected_tc=tc_filter,
                         selected_pf=pf_filter,
                         selected_stockable=stockable_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         per_page=per_page)


@app.route('/produit/<int:id>')
def produit_detail(id):
    produit = Produit.query.get_or_404(id)
    return render_template('produit.html', produit=produit)

@app.route('/produit/new', methods=['GET', 'POST'])
def produit_new():
    if request.method == 'POST':
        try:
            tc_value = request.form.get('tc', 'NON')
            pf_value = request.form.get('pf', 'NON')
            
            # Check if article is stockable
            article_stockable = request.form.get('article_stockable', 'NON')
            
            # Get stock values if stockable
            quantite_initiale = 0
            stock_minimum = 0
            pru = 0
            
            if article_stockable == 'OUI':
                quantite_initiale = float(request.form.get('quantite_initiale', 0))
                stock_minimum = float(request.form.get('stock_minimum', 0))
                pru = float(request.form.get('pru', 0))

            # Check if code already exists (optional - can rely on IntegrityError)
            code = request.form.get('code', '')
            if code:
                existing_product = Produit.query.filter_by(code=code).first()
                if existing_product:
                    flash(f'Le code "{code}" est déjà utilisé par le produit "{existing_product.nom}". Veuillez choisir un code différent.', 'error')
                    return redirect(url_for('produit_new'))    
            
            # Create product with all fields
            produit = Produit(
                nom=request.form['nom'],
                code=request.form.get('code', ''),
                unite_mesure_id=int(request.form['unite_mesure_id']),
                categorie_id=int(request.form['categorie_id']),
                tva=float(request.form['tva']),
                tc=tc_value,
                pf=pf_value,
                article_stockable=article_stockable,
                pv_ttc=float(request.form['pv_ttc']),
                quantite_initiale=quantite_initiale,
                stock_minimum=stock_minimum,
                pru=pru,
                stock_actuel=quantite_initiale  # Set current stock to initial quantity
            )
            
            # Add and flush to get an ID
            db.session.add(produit)
            db.session.flush()  # This assigns an ID and saves to DB temporarily
            
            # If stockable and has initial quantity, create stock movement
            if article_stockable == 'OUI' and quantite_initiale > 0:
                mouvement = MouvementStock(
                    produit_id=produit.id,
                    type_mouvement='entree',
                    quantite=quantite_initiale,
                    stock_avant=0,
                    stock_apres=quantite_initiale,
                    reference_type='initial',
                    reference_id=None,
                    commentaire='Stock initial',
                    date_mouvement=datetime.utcnow(),
                    utilisateur='System'
                )
                db.session.add(mouvement)
            
            # Commit everything
            db.session.commit()
            
            flash('Produit créé avec succès', 'success')
            return redirect(url_for('produits_list'))
        

        except IntegrityError as e:
            db.session.rollback()
            # Check if it's a unique constraint violation for code
            if 'unique' in str(e).lower() and 'code' in str(e).lower():
                flash(f'Erreur: Le code "{request.form.get("code", "")}" est déjà utilisé. Veuillez choisir un code différent.', 'error')
            else:
                # Other integrity error
                flash(f'Erreur de base de données: {str(e)}', 'error')
            return redirect(url_for('produit_new'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création: {str(e)}', 'error')
            return redirect(url_for('produit_new'))
    
    # GET request - show form
    categories = Categorie.query.all()
    unites = UniteMesure.query.all()
    options_tva = [0, 5.5, 10, 20]
    options_tc = [0, 1, 2, 5]
    options_pf = [0, 0.5, 1, 2]
    
    return render_template('produit_form.html', 
                         categories=categories,
                         unites=unites,
                         options_tva=options_tva,
                         options_tc=options_tc,
                         options_pf=options_pf,
                         produit=None)

@app.route('/produit/<int:id>/edit', methods=['GET', 'POST'])
def produit_edit(id):
    produit = Produit.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Check if code already exists (excluding current product)
            code = request.form.get('code', '')
            if code and code != produit.code:
                existing_product = Produit.query.filter(Produit.code == code, Produit.id != id).first()
                if existing_product:
                    flash(f'Le code "{code}" est déjà utilisé par le produit "{existing_product.nom}". Veuillez choisir un code différent.', 'error')
                    return redirect(url_for('produit_edit', id=id))
            
            # Update product fields
            produit.nom = request.form['nom']
            produit.code = code
            produit.unite_mesure_id = int(request.form['unite_mesure_id'])
            produit.categorie_id = int(request.form['categorie_id'])
            produit.tva = float(request.form['tva'])
            produit.tc = request.form.get('tc', 'NON')
            produit.pf = request.form.get('pf', 'NON')
            
            article_stockable = request.form.get('article_stockable', 'NON')
            produit.article_stockable = article_stockable
            produit.pv_ttc = float(request.form['pv_ttc'])

            # Update stock fields based on stockable status
            if article_stockable == 'OUI':
                produit.quantite_initiale = float(request.form.get('quantite_initiale', produit.quantite_initiale))
                produit.stock_minimum = float(request.form.get('stock_minimum', produit.stock_minimum))
                produit.pru = float(request.form.get('pru', produit.pru))
                # Note: stock_actuel is managed through stock movements
            else:
                produit.quantite_initiale = 0
                produit.stock_minimum = 0
                produit.pru = 0
                produit.stock_actuel = 0
            
            db.session.commit()
            flash('Produit modifié avec succès', 'success')
            return redirect(url_for('produit_detail', id=produit.id))
            
        except IntegrityError as e:
            db.session.rollback()
            if 'unique' in str(e).lower() and 'code' in str(e).lower():
                flash(f'Erreur: Le code "{request.form.get("code", "")}" est déjà utilisé. Veuillez choisir un code différent.', 'error')
            else:
                flash(f'Erreur de base de données: {str(e)}', 'error')
            return redirect(url_for('produit_edit', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'error')
            return redirect(url_for('produit_edit', id=id))
    
    # GET request - show form
    unites = UniteMesure.query.all()
    categories = Categorie.query.all()
    return render_template('produit_form.html', 
                         produit=produit,
                         unites=unites, 
                         categories=categories)
    
@app.route('/produit/<int:id>/delete', methods=['POST'])
def produit_delete(id):
    produit = Produit.query.get_or_404(id)
    try:
        db.session.delete(produit)
        db.session.commit()
        flash('Produit supprimé avec succès', 'success')
    except:
        flash('Impossible de supprimer ce produit (utilisé dans des factures)', 'error')
    return redirect(url_for('produits_list'))

@app.route('/api/check-code')
def check_code():
    """Check if a product code already exists"""
    code = request.args.get('code', '').strip()
    produit_id = request.args.get('produit_id', 0, type=int)
    
    if not code:
        return jsonify({'exists': False})
    
    # Query excluding current product if in edit mode
    query = Produit.query.filter(Produit.code == code)
    if produit_id:
        query = query.filter(Produit.id != produit_id)
    
    exists = query.first() is not None
    
    return jsonify({
        'exists': exists,
        'code': code
    })

@app.route('/categories')
def categories_list():
    categories = Categorie.query.all()
    return render_template('categories_list.html', categories=categories)

@app.route('/categorie/new', methods=['GET', 'POST'])
def categorie_new():
    if request.method == 'POST':
        categorie = Categorie(
            nom=request.form['nom'],
            description=request.form.get('description', '')
        )
        db.session.add(categorie)
        db.session.commit()
        flash('Catégorie créée avec succès', 'success')
        return redirect(url_for('categories_list'))
    return render_template('categorie_form.html')

@app.route('/categorie/<int:id>/edit', methods=['GET', 'POST'])
def categorie_edit(id):
    categorie = Categorie.query.get_or_404(id)
    if request.method == 'POST':
        categorie.nom = request.form['nom']
        categorie.description = request.form.get('description', '')
        db.session.commit()
        flash('Catégorie modifiée avec succès', 'success')
        return redirect(url_for('categories_list'))
    return render_template('categorie_form.html', categorie=categorie)

@app.route('/categorie/<int:id>/delete', methods=['POST'])
def categorie_delete(id):
    categorie = Categorie.query.get_or_404(id)
    try:
        db.session.delete(categorie)
        db.session.commit()
        flash('Catégorie supprimée avec succès', 'success')
    except:
        flash('Impossible de supprimer cette catégorie (utilisée par des produits)', 'error')
    return redirect(url_for('categories_list'))

# ---------- Unités de Mesure Routes ----------
@app.route('/unites')
def unites_list():
    unites = UniteMesure.query.all()
    return render_template('unites_list.html', unites=unites)

@app.route('/unite/new', methods=['GET', 'POST'])
def unite_new():
    if request.method == 'POST':
        unite = UniteMesure(
            nom=request.form['nom'],
            symbole=request.form.get('symbole', ''),
            description=request.form.get('description', '')
        )
        db.session.add(unite)
        db.session.commit()
        flash('Unité de mesure créée avec succès', 'success')
        return redirect(url_for('unites_list'))
    return render_template('unite_form.html')

@app.route('/unite/<int:id>/edit', methods=['GET', 'POST'])
def unite_edit(id):
    unite = UniteMesure.query.get_or_404(id)
    if request.method == 'POST':
        unite.nom = request.form['nom']
        unite.symbole = request.form.get('symbole', '')
        unite.description = request.form.get('description', '')
        db.session.commit()
        flash('Unité de mesure modifiée avec succès', 'success')
        return redirect(url_for('unites_list'))
    return render_template('unite_form.html', unite=unite)

@app.route('/unite/<int:id>/delete', methods=['POST'])
def unite_delete(id):
    unite = UniteMesure.query.get_or_404(id)
    try:
        db.session.delete(unite)
        db.session.commit()
        flash('Unité de mesure supprimée avec succès', 'success')
    except:
        flash('Impossible de supprimer cette unité (utilisée par des produits)', 'error')
    return redirect(url_for('unites_list'))


@app.route('/api/unites', methods=['POST'])
def api_create_unite():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('nom'):
            return jsonify({'success': False, 'message': 'Le nom est requis'}), 400
        
        # Create new unit
        unite = UniteMesure(
            nom=data['nom'],
            symbole=data.get('symbole', ''),
            description=data.get('description', '')
        )
        
        db.session.add(unite)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'unite': {
                'id': unite.id,
                'nom': unite.nom,
                'symbole': unite.symbole
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def api_create_categorie():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('nom'):
            return jsonify({'success': False, 'message': 'Le nom est requis'}), 400
        
        # Create new category
        categorie = Categorie(
            nom=data['nom'],
            description=data.get('description', '')
        )
        
        db.session.add(categorie)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'categorie': {
                'id': categorie.id,
                'nom': categorie.nom,
                'description': categorie.description
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
# ---------- Stock Routes ----------
@app.route('/stock')
def stock_list():
    produits = Produit.query.filter_by(article_stockable="OUI").all()
    return render_template('stock_list.html', produits=produits)

@app.route('/stock/mouvements/<int:produit_id>')
def stock_mouvements(produit_id):
    produit = Produit.query.get_or_404(produit_id)
    mouvements = MouvementStock.query.filter_by(produit_id=produit_id).order_by(MouvementStock.date_mouvement.desc()).all()
    return render_template('stock_mouvements.html', produit=produit, mouvements=mouvements)

@app.route('/stock/ajuster/<int:produit_id>', methods=['GET', 'POST'])
def stock_ajuster(produit_id):
    produit = Produit.query.get_or_404(produit_id)
    if request.method == 'POST':
        nouvelle_quantite = int(request.form['nouvelle_quantite'])
        commentaire = request.form.get('commentaire', '')
        
        # Enregistrer le mouvement
        mouvement = MouvementStock(
            produit_id=produit.id,
            type_mouvement=MouvementStock.TYPE_AJUSTEMENT,
            quantite=abs(nouvelle_quantite - produit.stock_actuel),
            stock_avant=produit.stock_actuel,
            stock_apres=nouvelle_quantite,
            commentaire=commentaire,
            utilisateur='admin'  # À améliorer avec système d'auth
        )
        
        produit.stock_actuel = nouvelle_quantite
        db.session.add(mouvement)
        db.session.commit()
        
        flash('Stock ajusté avec succès', 'success')
        return redirect(url_for('stock_mouvements', produit_id=produit.id))
    
    return render_template('stock_ajuster.html', produit=produit)

# ---------- Approvisionnement Routes ----------
@app.route('/approvisionnements')
def approvisionnements_list():
    appros = Approvisionnement.query.order_by(Approvisionnement.date_approvisionnement.desc()).all()
    return render_template('approvisionnements_list.html', appros=appros)

@app.route('/approvisionnement/<int:id>')
def approvisionnement_detail(id):
    appro = Approvisionnement.query.get_or_404(id)
    return render_template('approvisionnement.html', appro=appro)

@app.route('/approvisionnement/new', methods=['GET', 'POST'])
def approvisionnement_new():
    if request.method == 'POST':
        # Générer numéro
        last_appro = Approvisionnement.query.order_by(Approvisionnement.id.desc()).first()
        if last_appro:
            new_num = f'APP{last_appro.id + 1:04d}'
        else:
            new_num = 'APP0001'

        appro = Approvisionnement(
            numero=new_num,
            fournisseur=request.form.get('fournisseur', ''),
            reference_fournisseur=request.form.get('reference_fournisseur', ''),
            statut=Approvisionnement.STATUT_EN_ATTENTE,
            notes=request.form.get('notes', '')
        )
        db.session.add(appro)
        db.session.flush()

        # Traiter les lignes
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_ht = request.form.getlist('prix_ht[]')
        tva_list = request.form.getlist('tva[]')

        total_ht = 0.0
        total_ttc = 0.0

        for i in range(len(produits_ids)):
            if produits_ids[i] and quantites[i] and prix_ht[i]:
                produit = Produit.query.get(int(produits_ids[i]))
                tva = float(tva_list[i]) if i < len(tva_list) else produit.tva
                
                prix_unitaire_ht = float(prix_ht[i])
                prix_unitaire_ttc = prix_unitaire_ht * (1 + tva/100)
                
                ligne = LigneApprovisionnement(
                    approvisionnement_id=appro.id,
                    produit_id=int(produits_ids[i]),
                    quantite=int(quantites[i]),
                    prix_unitaire_ht=prix_unitaire_ht,
                    prix_unitaire_ttc=prix_unitaire_ttc,
                    tva=tva
                )
                db.session.add(ligne)
                
                total_ht += ligne.total_ht
                total_ttc += ligne.total_ttc

        appro.total_ht = total_ht
        appro.total_ttc = total_ttc
        db.session.commit()
        
        flash('Approvisionnement créé avec succès', 'success')
        return redirect(url_for('approvisionnement_detail', id=appro.id))

    produits = Produit.query.filter_by(article_stockable="OUI").all()
    produits_serialized = [{'id': p.id, 'nom': p.nom, 'tva': p.tva} for p in produits]
    return render_template('approvisionnement_form.html', produits=produits_serialized)

@app.route('/approvisionnement/<int:id>/recevoir', methods=['POST'])
def approvisionnement_recevoir(id):
    appro = Approvisionnement.query.get_or_404(id)
    
    if appro.statut == Approvisionnement.STATUT_EN_ATTENTE:
        for ligne in appro.lignes:
            # Mettre à jour le stock
            produit = ligne.produit
            ancien_stock = produit.stock_actuel
            
            # Créer mouvement de stock
            mouvement = MouvementStock(
                produit_id=produit.id,
                type_mouvement=MouvementStock.TYPE_ENTREE,
                quantite=ligne.quantite,
                stock_avant=ancien_stock,
                stock_apres=ancien_stock + ligne.quantite,
                reference_type='approvisionnement',
                reference_id=appro.id,
                commentaire=f"Réception approvisionnement {appro.numero}",
                utilisateur='admin'
            )
            
            produit.stock_actuel += ligne.quantite
            db.session.add(mouvement)
        
        appro.statut = Approvisionnement.STATUT_RECU
        db.session.commit()
        flash('Approvisionnement reçu et stock mis à jour', 'success')
    
    return redirect(url_for('approvisionnement_detail', id=appro.id))

@app.route('/approvisionnement/<int:id>/annuler', methods=['POST'])
def approvisionnement_annuler(id):
    appro = Approvisionnement.query.get_or_404(id)
    appro.statut = Approvisionnement.STATUT_ANNULE
    db.session.commit()
    flash('Approvisionnement annulé', 'success')
    return redirect(url_for('approvisionnement_detail', id=appro.id))  

##------------------Rapports------------------


@app.route('/rapports')
def rapports_index():
    """Page d'accueil des rapports"""
    return render_template('rapports_index.html')

@app.route('/rapports/client', methods=['GET', 'POST'])
def rapport_client():
    """Rapport pour un client spécifique sur une période"""
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        date_debut = request.form.get('date_debut')
        date_fin = request.form.get('date_fin')

        maintenant = datetime.now()
        
        # Convertir les dates
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d')
            date_fin_obj = datetime.strptime(date_fin + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            flash('Veuillez fournir des dates valides', 'error')
            return redirect(url_for('rapport_client'))
        
        # Récupérer le client
        client = Client.query.get_or_404(client_id)
        
        # Récupérer les factures du client sur la période
        factures = Facture.query.filter(
            Facture.client_id == client_id,
            Facture.date_creation >= date_debut_obj,
            Facture.date_creation <= date_fin_obj,
            Facture.type_document == 'facture'
        ).order_by(Facture.date_creation).all()
        
        # Récupérer les avoirs du client sur la période
        avoirs = Facture.query.filter(
            Facture.client_id == client_id,
            Facture.date_creation >= date_debut_obj,
            Facture.date_creation <= date_fin_obj,
            Facture.type_document == 'avoir'
        ).order_by(Facture.date_creation).all()
        
        # Calculer les totaux
        total_factures = sum(f.total for f in factures)
        total_avoirs = sum(a.total for a in avoirs)
        net_a_payer = total_factures - total_avoirs
        
        # Factures payées vs impayées
        factures_payees = [f for f in factures if f.etat == 'Payée']
        factures_impayees = [f for f in factures if f.etat == 'En attente']
        total_paye = sum(f.total for f in factures_payees)
        total_impaye = sum(f.total for f in factures_impayees)
        
        # Statistiques par mode de paiement
        paiements = {}
        for f in factures:
            mode = f.paiement or 'Non spécifié'
            if mode not in paiements:
                paiements[mode] = {'count': 0, 'total': 0}
            paiements[mode]['count'] += 1
            paiements[mode]['total'] += f.total
        
        return render_template('rapport_client_resultat.html',
                             client=client,
                             date_debut=date_debut_obj,
                             date_fin=date_fin_obj,
                             factures=factures,
                             avoirs=avoirs,
                             total_factures=total_factures,
                             total_avoirs=total_avoirs,
                             net_a_payer=net_a_payer,
                             total_paye=total_paye,
                             total_impaye=total_impaye,
                             paiements=paiements,
                             maintenant=maintenant,
                             nb_factures=len(factures),
                             nb_avoirs=len(avoirs))
    
    # GET request - afficher le formulaire
    clients = Client.query.order_by(Client.nom).all()
    maintenant = datetime.now()
    return render_template('rapport_client_form.html', clients=clients, maintenant=maintenant)

@app.route('/rapports/tous-clients', methods=['GET', 'POST'])
def rapport_tous_clients():
    """Rapport pour tous les clients sur une période"""
    if request.method == 'POST':
        date_debut = request.form.get('date_debut')
        date_fin = request.form.get('date_fin')

        maintenant = datetime.now()
        
        # Convertir les dates
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d')
            date_fin_obj = datetime.strptime(date_fin + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            flash('Veuillez fournir des dates valides', 'error')
            return redirect(url_for('rapport_tous_clients'))
        
        # Récupérer tous les clients
        clients = Client.query.order_by(Client.nom).all()
        
        # Statistiques globales
        stats_clients = []
        total_general_factures = 0
        total_general_avoirs = 0
        total_general_net = 0
        
        for client in clients:
            # Factures du client sur la période
            factures = Facture.query.filter(
                Facture.client_id == client.id,
                Facture.date_creation >= date_debut_obj,
                Facture.date_creation <= date_fin_obj,
                Facture.type_document == 'facture'
            ).all()
            
            # Avoirs du client sur la période
            avoirs = Facture.query.filter(
                Facture.client_id == client.id,
                Facture.date_creation >= date_debut_obj,
                Facture.date_creation <= date_fin_obj,
                Facture.type_document == 'avoir'
            ).all()
            
            total_factures = sum(f.total for f in factures)
            total_avoirs = sum(a.total for a in avoirs)
            net = total_factures - total_avoirs
            
            if total_factures > 0 or total_avoirs > 0:  # N'inclure que les clients avec activité
                stats_clients.append({
                    'client': client,
                    'nb_factures': len(factures),
                    'nb_avoirs': len(avoirs),
                    'total_factures': total_factures,
                    'total_avoirs': total_avoirs,
                    'net': net
                })
                
                total_general_factures += total_factures
                total_general_avoirs += total_avoirs
                total_general_net += net
        
        # Trier par net (du plus grand au plus petit)
        stats_clients.sort(key=lambda x: x['net'], reverse=True)
        
        # Statistiques globales supplémentaires
        toutes_factures = Facture.query.filter(
            Facture.date_creation >= date_debut_obj,
            Facture.date_creation <= date_fin_obj,
            Facture.type_document == 'facture'
        ).all()
        
        total_toutes_factures = sum(f.total for f in toutes_factures)
        nb_total_factures = len(toutes_factures)
        
        # Paiements par mode
        paiements = {}
        for f in toutes_factures:
            mode = f.paiement or 'Non spécifié'
            if mode not in paiements:
                paiements[mode] = {'count': 0, 'total': 0}
            paiements[mode]['count'] += 1
            paiements[mode]['total'] += f.total
        
        return render_template('rapport_tous_clients_resultat.html',
                             date_debut=date_debut_obj,
                             date_fin=date_fin_obj,
                             stats_clients=stats_clients,
                             total_general_factures=total_general_factures,
                             total_general_avoirs=total_general_avoirs,
                             total_general_net=total_general_net,
                             total_toutes_factures=total_toutes_factures,
                             nb_total_factures=nb_total_factures,
                             paiements=paiements,
                             maintenant=maintenant,
                             nb_clients_actifs=len(stats_clients))
    
    # GET request - afficher le formulaire
    maintenant = datetime.now()
    return render_template('rapport_tous_clients_form.html', maintenant=maintenant)






if __name__ == '__main__':
    app.run(debug=True)