import unicodedata

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mysqldb import MySQL

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuración de la Base de Datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'pizzeriasbd'

mysql = MySQL(app)

DIAS = {
    'domingo': 1, 'lunes': 2, 'martes': 3, 'miercoles': 4,
    'jueves': 5, 'viernes': 6, 'sabado': 7,
    'sunday': 1, 'monday': 2, 'tuesday': 3, 'wednesday': 4,
    'thursday': 5, 'friday': 6, 'saturday': 7,
}

MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10,
    'november': 11, 'december': 12,
}


def normalizar(texto):
    """Minúsculas y sin tildes: 'Sábado ' -> 'sabado'"""
    texto = unicodedata.normalize('NFD', str(texto).strip().lower())
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


# 1. Endpoint para Guardar el Pedido Completo
@app.route('/api/pedidos', methods=['POST'])
def crear_pedido():
    try:
        data = request.get_json()
        cursor = mysql.connection.cursor()

        cursor.execute(
            'INSERT INTO pedidos (nombre_cliente, direccion, telefono, total_pedido) VALUES (%s, %s, %s, %s)',
            (
                data['nombre_cliente'],
                data['direccion'],
                data['telefono'],
                data['total_pedido']
            )
        )

        pedido_id = cursor.lastrowid

        for item in data['detalles']:
            ingredientes_str = ", ".join(item['ingredientes']) if isinstance(item['ingredientes'], list) else item['ingredientes']

            cursor.execute(
                'INSERT INTO detalle_pedidos (pedido_id, tamano, ingredientes, num_pizzas, subtotal) VALUES (%s, %s, %s, %s, %s)',
                (
                    pedido_id,
                    item['tamano'],
                    ingredientes_str,
                    item['num_pizzas'],
                    item['subtotal']
                )
            )

        mysql.connection.commit()
        cursor.close()
        return jsonify({'mensaje': 'Pedido registrado con éxito', 'pedido_id': pedido_id, 'total': data['total_pedido']}), 201

    except Exception as e:
        print("ERROR EN PYTHON:", str(e))
        return jsonify({'error': str(e)}), 500


# 2. Endpoint para Consultar Ventas por Día (español o inglés, con o sin tilde)
@app.route('/api/ventas/dia', methods=['GET'])
def ventas_por_dia():
    try:
        dia = request.args.get('dia', '').strip()
        cursor = mysql.connection.cursor()

        if '-' in dia:  # fecha tipo 2026-11-07
            cursor.execute("""
                SELECT id, nombre_cliente, direccion, telefono, fecha_pedido, total_pedido
                FROM pedidos
                WHERE DATE(fecha_pedido) = %s
            """, (dia,))
        else:
            num_dia = DIAS.get(normalizar(dia))
            if num_dia is None:
                cursor.close()
                return jsonify({'error': 'Día no válido'}), 400
            cursor.execute("""
                SELECT id, nombre_cliente, direccion, telefono, fecha_pedido, total_pedido
                FROM pedidos
                WHERE DAYOFWEEK(fecha_pedido) = %s
            """, (num_dia,))

        rows = cursor.fetchall()

        ventas = []
        total_dia = 0
        for row in rows:
            ventas.append({
                'id': row[0],
                'nombre_cliente': row[1],
                'direccion': row[2],
                'telefono': row[3],
                'fecha_pedido': str(row[4]),
                'total_pedido': float(row[5]),
            })
            total_dia += float(row[5])

        cursor.close()
        return jsonify({'ventas': ventas, 'total_dia': total_dia})
    except Exception as e:
        print("ERROR EN VENTAS DIA:", str(e))
        return jsonify({'error': str(e)}), 500


# 3. Endpoint para Consultar Ventas por Mes (nombre o número)
@app.route('/api/ventas/mes', methods=['GET'])
def ventas_por_mes():
    try:
        mes = request.args.get('mes', '').strip()
        num_mes = int(mes) if mes.isdigit() else MESES.get(normalizar(mes))
        if num_mes is None:
            return jsonify({'error': 'Mes no válido'}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, nombre_cliente, direccion, telefono, fecha_pedido, total_pedido
            FROM pedidos
            WHERE MONTH(fecha_pedido) = %s
        """, (num_mes,))
        rows = cursor.fetchall()

        ventas = []
        total_mes = 0
        for row in rows:
            ventas.append({
                'id': row[0],
                'nombre_cliente': row[1],
                'direccion': row[2],
                'telefono': row[3],
                'fecha_pedido': str(row[4]),
                'total_pedido': float(row[5]),
            })
            total_mes += float(row[5])

        cursor.close()
        return jsonify({'ventas': ventas, 'total_mes': total_mes})
    except Exception as e:
        print("ERROR EN VENTAS MES:", str(e))
        return jsonify({'error': str(e)}), 500


# 4. Endpoint para ver el detalle (desglose de pizzas) de un pedido
@app.route('/api/pedidos/<int:pedido_id>/detalle', methods=['GET'])
def detalle_pedido(pedido_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT tamano, ingredientes, num_pizzas, subtotal
            FROM detalle_pedidos
            WHERE pedido_id = %s
        """, (pedido_id,))
        rows = cursor.fetchall()
        cursor.close()

        detalles = []
        for row in rows:
            detalles.append({
                'tamano': row[0],
                'ingredientes': row[1],
                'num_pizzas': row[2],
                'subtotal': float(row[3]),
            })
        return jsonify({'detalles': detalles})
    except Exception as e:
        print("ERROR EN DETALLE:", str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)