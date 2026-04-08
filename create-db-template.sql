CREATE DATABASE trabajo
DEFAULT CHARACTER SET = 'utf8mb4';
USE trabajo;

-- Tabla de usuarios (para el login)
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    rol VARCHAR(50) NOT NULL
);

-- Tabla de estudiantes
CREATE TABLE estudiantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(150) NOT NULL,
    Edad INT NOT NULL,
    Carrera VARCHAR(150) NOT NULL,
    nota1 FLOAT NOT NULL,
    nota2 FLOAT NOT NULL,
    nota3 FLOAT NOT NULL,
    Promedio FLOAT NOT NULL,
    Desempeño VARCHAR(50) NOT NULL
);
-- Usuario administrador
INSERT INTO usuarios (username, password, rol) VALUES ('admin', 'admin123', 'administrador');

-- Usuario normal
INSERT INTO usuarios (username, password, rol) VALUES ('usuario1', 'user123', 'usuario');

DROP DATABASE Trabajo;