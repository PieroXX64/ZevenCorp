import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROCESADOS_FOLDER = os.path.join(BASE_DIR, 'procesados')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESADOS_FOLDER, exist_ok=True)

MEMORIA_NRC_PATH = os.path.join(PROCESADOS_FOLDER, 'nrc_memoria.xlsx')
ARCHIVO_PLANIFICACION = os.path.join(UPLOAD_FOLDER, 'planificacion_academica.xlsx')
ARCHIVO_PROCESADO = os.path.join(PROCESADOS_FOLDER, 'planificacion_academica_proc.xlsx')

# Variable global
if os.path.exists(ARCHIVO_PROCESADO):
    df_evaluacion = pd.read_excel(ARCHIVO_PROCESADO)
else:
    df_evaluacion = pd.DataFrame()

def generar_nrcs(df):
    memoria_nrc = {}
    if os.path.exists(MEMORIA_NRC_PATH):
        memoria_nrc_df = pd.read_excel(MEMORIA_NRC_PATH)
        for _, row in memoria_nrc_df.iterrows():
            key = (row['ANO'], row['PERIODO'], row['Codigo_Carrera'], row['Codigo_Curso'], row['Seccion'])
            memoria_nrc[key] = row['NRC']
        last_nrc = memoria_nrc_df['NRC'].max()
    else:
        last_nrc = 999

    nuevos_nrcs = []
    for _, row in df.iterrows():
        key = (row['ANO'], row['PERIODO'], row['Codigo_Carrera'], row['Codigo_Curso'], row['Seccion'])
        if key in memoria_nrc:
            nrc = memoria_nrc[key]
        else:
            last_nrc += 1
            nrc = last_nrc
            memoria_nrc[key] = nrc
        nuevos_nrcs.append(nrc)

    df['NRC'] = nuevos_nrcs

    memoria_actualizada = pd.DataFrame([
        {'ANO': k[0], 'PERIODO': k[1], 'Codigo_Carrera': k[2], 'Codigo_Curso': k[3], 'Seccion': k[4], 'NRC': v}
        for k, v in memoria_nrc.items()
    ])
    memoria_actualizada.to_excel(MEMORIA_NRC_PATH, index=False)

    return df

def procesar_planificacion():
    global df_evaluacion
    try:
        print(f"[INFO] Leyendo archivo local: {ARCHIVO_PLANIFICACION}")
        df = pd.read_excel(ARCHIVO_PLANIFICACION)

        # Definir sedes principales
        carreras_fchb = ['AQPEOM', 'AQPSI', 'AQPPM', 'AQPMMP', 'AQPMSEII']
        carreras_abq = ['LIMEOM', 'LIMSI', 'LIMPM']
        carreras_irq = ['LIMMMP', 'LIMMSEII']

        def sede_principal(codigo):
            if codigo in carreras_fchb:
                return 'FCHB'
            elif codigo in carreras_abq:
                return 'ABQ'
            elif codigo in carreras_irq:
                return 'IRQ'
            return pd.NA

        df['SEDE_PRINCIPAL'] = df['Codigo_Carrera'].apply(sede_principal)

        empleabilidad_cursos = [
            'MARCA PROFESIONAL', 'COMUNICACIÓN PROFESIONAL', 'LIDERAZGO PROFESIONAL',
            'INNOVACIÓN TECNOLÓGICA', 'INGLÉS TÉCNICO', 'INFORMÁTICA BÁSICA'
        ]
        empleabilidad_cursos = [c.upper() for c in empleabilidad_cursos]

        df['SEDE_CURSO'] = df.apply(
            lambda row: 'EMPLEABILIDAD' if str(row['Asignatura']).upper() in empleabilidad_cursos else row['SEDE_PRINCIPAL'],
            axis=1
        )

        def modalidad(valor):
            try:
                valor = int(valor)
            except:
                return pd.NA
            if valor in [1, 3]:
                return 'PRESENCIAL'
            elif valor == 2:
                return 'VIRTUAL'
            return pd.NA

        df['MODALIDAD'] = df['Periodo_Nivel'].apply(modalidad)

        def tipo_curso(asignatura):
            asignatura = str(asignatura).upper()
            if asignatura.startswith('PROYECTO') or asignatura.startswith('EFSRT'):
                return 'P'
            return 'TP'

        df['Tipo_Curso'] = df['Asignatura'].apply(tipo_curso)

        df['INSTRUCTOR'] = df['Apellido_Docente'].astype(str) + ' ' + df['Nombre_Docente'].astype(str)

        if 'Carrera' not in df.columns:
            df['Carrera'] = df['Codigo_Carrera']

        if 'FechaCierre' in df.columns:
            col_index = df.columns.get_loc('FechaCierre') + 1
            nuevas_columnas = ['SEDE_PRINCIPAL', 'SEDE_CURSO', 'MODALIDAD', 'Tipo_Curso', 'INSTRUCTOR']
            nuevas_vals = df[nuevas_columnas].copy()
            df.drop(columns=nuevas_columnas, inplace=True)
            for i, col in enumerate(nuevas_columnas):
                df.insert(col_index + i, col, nuevas_vals[col])
        else:
            print("[ADVERTENCIA] Columna 'FechaCierre' no encontrada. Columnas adicionales no reordenadas.")

        df = generar_nrcs(df)

        output_path = os.path.join(PROCESADOS_FOLDER, 'planificacion_academica_proc.xlsx')
        df.to_excel(output_path, index=False)
        print(f"[INFO] Archivo procesado y guardado como: {output_path}")
        df_evaluacion = df

    except Exception as e:
        print(f"[ERROR] Error al procesar archivo local: {e}")

# --- Rutas Flask ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/evaluacion_docente')
def evaluacion_docente():
    return render_template('evaluacion_docente.html')

@app.route('/get_anos')
def get_anos():
    try:
        anos = sorted(df_evaluacion['ANO'].dropna().unique())
        anos = [int(a) for a in anos]  # Convertir a tipos nativos de Python
        return jsonify(anos)
    except Exception as e:
        print(f"[ERROR] al obtener años: {e}")
        return jsonify([])

@app.route('/get_periodos')
def get_periodos():
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

@app.route('/guardar_resultado', methods=['POST'])
def guardar_resultado():
    try:
        data = request.get_json()
        columnas = [
            "ANO", "PERIODO", "SEDE_CURSO", "Carrera",
            "Seccion", "Asignatura", "INSTRUCTOR", "NRC",
            "Eval_Aula", "Eval_Carpeta"
        ]
        nuevo_registro = {col: data.get(col, "") for col in columnas}

        ruta_archivo = os.path.join("procesados", "evaluacion_docente_proc.xlsx")
        if os.path.exists(ruta_archivo):
            df_existente = pd.read_excel(ruta_archivo)
            df_existente = pd.concat([df_existente, pd.DataFrame([nuevo_registro])], ignore_index=True)
        else:
            df_existente = pd.DataFrame([nuevo_registro])

        df_existente.to_excel(ruta_archivo, index=False)
        return jsonify({"status": "ok"})
    except Exception as e:
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
    procesar_planificacion()
    app.run(debug=True)
