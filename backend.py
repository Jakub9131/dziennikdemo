from flask import Flask, request, jsonify
import psycopg2
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="dziennik",
        user="postgres",
        password="postgres"
    )

# -------- LOGOWANIE --------
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']

    if email == "admin@admin.pl" and password == "admin":
        return jsonify({"status": "ok", "rola": "admin", "id": 0})

    conn = connect_db()
    cur = conn.cursor()

    for table, role in [('uczniowie', 'uczen'), ('rodzice', 'rodzic'), ('nauczyciele', 'nauczyciel')]:
        cur.execute(f"SELECT id, haslo FROM {table} WHERE email = %s", (email,))
        row = cur.fetchone()
        if row and row[1] == password:
            return jsonify({"status": "ok", "rola": role, "id": row[0]})

    return jsonify({"status": "blad"})

# -------- PODSTAWOWE DANE --------
@app.route('/klasy_nauczyciela/<int:nauczyciel_id>')
def klasy_nauczyciela(nauczyciel_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT min_klasa, max_klasa FROM nauczyciele WHERE id = %s", (nauczyciel_id,))
    row = cur.fetchone()
    if not row:
        return jsonify([])
    min_klasa, max_klasa = row
    cur.execute("SELECT id, nazwa FROM klasy WHERE CAST(nazwa AS INTEGER) BETWEEN %s AND %s ORDER BY nazwa", (min_klasa, max_klasa))
    klasy = [{"id": r[0], "nazwa": r[1]} for r in cur.fetchall()]
    return jsonify(klasy)

@app.route('/klasy')
def wszystkie_klasy():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nazwa FROM klasy ORDER BY nazwa")
    return jsonify([{"id": r[0], "nazwa": r[1]} for r in cur.fetchall()])

@app.route('/uczniowie/<int:klasa_id>')
def uczniowie_z_klasy(klasa_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, imie, nazwisko FROM uczniowie WHERE klasa_id = %s ORDER BY nazwisko, imie", (klasa_id,))
    uczniowie = [{"id": r[0], "imie": r[1], "nazwisko": r[2]} for r in cur.fetchall()]
    return jsonify(uczniowie)

@app.route('/przedmioty')
def przedmioty():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nazwa FROM przedmioty ORDER BY nazwa;")
    return jsonify([{"id": r[0], "nazwa": r[1]} for r in cur.fetchall()])

# -------- OCENY --------
@app.route('/oceny/<int:uczen_id>')
def oceny_ucznia(uczen_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT oceny.id, przedmioty.nazwa, oceny.wartosc, oceny.kategoria
        FROM oceny
        JOIN przedmioty ON oceny.przedmiot_id = przedmioty.id
        WHERE oceny.uczen_id = %s
        ORDER BY przedmioty.nazwa;
    """, (uczen_id,))
    return jsonify([{"id": r[0], "przedmiot": r[1], "wartosc": r[2], "kategoria": r[3]} for r in cur.fetchall()])

@app.route('/dodaj_ocene', methods=['POST'])
def dodaj_ocene():
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO oceny (uczen_id, przedmiot_id, wartosc, kategoria, nauczyciel_id, data)
        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
    """, (
        data['uczen_id'],
        data['przedmiot_id'],
        data['wartosc'],
        data['kategoria'],
        data['nauczyciel_id']
    ))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/edytuj_ocene/<int:ocena_id>', methods=['PUT'])
def edytuj_ocene(ocena_id):
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE oceny SET wartosc = %s, kategoria = %s WHERE id = %s", (
        data['wartosc'], data['kategoria'], ocena_id
    ))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/usun_ocene/<int:ocena_id>', methods=['DELETE'])
def usun_ocene(ocena_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM oceny WHERE id = %s", (ocena_id,))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/oceny_rodzica/<int:rodzic_id>')
def oceny_rodzica(rodzic_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id, p.nazwa, o.wartosc, o.kategoria, n.imie, n.nazwisko
        FROM rodzice r
        JOIN uczniowie u ON r.uczen_id = u.id
        JOIN oceny o ON o.uczen_id = u.id
        JOIN przedmioty p ON o.przedmiot_id = p.id
        LEFT JOIN nauczyciele n ON o.nauczyciel_id = n.id
        WHERE r.id = %s
        ORDER BY p.nazwa;
    """, (rodzic_id,))
    dane = [{
        "id": r[0], "przedmiot": r[1], "wartosc": r[2], "kategoria": r[3],
        "nauczyciel": f"{r[4]} {r[5]}" if r[4] and r[5] else "Brak"
    } for r in cur.fetchall()]
    return jsonify(dane)

# -------- NAUCZYCIELE --------
@app.route('/nauczyciele')
def nauczyciele():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, imie, nazwisko, email, min_klasa, max_klasa FROM nauczyciele ORDER BY nazwisko, imie")
    return jsonify([{
        "id": r[0], "imie": r[1], "nazwisko": r[2], "email": r[3], "min_klasa": r[4], "max_klasa": r[5]
    } for r in cur.fetchall()])

@app.route('/nauczyciel/<int:id>')
def nauczyciel(id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, imie, nazwisko, email, min_klasa, max_klasa FROM nauczyciele WHERE id = %s", (id,))
    row = cur.fetchone()
    if row:
        return jsonify({
            "id": row[0], "imie": row[1], "nazwisko": row[2], "email": row[3],
            "min_klasa": row[4], "max_klasa": row[5]
        })
    return jsonify({})

# -------- ADMIN: ZARZĄDZANIE --------
@app.route('/admin/edytuj_ucznia/<int:id>', methods=['PUT'])
def edytuj_ucznia(id):
    data = request.json
    pole = data['pole']
    wartosc = data['wartosc']
    if pole not in ['imie', 'nazwisko', 'email', 'klasa_id']:
        return jsonify({"status": "blad"}), 400
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE uczniowie SET {pole} = %s WHERE id = %s", (wartosc, id))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/zmien_haslo_ucznia/<int:id>', methods=['PUT'])
def zmien_haslo_ucznia(id):
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE uczniowie SET haslo = %s WHERE id = %s", (data['haslo'], id))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/zmien_haslo_rodzica/<int:id>', methods=['PUT'])
def zmien_haslo_rodzica(id):
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE rodzice SET haslo = %s WHERE id = %s", (data['haslo'], id))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/edytuj_rodzica/<int:id>', methods=['PUT'])
def edytuj_rodzica(id):
    data = request.json
    pole = data['pole']
    wartosc = data['wartosc']
    if pole not in ['imie', 'nazwisko', 'email']:
        return jsonify({"status": "blad"}), 400
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE rodzice SET {pole} = %s WHERE id = %s", (wartosc, id))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/edytuj_nauczyciela/<int:id>', methods=['PUT'])
def edytuj_nauczyciela(id):
    data = request.json
    pole = data['pole']
    wartosc = data['wartosc']
    if pole not in ['imie', 'nazwisko', 'email', 'min_klasa', 'max_klasa']:
        return jsonify({"status": "blad"}), 400
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE nauczyciele SET {pole} = %s WHERE id = %s", (wartosc, id))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/usun_ucznia/<int:id>', methods=['DELETE'])
def admin_usun_ucznia(id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM rodzice WHERE uczen_id = %s", (id,))
    cur.execute("DELETE FROM oceny WHERE uczen_id = %s", (id,))
    cur.execute("DELETE FROM uczniowie WHERE id = %s", (id,))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/usun_nauczyciela/<int:id>', methods=['DELETE'])
def admin_usun_nauczyciela(id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM oceny WHERE nauczyciel_id = %s", (id,))
    cur.execute("DELETE FROM nauczyciele WHERE id = %s", (id,))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/dodaj_nauczyciela', methods=['POST'])
def admin_dodaj_nauczyciela():
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO nauczyciele (imie, nazwisko, email, haslo, min_klasa, max_klasa)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data['imie'], data['nazwisko'], data['email'], data['haslo'], data['min_klasa'], data['max_klasa']))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/dodaj_ucznia', methods=['POST'])
def admin_dodaj_ucznia():
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO uczniowie (imie, nazwisko, email, haslo, klasa_id)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (data['imie'], data['nazwisko'], data['email'], data['haslo'], data['klasa_id']))
    uczen_id = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO rodzice (imie, nazwisko, email, haslo, uczen_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (data['imie_rodzica'], data['nazwisko_rodzica'], data['email_rodzica'], data['haslo_rodzica'], uczen_id))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/uczen/<int:id>')
def pobierz_ucznia_z_rodzicem(id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.imie, u.nazwisko, u.email, u.klasa_id,
               r.id, r.imie, r.nazwisko, r.email
        FROM uczniowie u
        LEFT JOIN rodzice r ON r.uczen_id = u.id
        WHERE u.id = %s
    """, (id,))
    r = cur.fetchone()
    if r:
        return jsonify({
            "uczen_id": r[0],
            "imie_ucznia": r[1],
            "nazwisko_ucznia": r[2],
            "email_ucznia": r[3],
            "klasa": r[4],
            "rodzic_id": r[5],
            "imie_rodzica": r[6],
            "nazwisko_rodzica": r[7],
            "email_rodzica": r[8]
        })
    return jsonify({})

# ----------- RUN ----------- 
if __name__ == '__main__':
    app.run(port=5000)
