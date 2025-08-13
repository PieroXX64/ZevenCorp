import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
import requests  # Necesitamos esta librería para interactuar con SheetDB
import datetime  # Necesario para la marca de tiempo en los logs

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necesario para manejar sesiones

# URL de la API de SheetDB para los resultados (esto ya lo tienes)
SHEETDB_API_URL = "https://sheetdb.io/api/v1/t5uvp45rl7ias"  # URL para los resultados

# URL de la API de SheetDB para los filtros (deberás poner esta URL específica para tu caso)
SHEETDB_API_URL_FILTERS = "https://sheetdb.io/api/v1/4m9mlphf2sk56"  # Reemplaza con la URL de tu hoja de filtros

# Variable global para almacenar el DataFrame cargado
df_evaluacion = pd.DataFrame()
is_data_loaded = False  # Variable global para controlar si los datos están cargados

def cargar_datos_desde_sheetdb():
    """Leer datos desde Google Sheets usando SheetDB para los filtros."""
    global df_evaluacion, is_data_loaded
    try:
        # Solicitud a la API de SheetDB
        response = requests.get(SHEETDB_API_URL_FILTERS, timeout=30)

        if response.status_code == 200:
            # Cargar JSON a DataFrame
            df_evaluacion = pd.DataFrame(response.json())

            # --- Normalización de columnas y datos ---
            # Quitar espacios en los nombres de columnas
            df_evaluacion.columns = [str(c).strip() for c in df_evaluacion.columns]

            # Reemplazar strings vacíos por NA
            df_evaluacion = df_evaluacion.replace(r'^\s*$', pd.NA, regex=True)

            # Normalizar columnas de texto (si existen)
            texto_cols = ['SEDE_PRINCIPAL', 'SEDE_CURSO', 'Carrera', 'Asignatura', 'INSTRUCTOR', 'Tipo_Curso']
            for col in texto_cols:
                if col in df_evaluacion.columns:
                    df_evaluacion[col] = df_evaluacion[col].astype(str).str.strip()

            # Normalizar columnas numéricas (SheetDB suele entregar strings)
            num_cols = ['ANO', 'PERIODO', 'Seccion', 'NRC']
            for col in num_cols:
                if col in df_evaluacion.columns:
                    df_evaluacion[col] = pd.to_numeric(df_evaluacion[col], errors='coerce')

            # Log útil
            print("[INFO] dtypes tras normalización:\n", df_evaluacion.dtypes)
            print("[INFO] Primeros 5 registros del DataFrame:\n", df_evaluacion.head())

            is_data_loaded = True
            print("[INFO] Datos de filtros cargados correctamente desde SheetDB.")
        else:
            print(f"[ERROR] Error al obtener datos de SheetDB para filtros: {response.text}")
            is_data_loaded = False

    except Exception as e:
        print(f"[ERROR] Error al obtener datos desde SheetDB: {e}")
        is_data_loaded = False



@app.route('/')
def home():
    # Mostrar la página de inicio con el botón de carga
    return render_template('index.html')

@app.route('/evaluacion_docente')
def evaluacion_docente():
    return render_template('evaluacion_docente.html')

@app.route('/load_data', methods=['POST'])
def load_data():
    """Carga los datos desde Google Sheets usando SheetDB al hacer clic en el botón."""
    global is_data_loaded
    if not is_data_loaded:  # Verifica si los datos ya han sido cargados
        cargar_datos_desde_sheetdb()  # Cargar datos desde SheetDB
        if is_data_loaded:
            print(f"[INFO] Datos de filtros cargados correctamente.")  # Debug
            return jsonify({"status": "success", "message": "Datos de filtros cargados correctamente"})
        else:
            return jsonify({"status": "error", "message": "Error al cargar los datos desde SheetDB"})
    else:
        return jsonify({"status": "info", "message": "Los datos de filtros ya están cargados"})

@app.route('/get_anos')
def get_anos():
    """Obtiene los años del archivo procesado."""  
    global is_data_loaded
    if is_data_loaded:
        try:
            anos = sorted(df_evaluacion['ANO'].dropna().unique())
            anos = [int(a) for a in anos]  # Convertir a tipos nativos de Python
            print(f"[INFO] Años disponibles en el archivo: {anos}")
            return jsonify(anos)
        except Exception as e:
            print(f"[ERROR] al obtener años: {e}")
            return jsonify([])
    else:
        return jsonify({"status": "error", "message": "No data loaded"})

@app.route('/get_periodos')
def get_periodos():
    """Obtiene los periodos del archivo procesado filtrados por año."""
    global is_data_loaded, df_evaluacion

    # Toma el año ya casteado a int; si no viene, devolvemos lista vacía
    ano = request.args.get('ano', type=int)
    if ano is None:
        print("[WARN] /get_periodos llamado sin parámetro 'ano'")
        return jsonify([])

    # Si aún no hay datos en memoria, intenta cargarlos
    if not is_data_loaded:
        cargar_datos_desde_sheetdb()

    # Validaciones básicas
    if df_evaluacion is None or df_evaluacion.empty:
        print("[ERROR] /get_periodos: df_evaluacion vacío o no cargado")
        return jsonify([])

    if 'ANO' not in df_evaluacion.columns or 'PERIODO' not in df_evaluacion.columns:
        print("[ERROR] /get_periodos: columnas requeridas no presentes en df_evaluacion")
        return jsonify([])

    try:
        # Cast defensivo: asegura que las columnas relevantes son numéricas
        anos_series = pd.to_numeric(df_evaluacion['ANO'], errors='coerce')
        periodos_col = pd.to_numeric(df_evaluacion['PERIODO'], errors='coerce')

        # Filtra por el año solicitado
        mask = anos_series == ano
        if not mask.any():
            print(f"[INFO] /get_periodos: no hay filas para ANO={ano}")
            return jsonify([])

        # Extrae periodos únicos, válidos y ordenados
        periodos = (
            periodos_col[mask]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
        periodos.sort()

        print(f"[DEBUG] /get_periodos -> ANO={ano}, PERIODOS={periodos}")
        return jsonify(periodos)

    except Exception as e:
        print(f"[ERROR] /get_periodos exception: {e}")
        return jsonify([])


@app.route('/get_sedes')
def get_sedes():
    """Obtiene las sedes del archivo procesado filtrados por año y periodo."""
    ano = request.args.get('ano')
    periodo = request.args.get('periodo')
    global is_data_loaded
    if ano and periodo:
        try:
            df_filtrado = df_evaluacion[
                (df_evaluacion['ANO'] == int(ano)) &
                (df_evaluacion['PERIODO'] == int(periodo))
            ]
            sedes = sorted(df_filtrado['SEDE_PRINCIPAL'].dropna().unique())
            sedes = [str(s) for s in sedes]
            print(f"[INFO] Sedes disponibles para el año {ano} y periodo {periodo}: {sedes}")
            return jsonify(sedes)
        except Exception as e:
            print(f"[ERROR] al obtener sedes: {e}")
            return jsonify([])
    return jsonify([])

@app.route('/get_carreras')
def get_carreras():
    """Obtiene las carreras del archivo procesado filtrados por año, periodo y sede."""
    ano = request.args.get('ano')
    periodo = request.args.get('periodo')
    sede = request.args.get('sede')
    global is_data_loaded
    if ano and periodo and sede:
        try:
            df_filtrado = df_evaluacion[
                (df_evaluacion['ANO'] == int(ano)) &
                (df_evaluacion['PERIODO'] == int(periodo)) &
                (df_evaluacion['SEDE_PRINCIPAL'] == sede)
            ]
            carreras = sorted(df_filtrado['Carrera'].dropna().unique())
            carreras = [str(c) for c in carreras]
            print(f"[INFO] Carreras disponibles para el año {ano}, periodo {periodo} y sede {sede}: {carreras}")
            return jsonify(carreras)
        except Exception as e:
            print(f"[ERROR] al obtener carreras: {e}")
            return jsonify([])
    return jsonify([])

@app.route('/get_secciones')
def get_secciones():
    """Obtiene las secciones del archivo procesado filtrados por año, periodo, sede y carrera."""
    ano = request.args.get('ano')
    periodo = request.args.get('periodo')
    sede = request.args.get('sede')
    carrera = request.args.get('carrera')
    global is_data_loaded
    if ano and periodo and sede and carrera:
        try:
            df_filtrado = df_evaluacion[
                (df_evaluacion['ANO'] == int(ano)) &
                (df_evaluacion['PERIODO'] == int(periodo)) &
                (df_evaluacion['SEDE_PRINCIPAL'] == sede) &
                (df_evaluacion['Carrera'] == carrera)
            ]
            secciones = sorted(df_filtrado['Seccion'].dropna().unique())
            secciones = [str(s) for s in secciones]
            print(f"[INFO] Secciones disponibles para el año {ano}, periodo {periodo}, sede {sede} y carrera {carrera}: {secciones}")
            return jsonify(secciones)
        except Exception as e:
            print(f"[ERROR] al obtener secciones: {e}")
            return jsonify([])
    return jsonify([])

@app.route('/get_asignaturas')
def get_asignaturas():
    ano = request.args.get('ano')
    periodo = request.args.get('periodo')
    sede = request.args.get('sede')
    carrera = request.args.get('carrera')
    seccion = request.args.get('seccion')
    global is_data_loaded
    if all([ano, periodo, sede, carrera, seccion]):
        try:
            print(f"[DEBUG] Filtros recibidos: año={ano}, periodo={periodo}, sede={sede}, carrera={carrera}, seccion={seccion}")
            print("[DEBUG] Valores únicos en df_evaluacion['Carrera']:", df_evaluacion['Carrera'].unique())
            print("[DEBUG] Valores únicos en df_evaluacion['Seccion']:", df_evaluacion['Seccion'].unique())
            print("[DEBUG] Valores únicos en df_evaluacion['SEDE_PRINCIPAL']:", df_evaluacion['SEDE_PRINCIPAL'].unique())

            df_filtrado = df_evaluacion[
                (df_evaluacion['ANO'] == int(ano)) &
                (df_evaluacion['PERIODO'] == int(periodo)) &
                (df_evaluacion['SEDE_PRINCIPAL'] == sede) &
                (df_evaluacion['Carrera'] == carrera) &
                (df_evaluacion['Seccion'] == int(seccion))  # CORREGIDO AQUÍ
            ]
            asignaturas = sorted(df_filtrado['Asignatura'].dropna().unique())
            asignaturas = [str(a) for a in asignaturas]
            return jsonify(asignaturas)
        except Exception as e:
            print(f"[ERROR] al obtener asignaturas: {e}")
            return jsonify([])
    return jsonify([])

@app.route('/get_instructores')
def get_instructores():
    ano = request.args.get('ano')
    periodo = request.args.get('periodo')
    sede = request.args.get('sede')
    carrera = request.args.get('carrera')
    seccion = request.args.get('seccion')
    asignatura = request.args.get('asignatura')
    
    if all([ano, periodo, sede, carrera, seccion, asignatura]):
        try:
            df_filtrado = df_evaluacion[
                (df_evaluacion['ANO'] == int(ano)) &
                (df_evaluacion['PERIODO'] == int(periodo)) &
                (df_evaluacion['SEDE_PRINCIPAL'] == sede) &
                (df_evaluacion['Carrera'] == carrera) &
                (df_evaluacion['Seccion'] == int(seccion)) &
                (df_evaluacion['Asignatura'] == asignatura)
            ]

            instructores = sorted(df_filtrado['INSTRUCTOR'].dropna().unique())

            # Lista de instructores a excluir
            instructores_excluir = [
                'LIM EOM AS INSTRUCTOR', 'LIM PM AS INSTRUCTOR', 'LIM SI AS INSTRUCTOR',
                'LIM MMP AS INSTRUCTOR', 'LIM MSEII AS INSTRUCTOR',
                'AQP EOM AS INSTRUCTOR', 'AQP SI AS INSTRUCTOR', 'AQP PM AS INSTRUCTOR',
                'AQP MMP AS INSTRUCTOR', 'AQP MSEII AS INSTRUCTOR'
            ]

            instructores_filtrados = [i for i in instructores if i not in instructores_excluir]

            return jsonify(instructores_filtrados)
        except Exception as e:
            print(f"[ERROR] al obtener instructores: {e}")
            return jsonify([])
    
    return jsonify([])

@app.route('/get_nrc')
def get_nrc():
    try:
        filtros = {
            'ANO': int(request.args.get('ano')),
            'PERIODO': int(request.args.get('periodo')),
            'SEDE_PRINCIPAL': request.args.get('sede'),
            'Carrera': request.args.get('carrera'),
            'Seccion': int(request.args.get('seccion')),
            'Asignatura': request.args.get('asignatura'),
            'INSTRUCTOR': request.args.get('instructor')
        }

        df_filtrado = df_evaluacion.copy()

        for k, v in filtros.items():
            if v is not None:
                df_filtrado = df_filtrado[df_filtrado[k] == v]

        if not df_filtrado.empty:
            return jsonify({
                'nrc': str(df_filtrado.iloc[0]['NRC']),
                'sede_curso': str(df_filtrado.iloc[0]['SEDE_CURSO'])
            })

        return jsonify({'nrc': None, 'sede_curso': None})
    
    except Exception as e:
        print(f"[ERROR] en /get_nrc: {e}")
        return jsonify({'nrc': None, 'sede_curso': None})

@app.route('/get_tipo_curso_por_nrc')
def get_tipo_curso_por_nrc():
    nrc = request.args.get('nrc')
    if not nrc:
        return jsonify({'tipo_curso': None})
    
    df_filtrado = df_evaluacion[df_evaluacion['NRC'].astype(str) == str(nrc)]

    if not df_filtrado.empty:
        tipo = df_filtrado.iloc[0]['Tipo_Curso']
        return jsonify({'tipo_curso': tipo})
    return jsonify({'tipo_curso': None})
    
import io
import pandas as pd

import requests  # Necesitamos esta librería para interactuar con SheetDB

@app.route('/guardar_resultado_tp', methods=['POST'])
def guardar_resultado_tp():
    """Guardar el resultado del formulario TP en Google Sheets usando SheetDB (aplanando respuestas)."""
    try:
        data = request.get_json()
        print(f"[INFO] Datos recibidos: {data}")

        # --- Campos base (filtros + totales por sección) ---
        nuevo_registro = {
            "ANO": data.get("ANO", ""),
            "PERIODO": data.get("PERIODO", ""),
            "SEDE_CURSO": data.get("SEDE_CURSO", ""),
            "Carrera": data.get("Carrera", ""),
            "Seccion": data.get("Seccion", ""),
            "Asignatura": data.get("Asignatura", ""),
            "INSTRUCTOR": data.get("INSTRUCTOR", ""),
            "NRC": data.get("NRC", ""),
            # Totales/porcentajes y resultados por sección
            "Aula_Porcentaje": data.get("Eval_Aula", ""),
            "Aula_Resultado": data.get("Resultado_Aula", ""),
            "Carpeta_Porcentaje": data.get("Eval_Carpeta", ""),
            "Carpeta_Resultado": data.get("Resultado_Carpeta", ""),
        }

        # --- Sección AULA: aplanar preguntas ---
        # Espera data.respuestasAula como lista de objetos:
        # { valoracion: str, puntaje: str/num, observaciones: str, recomendaciones: str }
        respuestas_aula = data.get("respuestasAula", []) or []
        for idx, item in enumerate(respuestas_aula, start=1):
            nuevo_registro[f"A{idx}_Valoracion"] = (item.get("valoracion") or "").strip()
            nuevo_registro[f"A{idx}_Puntaje"] = item.get("puntaje") or ""
            nuevo_registro[f"A{idx}_Observaciones"] = (item.get("observaciones") or "").strip()
            nuevo_registro[f"A{idx}_Recomendaciones"] = (item.get("recomendaciones") or "").strip()

        # --- Sección CARPETA: aplanar preguntas ---
        # Espera data.respuestasCarpeta como lista de objetos:
        # { valoracion: str, observaciones: str, recomendaciones: str }
        respuestas_carpeta = data.get("respuestasCarpeta", []) or []
        for idx, item in enumerate(respuestas_carpeta, start=1):
            nuevo_registro[f"C{idx}_Valoracion"] = (item.get("valoracion") or "").strip()
            nuevo_registro[f"C{idx}_Observaciones"] = (item.get("observaciones") or "").strip()
            nuevo_registro[f"C{idx}_Recomendaciones"] = (item.get("recomendaciones") or "").strip()

        # --- Envío a SheetDB ---
        response = requests.post(SHEETDB_API_URL, json=nuevo_registro, timeout=30)
        response_data = {}
        try:
            response_data = response.json()
        except Exception:
            pass

        print(f"[INFO] Respuesta de SheetDB: {response.status_code} {response_data}")

        if response.status_code == 200 or response_data.get('created') == 1:
            return jsonify({"status": "ok", "mensaje": "Evaluación guardada exitosamente"})
        else:
            return jsonify({"status": "error", "mensaje": f"Error al guardar: {response_data or response.text}"})

    except Exception as e:
        print(f"[ERROR] Error al guardar la evaluación: {e}")
        return jsonify({"status": "error", "mensaje": str(e)})
    
@app.route('/formulario_p')
def formulario_p():
    nrc = request.args.get('nrc')
    return render_template('formulario_p.html', nrc=nrc)

@app.route('/formulario_tp')
def formulario_tp():
    nrc = request.args.get('nrc')
    return render_template('formulario_tp.html', nrc=nrc)

@app.route('/cronjob_load_data', methods=['GET'])
def cronjob_load_data():
    """Este endpoint se ejecutará a través del cronjob para cargar automáticamente los datos desde SheetDB."""
    global is_data_loaded
    if not is_data_loaded:  # Verifica si los datos ya han sido cargados
        cargar_datos_desde_sheetdb()  # Cargar datos desde SheetDB
        if is_data_loaded:
            print(f"[INFO] Datos de filtros cargados correctamente desde SheetDB a las {datetime.datetime.now()}.")
            return jsonify({"status": "success", "message": "Datos de filtros cargados correctamente"})
        else:
            print(f"[ERROR] Error al cargar los datos desde SheetDB.")
            return jsonify({"status": "error", "message": "Error al cargar los datos desde SheetDB"})
    else:
        print(f"[INFO] Los datos de filtros ya están cargados.")
        return jsonify({"status": "info", "message": "Los datos de filtros ya están cargados"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Usar el puerto dinámico proporcionado por Render
    app.run(debug=True, host="0.0.0.0", port=port)  # Escuchar en todas las interfaces de red
