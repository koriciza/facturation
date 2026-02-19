import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Client, Produit, Facture, LigneFacture, Categorie, UniteMesure
from datetime import datetime
from flask import request, jsonify
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload
from sqlalchemy import or_


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
def serialize_produits(produits):
    return [{'id': p.id, 'nom': p.nom, 'prix': p.pv_ttc} for p in produits]

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

        tc_value = request.form.get('tc', 'NON')  # Default to 'NON' if not provided
        pf_value = request.form.get('pf', 'NON')  # Default to 'NON' if not provided

        produit = Produit(
            nom=request.form['nom'],
            code=request.form.get('code', ''),
            unite_mesure_id=int(request.form['unite_mesure_id']),
            categorie_id=int(request.form['categorie_id']),
            tva=float(request.form['tva']),
            tc=tc_value,
            pf=pf_value,
            article_stockable='article_stockable' in request.form,
            pv_ttc=float(request.form['pv_ttc'])
        )
        db.session.add(produit)
        db.session.commit()
        flash('Produit créé avec succès', 'success')
        return redirect(url_for('produits_list'))
    
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
                         options_pf=options_pf)

@app.route('/produit/<int:id>/edit', methods=['GET', 'POST'])
def produit_edit(id):
    produit = Produit.query.get_or_404(id)
    
    if request.method == 'POST':
        produit.nom = request.form['nom']
        produit.code = request.form.get('code', '')
        produit.unite_mesure_id = int(request.form['unite_mesure_id'])
        produit.categorie_id = int(request.form['categorie_id'])
        produit.tva = float(request.form['tva'])
        
        # Fix: Handle TC and PF as strings, not floats
        produit.tc = request.form.get('tc', 'NON')  # Now stores 'OUI' or 'NON'
        produit.pf = request.form.get('pf', 'NON')  # Now stores 'OUI' or 'NON'
        
        produit.article_stockable = 'article_stockable' in request.form
        produit.pv_ttc = float(request.form['pv_ttc'])
        
        db.session.commit()
        flash('Produit modifié avec succès', 'success')
        return redirect(url_for('produit_detail', id=produit.id))
    
    # GET request - show the form with existing data
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

if __name__ == '__main__':
    app.run(debug=True)