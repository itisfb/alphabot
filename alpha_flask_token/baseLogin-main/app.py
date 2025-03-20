from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from AlphaBot import AlphaBot

# inizializzazione dell'app flask
app = Flask(__name__)
app.secret_key = "chiave_segreta"

# creazione dell'istanza di alphabot
bot = AlphaBot()

# funzione per inizializzare il database utenti
def init_db():
    
    db_path = "users.db"
    
    try:
        # connessione al database sqlite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        print("Database inizializzato con successo")
        return True
    
    except Exception as e:
        print(f"Errore nell'inizializzazione del database: {e}")
        return False

# funzione per fermare alphabot all'avvio dell'applicazione
def stop_bot():
    bot.stop()

# gestione della pagina di login
@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("e-mail")
        password = request.form.get("password")

        try:
            # connessione al database per verificare le credenziali
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            conn.close()

            # verifica della password e gestione della sessione
            if user and check_password_hash(user[2], password):  
                print(f"Login riuscito per l'utente: {username}")
                response = make_response(redirect(url_for("telecomando.html")))
                response.set_cookie("username", username, max_age=60*60*24)
                return response
            else:
                print(f"Tentativo di login fallito per l'utente: {username}")
                return render_template("login.html", error="Credenziali errate o utente inesistente!")
        except Exception as e:
            print(f"Errore durante il login: {e}")
            return render_template("login.html", error=f"Errore di sistema: {e}")

    return render_template("login.html", error="")

# gestione della creazione di un nuovo account
@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        username = request.form.get("e-mail")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        try:
            # verifica se l'utente esiste già nel database
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if user:
                conn.close()
                print(f"Utente {username} già esistente nel database")
                return render_template("login.html", error="Email già registrata! Effettua il login.")

            # inserimento del nuovo utente
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            print(f"Nuovo utente registrato: {username}")
            
            conn.close()
            
            return redirect(url_for("login.html"))
        except Exception as e:
            print(f"Errore durante la registrazione dell'utente {username}: {e}")
            return render_template("create_account.html", error=f"Errore durante la registrazione: {e}")

    return render_template("create_account.html")

# gestione del logout
@app.route("/logout")
def logout():
    username = request.cookies.get("username")
    print(f"Logout utente: {username}")
    response = make_response(redirect(url_for("login.html")))
    response.delete_cookie("username")
    return response

# protezione dell'accesso al telecomando: solo utenti loggati possono accedere
@app.route("/telecomando", methods=["GET"])
def telecomando():
    username = request.cookies.get("username")
    if not username:
        print("Tentativo di accesso al telecomando senza autorizzazione")
        return redirect(url_for("login.html"))
    
    print(f"Accesso al telecomando da parte dell'utente: {username}")
    return render_template("telecomando.html", username=username)

# endpoint per inviare comandi ad alphabot
@app.route("/comando", methods=["POST"])
def comando():
    username = request.cookies.get("username")
    if not username:
        print("Tentativo di inviare comandi senza autorizzazione")
        return jsonify({"status": "errore", "messaggio": "Accesso negato"}), 403

    # lettura del comando inviato dal client
    data = request.get_json()
    comando = data.get('comando')

    print(f"Comando ricevuto: {comando} da {username}")

    # esecuzione del comando su alphabot
    if comando == "avanti":
        bot.forward()
    elif comando == "indietro":
        bot.backward()
    elif comando == "sinistra":
        bot.left()
    elif comando == "destra":
        bot.right()
    elif comando == "stop":
        bot.stop()
    else:
        print(f"Comando non valido: {comando}")
        return jsonify({"status": "errore", "messaggio": "Comando non valido"}), 400

    return jsonify({"status": "ok", "messaggio": f"Comando {comando} eseguito"})

# avvio dell'app flask con inizializzazione del database e fermata iniziale del bot
if __name__ == "__main__":
    stop_bot()  # fermiamo il bot appena si avvia l'app
    init_db()
    app.run(debug=True, host="0.0.0.0", port=4444)
