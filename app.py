import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
import boto3
from io import BytesIO

app = Flask(__name__)

# Configuración de S3 (asegúrate de que las credenciales estén configuradas correctamente)
s3_client = boto3.client('s3')
BUCKET_NAME = 'zeven-corp'  # Reemplaza con el nombre de tu bucket en S3

# Variable global (para almacenar el DataFrame cargado)
df_evaluacion = pd.DataFrame()

def cargar_archivo_s3(nombre_archivo):
    """Leer archivo procesado desde S3 y cargarlo en el DataFrame."""
    global df_evaluacion
    try:
        # Descargar el archivo desde S3
        file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=nombre_archivo)
        file_data = file_obj['Body'].read()

        # Leerlo con pandas
        df_evaluacion = pd.read_excel(BytesIO(file_data))
        print(f"[INFO] Archivo {nombre_archivo} cargado correctamente desde S3.")
        print(f"[INFO] Primeros 5 registros del DataFrame:\n{df_evaluacion.head()}")  # Verifica los datos cargados
    except Exception as e:
        print(f"[ERROR] Error al cargar el archivo desde S3: {e}")

@app.route('/')
def home():
    # Cargar el archivo automáticamente desde S3 al acceder a la página principal
    cargar_archivo_s3('planificacion_academica_proc.xlsx')
    
    # Renderizar la página con los datos ya cargados desde S3
    return render_template('index.html')

@app.route('/evaluacion_docente')
def evaluacion_docente():
    return render_template('evaluacion_docente.html')

@app.route('/get_anos')
def get_anos():
    """Obtiene los años del archivo procesado."""  
    try:
        anos = sorted(df_evaluacion['ANO'].dropna().unique())
        anos = [int(a) for a in anos]  # Convertir a tipos nativos de Python
        print(f"[INFO] Años disponibles en el archivo: {anos}")
        return jsonify(anos)
    except Exception as e:
        print(f"[ERROR] al obtener años: {e}")
        return jsonify([])

@app.route('/get_periodos')
def get_periodos():
    """Obtiene los periodos del archivo procesado filtrados por año."""
    ano = request.args.get('ano')
    if ano:
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

        # Guardar el archivo procesado como evaluacion_docente_proc.xlsx en S3
        ruta_archivo = 'evaluacion_docente_proc.xlsx'  # Ruta en S3, solo el nombre de archivo en este caso
        s3_client.put_object(Body=pd.DataFrame([nuevo_registro]).to_excel(index=False), Bucket=BUCKET_NAME, Key=ruta_archivo)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Usar el puerto dinámico proporcionado por Render
    app.run(debug=True, host="0.0.0.0", port=port)  # Escuchar en todas las interfaces de red

