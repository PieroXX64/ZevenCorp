import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
import boto3
from io import BytesIO

app = Flask(__name__)

# Configuración de S3 (asegúrate de que las credenciales estén configuradas correctamente)
s3_client = boto3.client('s3')
BUCKET_NAME = 'tu-bucket-name'  # Reemplaza con el nombre de tu bucket en S3

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
    except Exception as e:
        print(f"[ERROR] Error al cargar el archivo desde S3: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/evaluacion_docente')
def evaluacion_docente():
    return render_template('evaluacion_docente.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Recibe el archivo procesado desde la interfaz web y lo sube a S3."""
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    try:
        # Subir archivo a S3
        s3_client.upload_fileobj(file, BUCKET_NAME, file.filename)
        # Cargar el archivo procesado desde S3
        cargar_archivo_s3(file.filename)
        return "Archivo cargado y procesado correctamente", 200
    except Exception as e:
        print(f"Error al cargar el archivo a S3: {e}")
        return "Error al cargar el archivo a S3", 500

@app.route('/get_anos')
def get_anos():
    """Obtiene los años del archivo procesado."""  
    try:
        anos = sorted(df_evaluacion['ANO'].dropna().unique())
        anos = [int(a) for a in anos]  # Convertir a tipos nativos de Python
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


