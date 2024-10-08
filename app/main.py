from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Autenticación de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(creds)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Cambia esto por la URL donde se desplegará tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    username: str
    password: str

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
def register(user: User):
    sheet_usuarios = client.open("AhorrappDB").worksheet("Usuarios")  # Hoja de usuarios
    users = sheet_usuarios.get_all_records()
    for record in users:
        if record['username'] == user.username:
            return False
    sheet_usuarios.append_row([user.username, user.password])
    
    sheet_preferencias = client.open("AhorrappDB").worksheet("Preferencias")
    sheet_preferencias.append_row([user.username, 
                                   "Anual,Diario,Mensual,Semanal",
                                   "Agua,Alquiler,Celular,Comida,Cuenta/Subscripción,Gas,Higiene,Internet,Luz,Mascota,Productos del Hogar,Salud,Transporte",
                                   "Comida,Cuenta/Subscripción,Educación,Higiene,Mascota,Ocio,Productos del Hogar,Salud,Transporte",
                                   "Crédito,Daviplata,Débito,Efectivo,Nequi,Transfiya"])
    return True

@app.post("/login")
def login(user: User):
    sheet_usuarios = client.open("AhorrappDB").worksheet("Usuarios")  # Hoja de usuarios
    users = sheet_usuarios.get_all_records()
    for record in users:
        if str(record['username']) == user.username and str(record['password']) == user.password:
            return True
    return False
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
def obtener_gastos_del_periodo(username: str, desde: str, hasta:str):
    sheet_gastos_fijos = client.open("AhorrappDB").worksheet("Gastos_fijos")
    sheet_gastos_ocasionales = client.open("AhorrappDB").worksheet("Gastos_ocasionales")

    # Filtrar gastos fijos y ocasionales según la fecha
    gastos_fijos = sheet_gastos_fijos.get_all_records()
    gastos_ocasionales = sheet_gastos_ocasionales.get_all_records()

    # Filtrar por fecha y usuario
    gastos_filtrados_fijos = [gasto for gasto in gastos_fijos if gasto['username'] == username and gasto['fecha'] >= desde and gasto['fecha'] <= hasta]
    gastos_filtrados_ocasionales = [gasto for gasto in gastos_ocasionales if gasto['username'] == username and gasto['fecha'] >= desde and gasto['fecha'] <= hasta]

    # Unir los dos tipos de gastos
    todos_los_gastos = gastos_filtrados_fijos + gastos_filtrados_ocasionales
    total_acumulado = sum(gasto['monto'] for gasto in todos_los_gastos)

    return {"gastos": todos_los_gastos, "total": total_acumulado}

@app.get("/gastos-list")
def obtener_gastos_del_usuario(username: str):
    sheet_gastos_fijos = client.open("AhorrappDB").worksheet("Gastos_fijos")
    sheet_gastos_ocasionales = client.open("AhorrappDB").worksheet("Gastos_ocasionales")

    # Filtrar gastos fijos y ocasionales según la fecha
    gastos_fijos = sheet_gastos_fijos.get_all_records()
    gastos_ocasionales = sheet_gastos_ocasionales.get_all_records()

    # Filtrar por usuario
    gastos_filtrados_fijos = sorted(
    [gasto for gasto in gastos_fijos if gasto['username'] == username],
    key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'),
    reverse=True
)
    gastos_filtrados_ocasionales = sorted(
    [gasto for gasto in gastos_ocasionales if gasto['username'] == username],
    key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'),
    reverse=True
)
    for gasto in gastos_filtrados_fijos:
        gasto['esNecesidad'] = gasto['esNecesidad'].upper() == 'TRUE'

    for gasto in gastos_filtrados_ocasionales:
        gasto['esNecesidad'] = gasto['esNecesidad'].upper() == 'TRUE'

    return {"fijos": gastos_filtrados_fijos, "ocasionales": gastos_filtrados_ocasionales}

@app.get("/{preferencia}")
def obtener_preferencias(username: str, preferencia: str):
    sheet = client.open("AhorrappDB").worksheet("Preferencias")
    filas = sheet.get_all_records()
    for fila in filas:
        if fila['username'] == username:
            # Devolver la lista de categorías fijas para ese usuario
            preferencias = fila[preferencia].split(',')  # Suponiendo que las categorías están separadas por comas
            return preferencias

    return {"error": "Usuario no encontrado"}


@app.post("/gastos/ocasionales")
def agregar_gasto_ocasional(gasto: GastoOcasional):
    try:
        sheet_gastos_ocasionales = client.open("AhorrappDB").worksheet("Gastos_ocasionales")  # Hoja de gastos ocasionales
        sheet_gastos_ocasionales.append_row([gasto.username, gasto.esNecesidad, gasto.categoria, gasto.producto, gasto.fecha, gasto.metodoPago, gasto.monto])
        return True
    except:
        return False

@app.post("/gastos/fijos")
def agregar_gasto_fijo(gasto: GastoFijo):
    try:
        sheet_gastos_fijos = client.open("AhorrappDB").worksheet("Gastos_fijos")  # Hoja de gastos fijos
        sheet_gastos_fijos.append_row([gasto.username, gasto.esNecesidad, gasto.categoria, gasto.producto, gasto.periodo, gasto.fecha, gasto.metodoPago, gasto.monto])
        return True
    except:
        return False
    
@app.put("/agregar_preferencia")
def agregar_preferencia(username: str, preferencia: str, valor: str):
    #return "existing"
    sheet = client.open("AhorrappDB").worksheet("Preferencias")
    filas = sheet.get_all_records()

    # Encontrar la fila correspondiente al usuario
    for idx, fila in enumerate(filas):
        if fila['username'] == username:
            # Obtener la preferencia correspondiente
            valores_actuales = fila[preferencia].split(',') if fila[preferencia] else []
            
            # Verificar si el nuevo valor ya existe
            if valor in valores_actuales:
                return "existing"

            # Agregar el nuevo valor a la lista
            valores_actuales.append(valor)
            valores_actuales.sort()
            
            # Actualizar la hoja de cálculo con los nuevos valores
            nuevos_valores = ','.join(valores_actuales)
            sheet.update_cell(idx + 2, sheet.find(preferencia).col, nuevos_valores)
            
            return "success"

    return "error"

@app.put("/eliminar_preferencia")
def eliminar_preferencia(username: str, preferencia: str, valor: str):
    sheet = client.open("AhorrappDB").worksheet("Preferencias")
    filas = sheet.get_all_records()

    # Encontrar la fila correspondiente al usuario
    for idx, fila in enumerate(filas):
        if fila['username'] == username:
            # Obtener la preferencia correspondiente
            valores_actuales = fila[preferencia].split(',') if fila[preferencia] else []

            # Verificar si el valor está en la lista
            if valor not in valores_actuales:
                return "existing"

            # Eliminar el valor de la lista
            valores_actuales.remove(valor)

            # Actualizar la hoja de cálculo con los nuevos valores
            nuevos_valores = ','.join(valores_actuales)
            sheet.update_cell(idx + 2, sheet.find(preferencia).col, nuevos_valores)

            return "success"

    return "error"

@app.delete("/gastos-list")
def eliminar_gasto(data: dict = Body(...)):
    gasto = data['gasto']
    tabla = data['tabla']

    # Abrir la hoja de Google Sheets correspondiente
    if tabla == 'fijos':
        sheet = client.open("AhorrappDB").worksheet("Gastos_fijos")
    elif tabla == 'ocasionales':
        sheet = client.open("AhorrappDB").worksheet("Gastos_ocasionales")
    else:
        raise HTTPException(status_code=400, detail="Tabla no válida")

    # Obtener todas las filas de la hoja
    all_records = sheet.get_all_records()

    # Buscar la fila que coincide con los datos del gasto
    row_to_delete = None
    for idx, record in enumerate(all_records, start=2):  # Enumerar desde 2 porque la primera fila son los encabezados
        if (record['username'] == gasto['username'] and
                record['fecha'] == gasto['fecha'] and 
                record['monto'] == gasto['monto'] and
                record['producto'] == gasto['producto'] and
                record['categoria'] == gasto['categoria'] and
                record['metodoPago'] == gasto['metodoPago']
                ):
            row_to_delete = idx
            break

    # Si encontramos la fila, la eliminamos
    if row_to_delete:
        sheet.delete_rows(row_to_delete)
        return {"detail": "Gasto eliminado"}
    else:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")