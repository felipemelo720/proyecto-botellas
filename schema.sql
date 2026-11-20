CREATE TABLE IF NOT EXISTS locales (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS productos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  categoria VARCHAR(80) NOT NULL,
  local_id INT NOT NULL,
  stock INT NOT NULL DEFAULT 0,
  stock_minimo INT NOT NULL DEFAULT 0,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT chk_producto_stock CHECK (stock >= 0),
  CONSTRAINT chk_producto_minimo CHECK (stock_minimo >= 0),
  CONSTRAINT fk_producto_local FOREIGN KEY (local_id) REFERENCES locales (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimientos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  producto_id INT NOT NULL,
  local_id INT NOT NULL,
  tipo ENUM('entrada', 'salida') NOT NULL,
  cantidad INT NOT NULL,
  fecha DATE NOT NULL,
  CONSTRAINT chk_movimiento_cantidad CHECK (cantidad > 0),
  CONSTRAINT fk_movimiento_producto FOREIGN KEY (producto_id) REFERENCES productos (id),
  CONSTRAINT fk_movimiento_local FOREIGN KEY (local_id) REFERENCES locales (id)
) ENGINE=InnoDB;

INSERT IGNORE INTO locales (nombre) VALUES ('Osorno'), ('Temuco'), ('Valdivia');
