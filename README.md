# Cartographie des zones urbaines

## Description
Cette application a été développée avec **Python**, **Streamlit** et **Google Earth Engine** pour cartographier les zones urbaines de **Rabat**.

## Objectif
L’objectif est de :
- visualiser un fond d’image Sentinel-2,
- extraire les zones urbaines,
- afficher la limite administrative de Rabat,
- estimer la surface urbaine.

## Données utilisées
- **Google Earth Engine**
- **Sentinel-2 SR Harmonized**
- **Dynamic World V1**
- **Asset personnel importé dans Google Earth Engine Assets** : `rabat_boundary_asset`

## Méthode
Les zones urbaines sont estimées à partir de la probabilité **built** de Dynamic World.  
Un seuil de **0.72** a été appliqué, avec un filtrage spatial pour supprimer les petits objets isolés.

## Bibliothèques utilisées
- streamlit
- earthengine-api
- folium
- streamlit-folium

## Lancer le projet

### 1. Activer l’environnement virtuel
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Lancer l’application
```powershell
streamlit run app.py
```

## Remarque
La surface urbaine affichée est une **estimation** obtenue dans Google Earth Engine.  
Elle dépend du dataset choisi, du seuil appliqué et du filtrage utilisé.  
Ce n’est pas une valeur cadastrale officielle.