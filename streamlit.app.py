import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Système Intégré - Gestion des Stocks & Logistique", layout="wide")
st.title("🚛 Système Intégré de Gestion des Stocks & Logistique")
st.write("Application unifiée : Référentiel matériel et suivi des mouvements d'entrées/sorties par secteur et camion.")

# --- INITIALISATION DE LA BASE DE DONNÉES EN MÉMOIRE ---
if 'articles' not in st.session_state:
    # Référentiel initial propre sans prix unitaire
    st.session_state.articles = pd.DataFrame(columns=["Référence", "Désignation", "Catégorie", "Stock Initial"])

if 'mouvements' not in st.session_state:
    # Historique global des flux
    st.session_state.mouvements = pd.DataFrame(columns=[
        "Date", "Référence", "Type", "Quantité", "Secteur / Destination", "Emplacement", "Pièce / Matricule Camion"
    ])

# --- FONCTIONS DE CALCUL DYNAMIQUE ---
def calculer_stock_actuel(ref):
    """Calcule le stock restant réel pour une référence spécifique"""
    art_ligne = st.session_state.articles[st.session_state.articles["Référence"] == ref]
    if art_ligne.empty:
        return 0
    stock_initial = int(art_ligne.iloc[0]["Stock Initial"])
    
    # Filtrage des mouvements pour l'article
    mov_art = st.session_state.mouvements[st.session_state.mouvements["Référence"] == ref]
    entrees = mov_art[mov_art["Type"] == "Entrée"]["Quantité"].sum()
    sorties = mov_art[mov_art["Type"] == "Sortie"]["Quantité"].sum()
    
    return stock_initial + entrees - sorties

def obtenir_table_stock_global():
    """Génère le tableau final mis à jour avec la colonne dynamique 'Reste'"""
    if st.session_state.articles.empty:
        return st.session_state.articles
    df = st.session_state.articles.copy()
    df["Reste en Stock"] = df["Référence"].apply(calculer_stock_actuel)
    return df

# --- FONCTION EXPORT PDF ---
def generer_pdf(df_stock, df_mov):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, spaceAfter=15, textColor=colors.HexColor("#1A365D"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading2'], fontSize=12, spaceAfter=10, textColor=colors.HexColor("#2B6CB0"))
    
    # Section 1 : Tableau d'état des stocks
    story.append(Paragraph("Rapport Général de l'État des Stocks", title_style))
    table_data = [list(df_stock.columns)]
    for _, row in df_stock.iterrows():
        table_data.append([str(item) for item in row.values])
    
    t1 = Table(table_data, colWidths=[85, 155, 120, 90, 100])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(t1)
    story.append(Spacer(1, 25))
    
    # Section 2 : Tableau des mouvements
    story.append(Paragraph("Historique Complet des Mouvements (Entrées / Sorties)", subtitle_style))
    if df_mov.empty:
        story.append(Paragraph("Aucun mouvement enregistré à ce jour.", styles['Normal']))
    else:
        table_mov_data = [list(df_mov.columns)]
        for _, row in df_mov.iterrows():
            table_mov_data.append([str(item) for item in row.values])
        t2 = Table(table_mov_data, colWidths=[65, 65, 55, 55, 120, 90, 100])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(t2)
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- STRUCTURE DES ONGLETS DE L'APPLICATION ---
tab_flux, tab_gestion_articles, tab_rapports = st.tabs([
    "🔄 Flux & Mouvements de Stock", 
    "📦 Référentiel Matériels (Ajouter / Modifier / Supprimer)", 
    "📜 Historique & Téléchargement PDF"
])

# ==========================================
# 1. ENREGISTREMENT DES MOUVEMENTS (ENTRÉES/SORTIES)
# ==========================================
with tab_flux:
    st.subheader("Enregistrer un Mouvement (Entrée ou Sortie de Stock)")
    if st.session_state.articles.empty:
        st.info("Veuillez configurer vos matériels dans l'onglet 'Référentiel Matériels' avant d'effectuer un mouvement.")
    else:
        with st.form("form_nouveau_mouvement", clear_on_submit=True):
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                date_mouv = st.date_input("Date du mouvement", value=datetime.now())
                type_mouv = st.selectbox("Nature du mouvement", options=["Entrée", "Sortie"])
            with col_m2:
                ref_mouv = st.selectbox("Sélectionner le matériel", options=st.session_state.articles["Référence"].tolist())
                quantite_mouv = st.number_input("Quantité / Nombre d'unités", min_value=1, value=1, step=1)
            with col_m3:
                destination = st.text_input("Destination / Secteur de travail", placeholder="Ex: Secteur Est, Sidi Abdellah, Mahelma")
                emplacement = st.text_input("Emplacement physique / Abri", placeholder="Ex: Point d'apport B4, Dépôt principal")
            
            st.markdown("**Affectation Maintenance & Véhicules (Si applicable) :**")
            col_m4, col_m5 = st.columns(2)
            with col_m4:
                camion_mat = st.text_input("Matricule du Camion concerné", placeholder="Ex: 00123-116-16")
            with col_m5:
                piece_details = st.text_input("Détails sur la pièce de rechange", placeholder="Ex: Filtre à air, Batterie, Flexible")
                
            submit_mouv = st.form_submit_button("Valider le mouvement")
            
            if submit_mouv:
                # Vérification de la disponibilité du stock réel avant la sortie
                if type_mouv == "Sortie":
                    reste_dispo = calculer_stock_actuel(ref_mouv)
                    if quantite_mouv > reste_dispo:
                        st.error(f"Action impossible : Stock insuffisant. Il ne reste que {reste_dispo} unité(s) pour la référence {ref_mouv}.")
                        st.stop()
                
                nouveau_mouv = {
                    "Date": date_mouv.strftime("%Y-%m-%d"),
                    "Référence": ref_mouv,
                    "Type": type_mouv,
                    "Quantité": quantite_mouv,
                    "Secteur / Destination": destination if destination else "/",
                    "Emplacement": emplacement if emplacement else "/",
                    "Pièce / Matricule Camion": f"{piece_details} / {camion_mat}" if (piece_details or camion_mat) else "/"
                }
                st.session_state.mouvements = pd.concat([st.session_state.mouvements, pd.DataFrame([nouveau_mouv])], ignore_index=True)
                st.success(f"Mouvement de type [{type_mouv}] enregistré avec succès pour la référence : {ref_mouv}")

# ==========================================
# 2. GESTION COMPLÈTE DU RÉFÉRENTIEL (AJOUTER / MODIFIER / SUPPRIMER)
# ==========================================
with tab_gestion_articles:
    st.subheader("Configuration du catalogue d'articles")
    
    sub_add, sub_edit, sub_del = st.tabs(["➕ Ajouter un Matériel", "✏️ Modifier un Matériel", "❌ Supprimer un Matériel"])
    
    # 2.1. AJOUTER
    with sub_add:
        with st.form("form_creation_article", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                ref = st.text_input("Référence unique * (ex: BAC-660L, SAC-PIECE, FILTRE-HUILE)")
                designation = st.text_input("Désignation complète * (ex: Bac roulant à déchets 660L)")
            with col_a2:
                categorie = st.selectbox("Catégorie de matériel", options=[
                    "Bacs / Conteneurs / Abris", 
                    "Consommables Logistique (Sacs...)", 
                    "Pièces de Rechange Flotte", 
                    "Outillage & Équipements de Sécurité"
                ])
                stock_init = st.number_input("Quantité en stock initial", min_value=0, value=0, step=1)
            
            submit_art = st.form_submit_button("Enregistrer le matériel")
            if submit_art:
                if not ref or not designation:
                    st.error("Les champs 'Référence' et 'Désignation' sont strictement obligatoires.")
                elif ref in st.session_state.articles["Référence"].values:
                    st.error(f"La référence '{ref}' existe déjà dans le système.")
                else:
                    nouvel_art = {"Référence": ref, "Désignation": designation, "Catégorie": categorie, "Stock Initial": stock_init}
                    st.session_state.articles = pd.concat([st.session_state.articles, pd.DataFrame([nouvel_art])], ignore_index=True)
                    st.success(f"Le matériel [{designation}] a bien été intégré au catalogue.")
                    st.rerun()

    # 2.2. MODIFIER
    with sub_edit:
        if st.session_state.articles.empty:
            st.info("Aucun matériel enregistré à modifier.")
        else:
            ref_edit = st.selectbox("Sélectionner la référence à modifier", options=st.session_state.articles["Référence"].tolist(), key="select_edit")
            ligne_art = st.session_state.articles[st.session_state.articles["Référence"] == ref_edit].iloc[0]
            
            with st.form("form_modification_article"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    new_des = st.text_input("Nouvelle Désignation", value=ligne_art["Désignation"])
                with col_e2:
                    new_cat = st.text_input("Modifier la Catégorie", value=ligne_art["Catégorie"])
                    
                if st.form_submit_button("Appliquer les modifications"):
                    idx = st.session_state.articles[st.session_state.articles["Référence"] == ref_edit].index[0]
                    st.session_state.articles.at[idx, "Désignation"] = new_des
                    st.session_state.articles.at[idx, "Catégorie"] = new_cat
                    st.success("Données de l'article mises à jour.")
                    st.rerun()

    # 2.3. SUPPRIMER
    with sub_del:
        if st.session_state.articles.empty:
            st.info("Aucun matériel disponible pour la suppression.")
        else:
            ref_del = st.selectbox("Sélectionner la référence à supprimer", options=st.session_state.articles["Référence"].tolist(), key="select_del")
            st.warning(f"Attention : Supprimer la référence [{ref_del}] effacera également son historique complet de mouvements.")
            
            if st.button("🗑️ Confirmer la suppression définitive", type="primary"):
                st.session_state.articles = st.session_state.articles[st.session_state.articles["Référence"] != ref_del].reset_index(drop=True)
                st.session_state.mouvements = st.session_state.mouvements[st.session_state.mouvements["Référence"] != ref_del].reset_index(drop=True)
                st.success("Matériel supprimé du catalogue.")
                st.rerun()

# ==========================================
# 3. RAPPORTS GLOBAUX, HISTORIQUE ET EXPORT PDF
# ==========================================
with tab_rapports:
    df_global = obtenir_table_stock_global()
    
    st.subheader("📊 Situation Générale des Stocks (Le Reste)")
    if df_global.empty:
        st.info("Le référentiel est vide pour le moment.")
    else:
        # Affichage du tableau principal contenant le Reste calculé automatiquement
        st.dataframe(df_global, use_container_width=True)
        
    st.subheader("📜 Registre Chronologique des Flux")
    if st.session_state.mouvements.empty:
        st.info("Aucun mouvement enregistré dans l'historique.")
    else:
        st.dataframe(st.session_state.mouvements, use_container_width=True)
        
    # Actions de persistance et téléchargement du rapport complet
    st.markdown("---")
    col_save, col_pdf, _ = st.columns([2, 2, 4])
    
    with col_save:
        if st.button("💾 Enregistrer la Session Actuelle", use_container_width=True):
            st.success("Toutes les données courantes (articles et flux logistiques) ont été sécurisées dans la session.")
            
    with col_pdf:
        if not df_global.empty:
            # Génération dynamique du fichier PDF intégrant les deux tableaux
            pdf_flux = generer_pdf(df_global, st.session_state.mouvements)
            st.download_button(
                label="📄 Exporter l'état de stock en PDF",
                data=pdf_flux,
                file_name=f"Rapport_Stocks_Logistique_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

