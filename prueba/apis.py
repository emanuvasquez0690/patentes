import requests
import json
import time

BASE_URL = "https://api.us.socrata.com/api/catalog/v1"
DOMAIN = "datos.gov.co"

def obtener_datasets(limit=500):
    datasets = []
    offset = 0

    while True:
        url = f"{BASE_URL}?domains={DOMAIN}&limit={limit}&offset={offset}"
        print(f"Consultando: {url}")
        
        response = requests.get(url)
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            break

        for item in results:
            resource = item.get("resource", {})
            classification = item.get("classification", {})
            
            dataset_id = resource.get("id")
            nombre = resource.get("name")
            descripcion = resource.get("description")
            columnas = resource.get("columns_name", [])
            tipos_columnas = resource.get("columns_datatype", [])
            actualizado = resource.get("updatedAt")
            creado = resource.get("createdAt")
            tags = classification.get("tags", [])

            api_url = f"https://www.datos.gov.co/resource/{dataset_id}.json" if dataset_id else None

            datasets.append({
                "id": dataset_id,
                "nombre": nombre,
                "descripcion": descripcion,
                "columnas": columnas,
                "tipos_columnas": tipos_columnas,
                "tags": tags,
                "fecha_creacion": creado,
                "ultima_actualizacion": actualizado,
                "api_url": api_url
            })

        offset += limit
        time.sleep(0.2)  # evitar rate limits

    return datasets


def guardar_json(data, filename="datasets.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Archivo guardado en: {filename}")


if __name__ == "__main__":
    datasets = obtener_datasets()
    guardar_json(datasets)
