from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from pymongo.mongo_client import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from passlib.context import CryptContext
from pymongo import ReturnDocument


MONGO_DETAILS = "mongodb+srv://Onstrax:Bellezo17@ahorrapp.qgqpw.mongodb.net/?retryWrites=true&w=majority&appName=AhorrApp"

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.AhorrAppDB
#collection = database.get_collection("usuarios")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Autenticación de Google Sheets
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# credentials_json = os.getenv("GOOGLE_CREDENTIALS")
# credentials_info = json.loads(credentials_json)
# creds = Credentials.from_service_account_info(credentials_info, scopes=scope)
# client = gspread.authorize(creds)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "https://ahorrapp.netlify.app"],  # Permitir ambas URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    username: str
    password: str
    whatsapp: str

class GastoOcasional(BaseModel):
    username: str
    esNecesidad: bool
    categoria: str
    producto: str
    fecha: str
    metodoPago: str
    monto: float
    
class GastoFijo(BaseModel):
    username: str
    esNecesidad: bool
    categoria: str
    producto: str
    periodo: str
    fecha: str
    metodoPago: str
    monto: float

@app.post("/register")
async def register(user: User):
    # Verificar si el usuario ya existe en la colección de usuarios
    existing_user = await database["usuarios"].find_one({"username": user.username})
    if existing_user:
        return False
    
    hashed_password = pwd_context.hash(user.password)
    # Insertar nuevo usuario en la colección de usuarios
    new_user = {
        "username": user.username,
        "password": hashed_password,
        "whatsapp": user.whatsapp
    }
    await database["usuarios"].insert_one(new_user)
    
    # Insertar preferencias predeterminadas en la colección de preferencias
    new_preferences = {
        "username": user.username,
        "periodos": ["Anual", "Mensual", "Semanal", "Diario"],
        "categorias_fijas": ["Agua", "Alquiler", "Comida", "Cuenta/Subscripción", "Dentales", "Gas", "Higiene", "Luz", "Mascota", "Ocio", "Productos del Hogar", "Salud", "Teléfono", "Transporte"],
        "categorias_ocasionales": ["Productos del Hogar", "Comida", "Salud", "Higiene", "Cuenta/Subscripción", "Transporte", "Ocio", "Educación", "Mascota", "Materiales dentales"],
        "metodos_pago": ["Bancolombia", "Crédito", "Daviplata", "Débito", "Efectivo", "Nequi", "Transfiya"]
    }
    await database["preferencias"].insert_one(new_preferences)

    return True

# @app.post("/register")
# def register(user: User):
#     sheet_usuarios = client.open("AhorrappDB").worksheet("Usuarios")  # Hoja de usuarios
#     users = sheet_usuarios.get_all_records()
#     for record in users:
#         if record['username'] == user.username:
#             return False
#     sheet_usuarios.append_row([user.username, user.password, user.whatsapp])
    
#     sheet_preferencias = client.open("AhorrappDB").worksheet("Preferencias")
#     sheet_preferencias.append_row([user.username, 
#                                    "Anual,Diario,Mensual,Semanal",
#                                    "Agua,Alquiler,Celular,Comida,Cuenta/Subscripción,Gas,Higiene,Internet,Luz,Mascota,Productos del Hogar,Salud,Transporte",
#                                    "Comida,Cuenta/Subscripción,Educación,Higiene,Mascota,Ocio,Productos del Hogar,Salud,Transporte",
#                                    "Crédito,Daviplata,Débito,Efectivo,Nequi,Transfiya"])
#     return True

@app.post("/login")
async def login(user: User):
    # Buscar el usuario en la colección de MongoDB por su nombre de usuario
    existing_user = await database["usuarios"].find_one({"username": user.username})
    
    # Si el usuario no existe
    if not existing_user:
        return False
    
    # Verificar la contraseña usando bcrypt
    if not pwd_context.verify(user.password, existing_user["password"]):
        return False
    
    # Si la contraseña es correcta, devolver un mensaje de éxito
    return True

# @app.post("/login")
# def login(user: User):
#     sheet_usuarios = client.open("AhorrappDB").worksheet("Usuarios")  # Hoja de usuarios
#     users = sheet_usuarios.get_all_records()
#     for record in users:
#         if str(record['username']) == user.username and str(record['password']) == user.password:
#             return True
#     return False
    # raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

# def get_date_filter(period: str):
#     today = datetime.now()
#     if period == "hoy":
#         return today.strftime("%Y-%m-%d")
#     elif period == "esta_semana":
#         return (today - timedelta(days=7)).strftime("%Y-%m-%d")
#     elif period == "este_mes":
#         return (today - timedelta(days=30)).strftime("%Y-%m-%d")
#     elif period == "este_anio":
#         return (today - timedelta(days=365)).strftime("%Y-%m-%d")
#     return None

@app.get("/gastos")
async def obtener_gastos_del_periodo(username: str, desde: str, hasta: str):
    # Consultar gastos fijos del usuario en el rango de fechas (comparando cadenas)
    gastos_fijos = await database["gastos_fijos"].aggregate([
        {"$match": {"username": username}},
        {"$unwind": "$gastos"},
        {"$match": {
            "$and": [
                {"gastos.fecha": {"$gte": desde}},
                {"gastos.fecha": {"$lte": hasta}}
            ]
        }},
        {"$replaceRoot": {"newRoot": "$gastos"}}
    ]).to_list(None)
    
    # Consultar gastos ocasionales del usuario en el rango de fechas (comparando cadenas)
    gastos_ocasionales = await database["gastos_ocasionales"].aggregate([
        {"$match": {"username": username}},
        {"$unwind": "$gastos"},
        {"$match": {
            "$and": [
                {"gastos.fecha": {"$gte": desde}},
                {"gastos.fecha": {"$lte": hasta}}
            ]
        }},
        {"$replaceRoot": {"newRoot": "$gastos"}}
    ]).to_list(None)

    # Unir los dos tipos de gastos
    todos_los_gastos = gastos_fijos + gastos_ocasionales

    # Calcular el total acumulado
    total_acumulado = sum(gasto["monto"] for gasto in todos_los_gastos)

    return {"gastos": todos_los_gastos, "total": total_acumulado}

# @app.get("/gastos")
# def obtener_gastos_del_periodo(username: str, desde: str, hasta:str):
#     sheet_gastos_fijos = client.open("AhorrappDB").worksheet("Gastos_fijos")
#     sheet_gastos_ocasionales = client.open("AhorrappDB").worksheet("Gastos_ocasionales")

#     # Filtrar gastos fijos y ocasionales según la fecha
#     gastos_fijos = sheet_gastos_fijos.get_all_records()
#     gastos_ocasionales = sheet_gastos_ocasionales.get_all_records()

#     # Filtrar por fecha y usuario
#     gastos_filtrados_fijos = [gasto for gasto in gastos_fijos if gasto['username'] == username and gasto['fecha'] >= desde and gasto['fecha'] <= hasta]
#     gastos_filtrados_ocasionales = [gasto for gasto in gastos_ocasionales if gasto['username'] == username and gasto['fecha'] >= desde and gasto['fecha'] <= hasta]

#     # Unir los dos tipos de gastos
#     todos_los_gastos = gastos_filtrados_fijos + gastos_filtrados_ocasionales
#     total_acumulado = sum(gasto['monto'] for gasto in todos_los_gastos)

#     return {"gastos": todos_los_gastos, "total": total_acumulado}

@app.get("/gastos-list")
async def obtener_gastos_del_usuario(username: str):
    # Consultar gastos fijos del usuario en MongoDB
    gastos_fijos = await database["gastos_fijos"].aggregate([
        {"$match": {"username": username}},
        {"$unwind": "$gastos"},
        {"$replaceRoot": {"newRoot": "$gastos"}}
    ]).to_list(None)
    
    # Consultar gastos ocasionales del usuario en MongoDB
    gastos_ocasionales = await database["gastos_ocasionales"].aggregate([
        {"$match": {"username": username}},
        {"$unwind": "$gastos"},
        {"$replaceRoot": {"newRoot": "$gastos"}}
    ]).to_list(None)

    # Ordenar los gastos fijos por fecha, de más reciente a más antiguo
    gastos_filtrados_fijos = sorted(
        gastos_fijos,
        key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'),
        reverse=True
    )

    # Ordenar los gastos ocasionales por fecha, de más reciente a más antiguo
    gastos_filtrados_ocasionales = sorted(
        gastos_ocasionales,
        key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'),
        reverse=True
    )

    # Convertir 'esNecesidad' de boolean a True/False (si es necesario)
    for gasto in gastos_filtrados_fijos:
        gasto['esNecesidad'] = bool(gasto['esNecesidad'])

    for gasto in gastos_filtrados_ocasionales:
        gasto['esNecesidad'] = bool(gasto['esNecesidad'])

    return {"fijos": gastos_filtrados_fijos, "ocasionales": gastos_filtrados_ocasionales}

# @app.get("/gastos-list")
# def obtener_gastos_del_usuario(username: str):
#     sheet_gastos_fijos = client.open("AhorrappDB").worksheet("Gastos_fijos")
#     sheet_gastos_ocasionales = client.open("AhorrappDB").worksheet("Gastos_ocasionales")

#     # Filtrar gastos fijos y ocasionales según la fecha
#     gastos_fijos = sheet_gastos_fijos.get_all_records()
#     gastos_ocasionales = sheet_gastos_ocasionales.get_all_records()

#     # Filtrar por usuario
#     gastos_filtrados_fijos = sorted(
#     [gasto for gasto in gastos_fijos if gasto['username'] == username],
#     key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'),
#     reverse=True
# )
#     gastos_filtrados_ocasionales = sorted(
#     [gasto for gasto in gastos_ocasionales if gasto['username'] == username],
#     key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'),
#     reverse=True
# )
#     for gasto in gastos_filtrados_fijos:
#         gasto['esNecesidad'] = gasto['esNecesidad'].upper() == 'TRUE'

#     for gasto in gastos_filtrados_ocasionales:
#         gasto['esNecesidad'] = gasto['esNecesidad'].upper() == 'TRUE'

#     return {"fijos": gastos_filtrados_fijos, "ocasionales": gastos_filtrados_ocasionales}

@app.get("/{preferencia}")
async def obtener_preferencias(username: str, preferencia: str):
    # Buscar el documento de preferencias del usuario en la colección "preferencias"
    user_preferencias = await database["preferencias"].find_one({"username": username})
    
    # Si no se encuentra el usuario, devolver un error
    if not user_preferencias:
        return {"error": "Usuario no encontrado"}

    # Verificar si la preferencia solicitada existe en el documento
    if preferencia in user_preferencias:
        return user_preferencias[preferencia]

    # Si la preferencia solicitada no existe, devolver un error
    return {"error": "Preferencia no encontrada"}

# @app.get("/{preferencia}")
# def obtener_preferencias(username: str, preferencia: str):
#     sheet = client.open("AhorrappDB").worksheet("Preferencias")
#     filas = sheet.get_all_records()
#     for fila in filas:
#         if fila['username'] == username:
#             preferencias = fila[preferencia].split(',')
#             return preferencias

#     return {"error": "Usuario no encontrado"}

@app.post("/gastos/ocasionales")
async def agregar_gasto_ocasional(gasto: GastoOcasional):
    try:
        # Preparar el nuevo gasto como un diccionario
        nuevo_gasto = {
            "esNecesidad": gasto.esNecesidad,
            "categoria": gasto.categoria,
            "producto": gasto.producto,
            "fecha": gasto.fecha,  # Asegúrate de que la fecha esté en formato correcto (ISODate en MongoDB)
            "metodoPago": gasto.metodoPago,
            "monto": gasto.monto
        }

        # Buscar el documento del usuario por el nombre de usuario
        result = await database["gastos_ocasionales"].find_one({"username": gasto.username})

        # Si el usuario ya tiene un registro de gastos fijos, añadir el nuevo gasto
        if result:
            await database["gastos_ocasionales"].update_one(
                {"username": gasto.username},
                {"$push": {"gastos": nuevo_gasto}}  # Añadir el nuevo gasto al array de gastos
            )
        else:
            # Si el usuario no tiene un registro de gastos fijos, crear uno nuevo
            nuevo_documento = {
                "username": gasto.username,
                "gastos": [nuevo_gasto]  # Crear el array con el primer gasto
            }
            await database["gastos_ocasionales"].insert_one(nuevo_documento)

        return True
    except Exception as e:
        return False

# @app.post("/gastos/ocasionales")
# def agregar_gasto_ocasional(gasto: GastoOcasional):
#     try:
#         sheet_gastos_ocasionales = client.open("AhorrappDB").worksheet("Gastos_ocasionales")  # Hoja de gastos ocasionales
#         sheet_gastos_ocasionales.append_row([gasto.username, gasto.esNecesidad, gasto.categoria, gasto.producto, gasto.fecha, gasto.metodoPago, gasto.monto])
#         return True
#     except:
#         return False

@app.post("/gastos/fijos")
async def agregar_gasto_fijo(gasto: GastoFijo):
    try:
        # Preparar el nuevo gasto como un diccionario
        nuevo_gasto = {
            "esNecesidad": gasto.esNecesidad,
            "categoria": gasto.categoria,
            "producto": gasto.producto,
            "periodo": gasto.periodo,
            "fecha": gasto.fecha,  # Asegúrate de que la fecha esté en formato correcto (ISODate en MongoDB)
            "metodoPago": gasto.metodoPago,
            "monto": gasto.monto
        }

        # Buscar el documento del usuario por el nombre de usuario
        result = await database["gastos_fijos"].find_one({"username": gasto.username})

        # Si el usuario ya tiene un registro de gastos fijos, añadir el nuevo gasto
        if result:
            await database["gastos_fijos"].update_one(
                {"username": gasto.username},
                {"$push": {"gastos": nuevo_gasto}}  # Añadir el nuevo gasto al array de gastos
            )
        else:
            # Si el usuario no tiene un registro de gastos fijos, crear uno nuevo
            nuevo_documento = {
                "username": gasto.username,
                "gastos": [nuevo_gasto]  # Crear el array con el primer gasto
            }
            await database["gastos_fijos"].insert_one(nuevo_documento)

        return True
    except Exception as e:
        return False

# @app.post("/gastos/fijos")
# def agregar_gasto_fijo(gasto: GastoFijo):
#     try:
#         sheet_gastos_fijos = client.open("AhorrappDB").worksheet("Gastos_fijos")  # Hoja de gastos fijos
#         sheet_gastos_fijos.append_row([gasto.username, gasto.esNecesidad, gasto.categoria, gasto.producto, gasto.periodo, gasto.fecha, gasto.metodoPago, gasto.monto])
#         return True
#     except:
#         return False
  
@app.put("/agregar_preferencia")
async def agregar_preferencia(username: str, preferencia: str, valor: str):
    # Buscar el documento del usuario por el nombre de usuario
    user_preferencias = await database["preferencias"].find_one({"username": username})

    # Verificar si el usuario existe
    if not user_preferencias:
        return "error"

    # Verificar si la preferencia solicitada existe en el documento
    if preferencia not in user_preferencias:
        return "error"

    # Obtener los valores actuales de la preferencia
    valores_actuales = user_preferencias[preferencia]

    # Verificar si el valor ya existe en la lista de preferencias
    if valor in valores_actuales:
        return "existing"

    # Agregar el nuevo valor y ordenar la lista
    valores_actuales.append(valor)
    valores_actuales.sort()

    # Actualizar el documento en MongoDB
    await database["preferencias"].update_one(
        {"username": username},
        {"$set": {preferencia: valores_actuales}}
    )

    return "success"
    
# @app.put("/agregar_preferencia")
# def agregar_preferencia(username: str, preferencia: str, valor: str):
#     #abrir la hoja correspondiente
#     sheet = client.open("AhorrappDB").worksheet("Preferencias")
#     filas = sheet.get_all_records()

#     # Encontrar la fila correspondiente al usuario
#     for idx, fila in enumerate(filas):
#         if fila['username'] == username:
#             # Obtener la preferencia correspondiente
#             valores_actuales = fila[preferencia].split(',') if fila[preferencia] else []
            
#             # Verificar si el nuevo valor ya existe
#             if valor in valores_actuales:
#                 return "existing"

#             # Agregar el nuevo valor a la lista
#             valores_actuales.append(valor)
#             valores_actuales.sort()
            
#             # Actualizar la hoja de cálculo con los nuevos valores
#             nuevos_valores = ','.join(valores_actuales)
#             sheet.update_cell(idx + 2, sheet.find(preferencia).col, nuevos_valores)
            
#             return "success"

#     return "error"

@app.put("/eliminar_preferencia")
async def eliminar_preferencia(username: str, preferencia: str, valor: str):
    # Buscar el documento del usuario por el nombre de usuario
    user_preferencias = await database["preferencias"].find_one({"username": username})

    # Verificar si el usuario existe
    if not user_preferencias:
        return "error"

    # Verificar si la preferencia solicitada existe en el documento
    if preferencia not in user_preferencias:
        return "error"

    # Obtener los valores actuales de la preferencia
    valores_actuales = user_preferencias[preferencia]

    # Verificar si el valor está en la lista de preferencias
    if valor not in valores_actuales:
        return "existing"

    # Eliminar el valor de la lista
    valores_actuales.remove(valor)

    # Actualizar el documento en MongoDB
    await database["preferencias"].update_one(
        {"username": username},
        {"$set": {preferencia: valores_actuales}}
    )

    return "success"

# @app.put("/eliminar_preferencia")
# def eliminar_preferencia(username: str, preferencia: str, valor: str):
#     sheet = client.open("AhorrappDB").worksheet("Preferencias")
#     filas = sheet.get_all_records()

#     # Encontrar la fila correspondiente al usuario
#     for idx, fila in enumerate(filas):
#         if fila['username'] == username:
#             # Obtener la preferencia correspondiente
#             valores_actuales = fila[preferencia].split(',') if fila[preferencia] else []

#             # Verificar si el valor está en la lista
#             if valor not in valores_actuales:
#                 return "existing"

#             # Eliminar el valor de la lista
#             valores_actuales.remove(valor)

#             # Actualizar la hoja de cálculo con los nuevos valores
#             nuevos_valores = ','.join(valores_actuales)
#             sheet.update_cell(idx + 2, sheet.find(preferencia).col, nuevos_valores)

#             return "success"

#     return "error"

@app.delete("/gastos-list")
async def eliminar_gasto(data: dict = Body(...)):
    gasto = data['gasto']
    tabla = data['tabla']
    user = data['user']

    # Seleccionar la colección correcta en función del tipo de gasto
    if tabla == 'fijos':
        collection = database["gastos_fijos"]
    elif tabla == 'ocasionales':
        collection = database["gastos_ocasionales"]
    else:
        raise HTTPException(status_code=400, detail="Tabla no válida")

    # Buscar y eliminar el gasto del array de la colección seleccionada
    result = await collection.find_one_and_update(
        {"username": user},  # Buscar por el usuario
        {
            "$pull": {
                "gastos": {
                    "fecha": gasto['fecha'],
                    "monto": gasto['monto'],
                    "producto": gasto['producto'],
                    "categoria": gasto['categoria'],
                    "metodoPago": gasto['metodoPago'],
                    "esNecesidad": gasto['esNecesidad']
                }
            }
        },
        return_document=ReturnDocument.AFTER
    )

    # Si no se encontró el gasto, lanzar un error
    if not result or 'gastos' not in result:
        raise HTTPException(status_code=404, detail="Gasto no encontrado o ya eliminado")

    return {"detail": "Gasto eliminado"}

# @app.delete("/gastos-list")
# def eliminar_gasto(data: dict = Body(...)):
#     gasto = data['gasto']
#     tabla = data['tabla']

#     # Abrir la hoja de Google Sheets correspondiente
#     if tabla == 'fijos':
#         sheet = client.open("AhorrappDB").worksheet("Gastos_fijos")
#     elif tabla == 'ocasionales':
#         sheet = client.open("AhorrappDB").worksheet("Gastos_ocasionales")
#     else:
#         raise HTTPException(status_code=400, detail="Tabla no válida")

#     # Obtener todas las filas de la hoja
#     all_records = sheet.get_all_records()

#     # Buscar la fila que coincide con los datos del gasto
#     row_to_delete = None
#     for idx, record in enumerate(all_records, start=2):  # Enumerar desde 2 porque la primera fila son los encabezados
#         if (record['username'] == gasto['username'] and
#                 record['fecha'] == gasto['fecha'] and 
#                 record['monto'] == gasto['monto'] and
#                 record['producto'] == gasto['producto'] and
#                 record['categoria'] == gasto['categoria'] and
#                 record['metodoPago'] == gasto['metodoPago']
#                 ):
#             row_to_delete = idx
#             break

#     # Si encontramos la fila, la eliminamos
#     if row_to_delete:
#         sheet.delete_rows(row_to_delete)
#         return {"detail": "Gasto eliminado"}
#     else:
#         raise HTTPException(status_code=404, detail="Gasto no encontrado")