import streamlit as st
import ee
import folium
from streamlit_folium import st_folium

PROJECT_ID = "projet-mbeirike"

st.set_page_config(page_title="Cartographie des zones urbaines", layout="wide")

st.title("Cartographie des zones urbaines")
st.write("Application basée sur Google Earth Engine pour l’estimation des zones urbaines de Rabat.")

# =========================
# Connexion Earth Engine
# =========================
try:
    ee.Initialize(project=PROJECT_ID)
    st.success("Google Earth Engine connecté avec succès.")
except Exception as e:
    st.error("Erreur de connexion à Google Earth Engine")
    st.code(str(e))
    st.stop()

# =========================
# Barre latérale
# =========================
st.sidebar.header("Paramètres")

zone_etude = st.sidebar.selectbox(
    "Choisir la zone d'étude",
    ["Rabat"]
)

annee = st.sidebar.selectbox(
    "Choisir l'année",
    ["2024", "2023", "2022"]
)

afficher_sentinel = st.sidebar.checkbox("Afficher le fond Sentinel-2", value=True)
afficher_urbain = st.sidebar.checkbox("Afficher les zones urbaines", value=True)
afficher_limite = st.sidebar.checkbox("Afficher la limite administrative", value=True)

st.info(f"Zone sélectionnée : {zone_etude} | Année : {annee}")

# =========================
# Zone d'étude : Rabat
# =========================
rabat_fc = ee.FeatureCollection(
    "projects/projet-mbeirike/assets/rabat_boundary_asset"
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

s2_map = ee.Image(s2).getMapId(s2_vis)
s2_tile_url = s2_map["tile_fetcher"].url_format

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

# Réglage retenu
urban_mask = dw_built.gt(0.72).selfMask()
urban_mask = urban_mask.updateMask(
    urban_mask.connectedPixelCount(8, True).gte(6)
)

urban_vis = {
    "palette": ["red"]
}

urban_map = ee.Image(urban_mask).getMapId(urban_vis)
urban_tile_url = urban_map["tile_fetcher"].url_format

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

# =========================
# Limite administrative
# =========================
boundary_image = ee.Image().byte().paint(
    featureCollection=rabat_fc,
    color=1,
    width=3
)

boundary_map = boundary_image.getMapId({"palette": ["yellow"]})
boundary_tile_url = boundary_map["tile_fetcher"].url_format

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

if afficher_limite:
    folium.raster_layers.TileLayer(
        tiles=boundary_tile_url,
        attr="Google Earth Engine",
        name="Limite Rabat",
        overlay=True,
        control=True,
        opacity=1
    ).add_to(m)

folium.LayerControl().add_to(m)

# =========================
# Affichage principal
# =========================
col1, col2 = st.columns([1, 2])

with col2:
    st.markdown(
        """
**Méthode**
- Limite administrative : asset personnel GEE (`rabat_boundary_asset`)
- Fond d’image : Sentinel-2 SR Harmonized
- Zones urbaines : Dynamic World V1, bande **built**
- Seuil appliqué : **0.72**
- Filtrage spatial : suppression des petits objets isolés
        """
    )
st.subheader("Carte Google Earth Engine")
st_folium(m, width=1200, height=600)

# =========================
# Légende
# =========================
st.markdown("### Légende")
st.markdown(
    """
<div style="display: flex; gap: 30px; align-items: center; flex-wrap: wrap;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <div style="width: 20px; height: 20px; background-color: red;"></div>
        <span>Zones urbaines estimées</span>
    </div>
    <div style="display: flex; align-items: center; gap: 8px;">
        <div style="width: 20px; height: 20px; background-color: yellow; border: 1px solid black;"></div>
        <span>Limite administrative de Rabat</span>
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
        "Elle dépend du seuil appliqué et du filtrage spatial choisi. "
        "Ce n’est pas une valeur cadastrale officielle."
    )