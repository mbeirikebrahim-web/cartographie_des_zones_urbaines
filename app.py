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
    layout="wide"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
    }

    h1 {
        margin-bottom: 0.2rem !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #f7f9fc;
    }

    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e6eaf0;
        padding: 14px;
        border-radius: 12px;
    }

    .stAlert {
        border-radius: 12px;
    }

    .custom-card {
        background-color: #ffffff;
        border: 1px solid #e6eaf0;
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 10px;
    }

    .small-text {
        color: #4b5563;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Connexion Earth Engine
# =========================
def initialize_earth_engine():
    """
    Initialise Google Earth Engine.
    - En ligne : utilise les secrets Streamlit
    - En local : essaie l'initialisation classique
    """
    project_id = "projet-mbeirike"
    key_path = None

    try:
        if "EE_PROJECT" in st.secrets and "GCP_SERVICE_ACCOUNT_JSON" in st.secrets:
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
        else:
            ee.Initialize(project=project_id)

        return project_id

    finally:
        if key_path and os.path.exists(key_path):
            os.remove(key_path)


try:
    PROJECT_ID = initialize_earth_engine()
except Exception as e:
    st.error("Erreur de connexion à Google Earth Engine")
    st.code(str(e))
    st.stop()

# =========================
# Titre
# =========================
st.title("Cartographie des zones urbaines")
st.markdown(
    '<p class="small-text">Application web basée sur Google Earth Engine pour estimer les zones urbaines de Rabat.</p>',
    unsafe_allow_html=True
)

# =========================
# Barre latérale
# =========================
st.sidebar.header("Filtres")

zone_etude = st.sidebar.selectbox(
    "Zone d'étude",
    ["Rabat"]
)

annee = st.sidebar.selectbox(
    "Année",
    ["2024", "2023", "2022"]
)

afficher_sentinel = st.sidebar.checkbox("Afficher le fond Sentinel-2", value=True)
afficher_urbain = st.sidebar.checkbox("Afficher les zones urbaines", value=True)

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

# =========================
# Fond Sentinel-2
# =========================
s2 = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(rabat)
    .filterDate(f"{annee}-01-01", f"{annee}-12-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    .median()
    .clip(rabat)
)

s2_vis = {
    "min": 0,
    "max": 3000,
    "bands": ["B4", "B3", "B2"]
}

try:
    s2_map = s2.getMapId(s2_vis)
    s2_tile_url = s2_map["tile_fetcher"].url_format
except Exception as e:
    st.error("Erreur sur le fond Sentinel-2")
    st.code(str(e))
    st.stop()

# =========================
# Zones urbaines
# =========================
dw_built = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterBounds(rabat)
    .filterDate(f"{annee}-01-01", f"{annee}-12-31")
    .select("built")
    .median()
    .clip(rabat)
)

urban_mask = dw_built.gt(0.72).selfMask()
urban_mask = urban_mask.updateMask(
    urban_mask.connectedPixelCount(8, True).gte(6)
)

urban_vis = {
    "palette": ["red"]
}

try:
    urban_map = urban_mask.getMapId(urban_vis)
    urban_tile_url = urban_map["tile_fetcher"].url_format
except Exception as e:
    st.error("Erreur sur la couche des zones urbaines")
    st.code(str(e))
    st.stop()

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
m = folium.Map(
    location=[34.02, -6.84],
    zoom_start=11,
    tiles="OpenStreetMap"
)

if afficher_sentinel:
    folium.raster_layers.TileLayer(
        tiles=s2_tile_url,
        attr="Google Earth Engine",
        name=f"Sentinel-2 {annee}",
        overlay=True,
        control=True,
        opacity=1
    ).add_to(m)

if afficher_urbain:
    folium.raster_layers.TileLayer(
        tiles=urban_tile_url,
        attr="Google Earth Engine",
        name="Zones urbaines",
        overlay=True,
        control=True,
        opacity=0.7
    ).add_to(m)

folium.LayerControl().add_to(m)

# =========================
# Bloc résumé
# =========================
st.info(f"Zone sélectionnée : {zone_etude} | Année : {annee}")

col1, col2 = st.columns([1, 2])

with col1:
    st.metric("Surface urbaine estimée", f"{urban_area_ha_value:,.2f} ha")

with col2:
    st.markdown(
        """
<div class="custom-card">
<b>Méthode</b><br><br>
- Limite de travail : <b>FAO/GAUL/2015/level2</b> (donnée publique)<br>
- Fond d’image : <b>Sentinel-2 SR Harmonized</b><br>
- Zones urbaines : <b>Dynamic World V1</b>, bande <b>built</b><br>
- Seuil appliqué : <b>0.72</b><br>
- Filtrage spatial : suppression des petits objets isolés
</div>
        """,
        unsafe_allow_html=True
    )

# =========================
# Carte
# =========================
st.subheader("Carte Google Earth Engine")
st_folium(m, width=1200, height=650)

# =========================
# Légende
# =========================
st.markdown("### Légende")
st.markdown(
    """
<div style="display: flex; gap: 30px; align-items: center; flex-wrap: wrap;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <div style="width: 20px; height: 20px; background-color: red; border-radius: 4px;"></div>
        <span>Zones urbaines estimées</span>
    </div>
</div>
""",
    unsafe_allow_html=True
)

# =========================
# Remarque méthodologique
# =========================
with st.expander("Remarque importante"):
    st.write(
        "La surface urbaine affichée est une estimation obtenue dans Google Earth Engine "
        "à partir de la probabilité 'built' de Dynamic World. "
        "Elle dépend du dataset choisi, du seuil appliqué et du filtrage spatial utilisé. "
        "Ce n’est pas une valeur cadastrale officielle."
    )