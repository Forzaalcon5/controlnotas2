from flask import Flask, render_template, request, redirect, session, send_file
from database import conectar, obtenerusuarios, insertar_estudiante, obtenerestudiantes
from dashprincipal import creartablero
import pandas as pd
import unicodedata
import io

app = Flask(__name__)
app.secret_key = "40414732"

creartablero(app)

server = app

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        usuario = obtenerusuarios(username)

        if usuario:
            if usuario["password"] == password:
                session["username"] = usuario["username"]
                session["rol"] = usuario["rol"]
                return redirect("/dashprincipal")
            else:
                return "Contraseña incorrecta"
        else:
            return "Usuario no existe"

    return render_template("login.html")


@app.route("/dashprincipal")
def dashprinci():
    if "username" not in session:
        return redirect("/")
    return render_template("dashprinci.html", usuario=session["username"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─────────────────────────────────────────────
#Validacion duplicado 
# ─────────────────────────────────────────────
def estudiante_existe(nombre, carrera):
    """Retorna True si ya existe un estudiante con ese nombre y carrera."""
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id FROM estudiantes WHERE Nombre = %s AND Carrera = %s",
        (nombre, carrera)
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None


@app.route("/registro_estudiante", methods=["GET", "POST"])
def registroestudiante():
    if "username" not in session:
        return redirect("/")

    if request.method == "POST":
        nombre   = request.form["txtnombre"]
        edad     = request.form["txtedad"]
        carrera  = request.form["txtcarrera"]
        notauno  = float(request.form["txtnota1"])
        notados  = float(request.form["txtnota2"])
        notatres = float(request.form["txtnota3"])

        
        if estudiante_existe(nombre, carrera):
            return render_template(
                "registro_estudiante.html",
                error=f"El estudiante '{nombre}' ya está registrado en '{carrera}'."
            )

        promedio  = round((notauno + notados + notatres) / 3, 2)
        desempeno = calculardesempeño(promedio)
        insertar_estudiante(nombre, edad, carrera, notauno, notados, notatres, promedio, desempeno)
        return redirect("/dashprincipal")

    return render_template("registro_estudiante.html")


# ─────────────────────────────────────────────────────────────────────────────
#  Carga masiva 
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/cargamasiva", methods=["GET", "POST"])
def carga_masiva():
    if "username" not in session:
        return redirect("/")

    if request.method == "POST":
        archivo = request.files["txtarchivo"]
        df_original = pd.read_excel(archivo)

        # ── Limpiar texto ──────────────────────────────────────────────────
        for col in ["Nombre", "Carrera"]:
            df_original[col] = df_original[col].astype(str).str.strip()
            df_original[col] = df_original[col].apply(quitar)
            df_original[col] = df_original[col].str.title()

        rechazados = []  # lista 

        def rechazar(row, motivo):
            r = row.to_dict()
            r["Motivo"] = motivo
            rechazados.append(r)

        # ── Validaciones fila por fila ─────────────────────────────────────
        validos = []
        for _, row in df_original.iterrows():

            # Datos faltantes
            if row[["Nombre", "Edad", "Carrera", "Nota1", "Nota2", "Nota3"]].isnull().any():
                rechazar(row, "Datos faltantes")
                continue

            # Edad negativa
            if row["Edad"] < 0:
                rechazar(row, "Edad negativa")
                continue

            # Notas inválidas
            notas_invalidas = any(
                not (0 <= row[n] <= 5) for n in ["Nota1", "Nota2", "Nota3"]
            )
            if notas_invalidas:
                rechazar(row, "Notas fuera de rango (0-5)")
                continue

            # Duplicado en BD
            if estudiante_existe(row["Nombre"], row["Carrera"]):
                rechazar(row, "Duplicado")
                continue

            # Duplicado dentro del mismo archivo
            if any(
                v["Nombre"] == row["Nombre"] and v["Carrera"] == row["Carrera"]
                for v in validos
            ):
                rechazar(row, "Duplicado en el archivo")
                continue

            validos.append(row)

        # ── Insertar válidos ───────────────────────────────────────────────
        conn   = conectar()
        cursor = conn.cursor()
        query  = """INSERT INTO estudiantes(Nombre,Edad,Carrera,nota1,nota2,nota3,Promedio,Desempeño)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""

        insertados = 0
        for row in validos:
            promedio  = round((row["Nota1"] + row["Nota2"] + row["Nota3"]) / 3, 2)
            desempeno = calculardesempeño(promedio)
            cursor.execute(query, (
                row["Nombre"], row["Edad"], row["Carrera"],
                row["Nota1"], row["Nota2"], row["Nota3"],
                promedio, desempeno
            ))
            insertados += 1

        conn.commit()
        conn.close()

        #  Excel de rechazados  
        duplicados_count = sum(1 for r in rechazados if "Duplicado" in r["Motivo"])
        session["rechazados"] = rechazados          # para descargar después

        #  Estadísticas del cargue 
        session["stats_cargue"] = {
            "insertados": insertados,
            "rechazados": len(rechazados),
            "duplicados": duplicados_count,
        }

        #  resetee filtros
        session["reset_filtros"] = True

        return redirect("/resultado_cargue")

    return render_template("carga_masiva.html")


@app.route("/resultado_cargue")
def resultado_cargue():
    """Muestra estadísticas y ofrece descargar el Excel de rechazados."""
    if "username" not in session:
        return redirect("/")

    stats     = session.pop("stats_cargue", {})
    rechazados = session.pop("rechazados", [])

    # Guardar temporalmente 
    session["rechazados_temp"] = rechazados

    return render_template("resultado_cargue.html", stats=stats, rechazados=rechazados)


@app.route("/descargar_rechazados")
def descargar_rechazados():
    """Genera y descarga el Excel con los registros rechazados."""
    rechazados = session.pop("rechazados_temp", [])

    if not rechazados:
        return "No hay registros rechazados.", 404

    df = pd.DataFrame(rechazados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rechazados")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="rechazados.xlsx"
    )


# ── Helpers ────────────────────────────────────────────────────────────────
def quitar(texto):
    if pd.isna(texto):
        return texto
    texto = str(texto)
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def calculardesempeño(prom):
    if prom >= 4.5:
        return "Excelente"
    elif prom >= 4:
        return "Bueno"
    elif prom >= 3:
        return "Regular"
    else:
        return "Bajo"


if __name__ == "__main__":
    app.run(debug=True)