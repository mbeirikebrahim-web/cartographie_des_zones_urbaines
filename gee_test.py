import ee

PROJECT_ID = "projet-mbeirike"

ee.Authenticate(force=True)
ee.Initialize(project=PROJECT_ID)

print(ee.String("Connexion Earth Engine OK").getInfo())