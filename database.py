import mysql.connector
import pandas as pd

def conectar():
    conexion = mysql.connector.connect(
        host="localhost",
        user = "root",
        password = "",
        database = "Trabajo"
    )
    return conexion

#obtener usuarios
def  obtenerusuarios(username):
     #conectar a la base bd
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        #buscar el usuario en la bd
        cursor.execute("SELECT * FROM usuarios WHERE username=%s",(username,))
        usuario = cursor.fetchone()
        conn.close()
        return usuario
#obtener los estudiantes
def  obtenerestudiantes():
     conn = conectar()
     query = "SELECT * FROM estudiantes"
     df = pd.read_sql(query,conn)
     conn.close()

     return df

#registrar estudiante 
def insertar_estudiante(nombre,edad,carrera,nota1,nota2,nota3,promedio,desempeno):
     coon = conectar()
     cursor = coon.cursor()

     query = """INSERT INTO estudiantes(Nombre,Edad,Carrera,nota1,nota2,nota3,Promedio,Desempeño)values(%s,%s,%s,%s,%s,%s,%s,%s)"""
     cursor.execute(query,(nombre,edad,carrera,nota1,nota2,nota3,promedio,desempeno))
     
     coon.commit()
     coon.close()


if __name__ == "__main__":
    coon = conectar()
    print("Conexion exitosa")
    coon.close()