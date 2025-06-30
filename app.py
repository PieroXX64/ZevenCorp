import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, session
import boto3
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necesario para manejar sesiones

# Configuración de S3
s3_client = boto3.client('s3')
BUCKET_NAME = 'zeven-corp'  # Asegúrate de que este es el nombre correcto de tu bucket en S3

# Variable global para almacenar el DataFrame cargado
df_evaluacion = pd.DataFrame()

def cargar_archivo_s3(nombre_archivo):
    """Leer archivo procesado desde S3 y cargarlo en el DataFrame global."""
    global df_evaluacion
    try:
        print(f"[INFO] Intentando descargar el archivo {nombre_archivo} desde S3.")
        
        # Descargar el archivo desde S3
        file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=nombre_archivo)
        file_data = file_obj['Body'].read()

        # Leerlo con pandas
        df_evaluacion = pd.read_excel(BytesIO(file_data))
        print(f"[INFO] Archivo {nombre_archivo} cargado correctamente desde S3.")
        print(f"[INFO] Primeros 5 registros del DataFrame:\n{df_evaluacion.head()}")
        session['data_loaded'] = True  # Marcamos que los datos se han cargado
    except Exception as e:
        print(f"[ERROR] Error al cargar el archivo desde S3: {e}")
        session['data_loaded'] = False

@app.route('/')
def home():
    # Mostrar la página de inicio con el botón de carga
    return render_template('index.html')

@app.route('/evaluacion_docente')
def evaluacion_docente():
    return render_template('evaluacion_docente.html')

@app.route('/load_data', methods=['POST'])
def load_data():
    """Carga el archivo desde S3 al hacer clic en el botón."""
    if not session.get('data_loaded', False):  # Verifica si los datos ya han sido cargados
        cargar_archivo_s3('planificacion_academica_proc.xlsx')  # Cargar datos desde S3
        if session.get('data_loaded', False):
            return jsonify({"status": "success", "message": "Datos cargados correctamente"})
        else:
            return jsonify({"status": "error", "message": "Error al cargar los datos desde S3"})
    else:
        return jsonify({"status": "info", "message": "Los datos ya están cargados"})

@app.route('/get_anos')
def get_anos():
    """Obtiene los años del archivo procesado."""  
    if session.get('data_loaded', False):
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
    if ano:
        # Cargar el archivo solo cuando sea necesario
        if not session.get('data_loaded', False):
            cargar_archivo_s3('planificacion_academica_proc.xlsx')
        
        try:
            periodos = sorted(df_evaluacion[df_evaluacion['ANO'] == int(ano)]['PERIODO'].dropna().unique())
            periodos = [int(p) for p in periodos]  # Asegurar tipos nativos
            print(f"[INFO] Periodos disponibles para el año {ano}: {periodos}")
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
@app.route('/guardar_resultado', methods=['POST'])
def guardar_resultado():
    """Guardar el resultado de la evaluación docente en S3."""  
    try:
        data = request.get_json()
        columnas = [
            "ANO", "PERIODO", "SEDE_CURSO", "Carrera",
            "Seccion", "Asignatura", "INSTRUCTOR", "NRC",
            "Eval_Aula", "Eval_Carpeta"
        ]
        nuevo_registro = {col: data.get(col, "") for col in columnas}

        # Crear el DataFrame con el nuevo registro
        df_nuevo_registro = pd.DataFrame([nuevo_registro])

        # Crear un objeto BytesIO para almacenar el archivo en memoria
        output = io.BytesIO()

        # Usar ExcelWriter para escribir el DataFrame en el archivo Excel en memoria
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_nuevo_registro.to_excel(writer, index=False, sheet_name='EvaluacionDocente')

        # Guardar el archivo procesado como evaluacion_docente_proc.xlsx en S3
        output.seek(0)  # Volver al principio del archivo en memoria
        s3_client.put_object(Body=output, Bucket=BUCKET_NAME, Key='evaluacion_docente_proc.xlsx')

        return jsonify({"status": "ok"})
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
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Usar el puerto dinámico proporcionado por Render
    app.run(debug=True, host="0.0.0.0", port=port)  # Escuchar en todas las interfaces de red

