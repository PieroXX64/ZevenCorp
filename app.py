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
        # Hacemos una solicitud GET a la API de SheetDB para obtener los filtros
        response = requests.get(SHEETDB_API_URL_FILTERS)
        
        if response.status_code == 200:
            # Convertir la respuesta en formato JSON a un DataFrame de pandas
            global df_evaluacion  # Añadido para modificar la variable global
            df_evaluacion = pd.DataFrame(response.json())
            is_data_loaded = True  # Marcamos que los datos se han cargado
            print(f"[INFO] Datos de filtros cargados correctamente desde SheetDB.")
            print(f"[INFO] Primeros 5 registros del DataFrame:\n{df_evaluacion.head()}")
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
    ano = request.args.get('ano')
    global is_data_loaded
    if ano:
        # Cargar los datos solo cuando no están cargados
        if not is_data_loaded:
            cargar_datos_desde_sheetdb()  # Cargar datos desde SheetDB

        # Depurar: Verifica si el DataFrame contiene datos después de cargar
        if df_evaluacion.empty:
            return jsonify({"status": "error", "message": "No se han cargado datos."})

        try:
            # Filtrando por 'ANO' y obteniendo los 'PERIODO'
            print(f"[DEBUG] Filtrando por el año: {ano}")
            df_filtrado = df_evaluacion[df_evaluacion['ANO'] == int(ano)]
            
            if df_filtrado.empty:
                print(f"[ERROR] No se encontraron datos para el año {ano}.")
                return jsonify([])

            periodos = sorted(df_filtrado['PERIODO'].dropna().unique())  # Obtiene los valores únicos de 'PERIODO'
            
            if not periodos:
                print(f"[ERROR] No se encontraron periodos para el año {ano}.")
                
            print(f"[DEBUG] Periodos encontrados para el año {ano}: {periodos}")
            
            periodos = [int(p) for p in periodos]  # Convertir a enteros para garantizar que no haya tipos incorrectos
            return jsonify(periodos)

        except Exception as e:
            print(f"[ERROR] al obtener periodos: {e}")
            return jsonify([])

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
    """Guardar el resultado del formulario TP en Google Sheets usando SheetDB."""  
    try:
        data = request.get_json()
        print(f"[INFO] Datos recibidos: {data}")  # Verificar que los datos son correctos

        # Crear el diccionario con los datos del formulario
        nuevo_registro = {
            "ANO": data.get("ANO", ""),
            "PERIODO": data.get("PERIODO", ""),
            "SEDE_CURSO": data.get("SEDE_CURSO", ""),
            "Carrera": data.get("Carrera", ""),
            "Seccion": data.get("Seccion", ""),
            "Asignatura": data.get("Asignatura", ""),
            "INSTRUCTOR": data.get("INSTRUCTOR", ""),
            "NRC": data.get("NRC", ""),
            "Eval_Aula": data.get("Eval_Aula", ""),
            "Eval_Carpeta": data.get("Eval_Carpeta", ""),
            # Añadir más campos de respuestas según tu formulario
        }

        # Realizar una solicitud POST a SheetDB para guardar los datos
        response = requests.post(SHEETDB_API_URL, json=nuevo_registro)

        # Verificamos si la respuesta tiene el campo "created"
        response_data = response.json()
        print(f"[INFO] Respuesta de SheetDB: {response_data}")

        if response.status_code == 200 or response_data.get('created') == 1:
            # Si "created" está presente y es igual a 1, significa que el registro fue creado
            return jsonify({"status": "ok", "mensaje": "Evaluación guardada exitosamente"})
        else:
            # Si no "created" o tiene un valor diferente a 1, devolvemos mensaje de error
            print(f"[ERROR] Error al guardar la evaluación: {response_data}")
            return jsonify({"status": "error", "mensaje": "Error al guardar la evaluación: " + str(response_data)})

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
