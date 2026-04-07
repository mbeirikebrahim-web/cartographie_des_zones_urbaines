import json
import os
import tempfile

import ee
import folium
import streamlit as st
from streamlit_folium import st_folium

# =========================
# Configuration de la page
# =========================
st.set_page_config(
    page_title="Cartographie des zones urbaines",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1600px;
    }

    header[data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0);
    }

    section[data-testid="stSidebar"] {
        display: none;
    }

    .hero-box {
        background: linear-gradient(135deg, #ffffff 0%, #f5f9ff 100%);
        border: 1px solid #e6eaf0;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
    }

    .hero-title {
        font-size: 2.35rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.35rem;
    }

    .hero-subtitle {
        color: #475569;
        font-size: 1rem;
        margin-bottom: 0.9rem;
        line-height: 1.6;
    }

    .badge-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .badge-item {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: #eef4ff;
        border: 1px solid #dbe7ff;
        color: #1d4ed8;
        font-size: 0.88rem;
        font-weight: 600;
    }

    .top-card {
        background-color: #ffffff;
        border: 1px solid #e6eaf0;
        padding: 18px;
        border-radius: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 8px rgba(15, 23, 42, 0.04);
    }

    .top-label {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 6px;
    }

    .top-value {
        color: #1f2937;
        font-size: 1.35rem;
        font-weight: 700;
    }

    .custom-card {
        background-color: #ffffff;
        border: 1px solid #e6eaf0;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 8px rgba(15, 23, 42, 0.04);
    }

    .panel-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 10px;
        color: #1f2937;
    }

    .panel-line {
        margin-bottom: 8px;
        color: #374151;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }

    .legend-red {
        width: 18px;
        height: 18px;
        background-color: red;
        border-radius: 4px;
        border: 1px solid #d1d5db;
    }

    .legend-blue {
        width: 18px;
        height: 18px;
        background-color: #2563eb;
        border-radius: 4px;
        border: 1px solid #d1d5db;
    }

    .map-title {
        font-size: 1.18rem;
        font-weight: 800;
        margin-bottom: 0.65rem;
        color: #0f172a;
    }

    .filter-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.25rem;
    }

    .filter-subtitle {
        color: #64748b;
        font-size: 0.94rem;
        margin-bottom: 1rem;
        line-height: 1.5;
    }

    .footer-note {
        color: #64748b;
        text-align: center;
        font-size: 0.9rem;
        margin-top: 0.8rem;
    }

    div[data-testid="stSelectbox"] > label,
    div[data-testid="stCheckbox"] > label {
        font-weight: 600;
        color: #334155;
    }

    div[data-baseweb="select"] > div {
        border-radius: 14px !important;
        border: 1px solid #e5e7eb !important;
        min-height: 48px !important;
        box-shadow: none !important;
    }

    div[data-testid="stCheckbox"] {
        margin-bottom: 0.2rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 20px !important;
        border: 1px solid #e6eaf0 !important;
        background: #ffffff !important;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05) !important;
        padding: 0.3rem 0.2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Connexion Earth Engine
# =========================
def initialize_earth_engine():
    """
    Priorité :
    1. Fichier local .streamlit/service_account.json
    2. Secrets Streamlit
    3. Initialisation locale classique
    """
    project_id = "projet-mbeirike"
    key_path = None

    try:
        local_key_path = os.path.join(".streamlit", "service_account.json")

        if os.path.exists(local_key_path):
            with open(local_key_path, "r", encoding="utf-8") as f:
                service_account_info = json.load(f)

            service_account_email = service_account_info["client_email"]
            project_id = service_account_info.get("project_id", project_id)

            credentials = ee.ServiceAccountCredentials(
                service_account_email,
                local_key_path
            )
            ee.Initialize(credentials=credentials, project=project_id)
            return project_id

        secrets_available = True
        try:
            _ = st.secrets
        except Exception:
            secrets_available = False

        if secrets_available and "EE_PROJECT" in st.secrets and "GCP_SERVICE_ACCOUNT_JSON" in st.secrets:
            project_id = st.secrets["EE_PROJECT"]
            service_account_json = st.secrets["GCP_SERVICE_ACCOUNT_JSON"]

            service_account_info = json.loads(service_account_json)
            service_account_email = service_account_info["client_email"]

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                encoding="utf-8"
            ) as tmp:
                tmp.write(service_account_json)
                key_path = tmp.name

            credentials = ee.ServiceAccountCredentials(service_account_email, key_path)
            ee.Initialize(credentials=credentials, project=project_id)
            return project_id

        ee.Initialize(project=project_id)
        return project_id

    finally:
        if key_path and os.path.exists(key_path):
            os.remove(key_path)


def add_ee_tile(map_obj, image, vis_params, layer_name, opacity=1.0):
    map_id = ee.Image(image).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=layer_name,
        overlay=True,
        control=True,
        opacity=opacity
    ).add_to(map_obj)


try:
    PROJECT_ID = initialize_earth_engine()
except Exception as e:
    st.error("Erreur de connexion à Google Earth Engine")
    st.code(str(e))
    st.stop()

# =========================
# Mise en page principale
# =========================
left_col, right_col = st.columns([1.0, 2.6], gap="large")   

with left_col:
    with st.container(border=True):
        st.markdown('<div class="filter-title">Filtres</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="filter-subtitle">Personnalise l’affichage de la carte et des couches urbaines.</div>',
            unsafe_allow_html=True
        )

        zone_etude = st.selectbox(
            "Zone d'étude",
            ["Rabat"]
        )

        annee = st.selectbox(
            "Année",
            ["2024", "2023", "2022"],
            index=0
        )

        fond_carte = st.selectbox(
            "Fond de carte",
            ["OpenStreetMap", "Satellite"],
            index=1
        )

        st.markdown("")

        afficher_sentinel = st.checkbox("Afficher le fond Sentinel-2", value=True)
        afficher_urbain = st.checkbox("Afficher les zones urbaines", value=True)
        afficher_limite = st.checkbox("Afficher la limite de la zone d'étude", value=True)

with right_col:
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">Cartographie des zones urbaines</div>
        <div class="hero-subtitle">
            Application web basée sur Google Earth Engine pour estimer les zones urbaines de Rabat
            et les visualiser dans une interface plus propre, plus claire et plus attractive.
        </div>
        <div class="badge-wrap">
            <span class="badge-item">Streamlit</span>
            <span class="badge-item">Google Earth Engine</span>
            <span class="badge-item">Sentinel-2</span>
            <span class="badge-item">Dynamic World</span>
            <span class="badge-item">Rabat</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Zone d'étude : Rabat
# =========================
gaul2 = ee.FeatureCollection("FAO/GAUL/2015/level2")

rabat_fc = (
    gaul2
    .filter(ee.Filter.eq("ADM0_NAME", "Morocco"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rabat"))
)

rabat = rabat_fc.geometry()

boundary = ee.Image().byte().paint(rabat_fc, 1, 3)
boundary_vis = {"palette": ["#2563eb"]}

# =========================
# Dates
# =========================
annee_int = int(annee)
date_debut = f"{annee_int}-01-01"
date_fin = f"{annee_int + 1}-01-01"

# =========================
# Fond Sentinel-2
# =========================
s2 = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(rabat)
    .filterDate(date_debut, date_fin)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    .median()
    .clip(rabat)
)

s2_vis = {
    "min": 0,
    "max": 3000,
    "bands": ["B4", "B3", "B2"]
}

# =========================
# Zones urbaines
# =========================
dw_built = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterBounds(rabat)
    .filterDate(date_debut, date_fin)
    .select("built")
    .median()
    .clip(rabat)
)

urban_mask = dw_built.gt(0.72).selfMask()
urban_mask = urban_mask.updateMask(
    urban_mask.connectedPixelCount(100, True).gte(6)
)

# =========================
# Surface urbaine estimée
# =========================
urban_area_m2 = urban_mask.multiply(ee.Image.pixelArea()).reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=rabat,
    scale=10,
    maxPixels=1e10
).getNumber("built")

urban_area_ha = ee.Number(urban_area_m2).divide(10000)
urban_area_ha_value = urban_area_ha.getInfo()

if urban_area_ha_value is None:
    urban_area_ha_value = 0.0

# =========================
# Carte Folium
# =========================
centroid = rabat.centroid(1).coordinates().getInfo()
center_lon, center_lat = centroid[0], centroid[1]

if fond_carte == "Satellite":
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles=None,
        control_scale=True
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)
else:
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="OpenStreetMap",
        control_scale=True
    )

try:
    if afficher_sentinel:
        add_ee_tile(m, s2, s2_vis, f"Sentinel-2 {annee}", opacity=1)

    if afficher_urbain:
        add_ee_tile(
            m,
            urban_mask,
            {"palette": ["red"]},
            "Zones urbaines estimées",
            opacity=0.72
        )

    if afficher_limite:
        add_ee_tile(
            m,
            boundary,
            boundary_vis,
            "Limite de la zone d'étude",
            opacity=1
        )
except Exception as e:
    st.error("Erreur lors de l'affichage des couches cartographiques")
    st.code(str(e))
    st.stop()

folium.LayerControl(collapsed=True).add_to(m)

# =========================
# Contenu principal à droite
# =========================
with right_col:
    top1, top2, top3 = st.columns(3)

    with top1:
        st.markdown(
            f"""
        <div class="top-card">
            <div class="top-label">Zone</div>
            <div class="top-value">{zone_etude}</div>
        </div>
            """,
            unsafe_allow_html=True
        )

    with top2:
        st.markdown(
            f"""
        <div class="top-card">
            <div class="top-label">Année</div>
            <div class="top-value">{annee}</div>
        </div>
            """,
            unsafe_allow_html=True
        )

    with top3:
        st.markdown(
            f"""
        <div class="top-card">
            <div class="top-label">Surface urbaine estimée</div>
            <div class="top-value">{urban_area_ha_value:,.2f} ha</div>
        </div>
            """,
            unsafe_allow_html=True
        )

    col_map, col_right_info = st.columns([2.1, 0.9], gap="large")

    with col_map:
        st.markdown('<div class="map-title">Carte des zones urbaines détectées</div>', unsafe_allow_html=True)
        st_folium(m, use_container_width=True, height=780)

    with col_right_info:
        st.markdown(
            """
        <div class="custom-card">
            <div class="panel-title">Méthode</div>
            <div class="panel-line"><b>Limite :</b> FAO/GAUL/2015/level2</div>
            <div class="panel-line"><b>Image :</b> Sentinel-2 SR Harmonized</div>
            <div class="panel-line"><b>Détection :</b> Dynamic World V1, bande <b>built</b></div>
            <div class="panel-line"><b>Seuil :</b> 0.72</div>
            <div class="panel-line"><b>Filtrage :</b> petits objets isolés supprimés</div>
        </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
        <div class="custom-card">
            <div class="panel-title">Légende</div>
            <div class="legend-item">
                <div class="legend-red"></div>
                <div>Zones urbaines estimées</div>
            </div>
            <div class="legend-item">
                <div class="legend-blue"></div>
                <div>Limite de la zone d’étude</div>
            </div>
        </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
        <div class="custom-card">
            <div class="panel-title">Lecture rapide</div>
            <div class="panel-line"><b>Zone :</b> {zone_etude}</div>
            <div class="panel-line"><b>Année :</b> {annee}</div>
            <div class="panel-line"><b>Surface :</b> {urban_area_ha_value:,.2f} ha</div>
            <div class="panel-line"><b>Interprétation :</b> estimation des zones bâties détectées</div>
        </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
        <div class="custom-card">
            <div class="panel-title">Limites</div>
            <div class="panel-line">Résultat estimatif</div>
            <div class="panel-line">Dépend du seuil et du filtrage spatial</div>
            <div class="panel-line">Ce n’est pas une donnée cadastrale officielle</div>
        </div>
            """,
            unsafe_allow_html=True
        )

    with st.expander("Remarque importante", expanded=False):
        st.write(
            "La surface urbaine affichée est une estimation obtenue dans Google Earth Engine "
            "à partir de la probabilité 'built' de Dynamic World. "
            "Elle dépend du dataset choisi, du seuil appliqué et du filtrage spatial utilisé. "
            "Ce n’est pas une valeur cadastrale officielle."
        )

    st.markdown(
        '<div class="footer-note">Application démonstrative de cartographie urbaine avec Streamlit et Google Earth Engine.</div>',
        unsafe_allow_html=True
    )