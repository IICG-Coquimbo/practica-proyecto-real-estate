from scraper_millaray_zalazar1 import scraper1
from scraper_millaray_zalazar2 import scraper2
from scraper_millaray_zalazar3 import scraper3

def extraccion_datos()
    datos_finales = []
    datos1 = scraper1()
    if datos1:
        datos_finales.extend(datos1)
        
    datos2 = scraper2()
    if datos2:
        datos_finales.extend(datos2)

    return datos_finales