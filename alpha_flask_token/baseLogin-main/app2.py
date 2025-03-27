# importa tutte le librerie necessarie
from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from AlphaBot import AlphaBot

# inizializzazione dell'app flask
app = Flask(__name__)
# definisce una chiave segreta per proteggere le sessioni dell'app
app.secret_key = "chiave_segreta"

# creazione dell'istanza di AlphaBot per controllare il robot
bot = AlphaBot()

# funzione per inizializzare il database utenti
def init_db():
    db_path = "users.db"  # definisce il percorso del database

    try:
        # connessione al database SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # crea una tabella 'users' se non esiste già
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        # salva le modifiche al database
        conn.commit()
        conn.close()
        print("Database inizializzato con successo")
        return True
    
    except Exception as e:
        # se c'è un errore nella connessione o nell'esecuzione, lo cattura e lo stampa
        print(f"Errore nell'inizializzazione del database: {e}")
        return False

# funzione che ferma il robot quando l'app viene avviata
def stop_bot():
    bot.stop()  # invoca il metodo 'stop' del bot per fermarlo

# gestione della pagina di login
@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":  # se il metodo è POST (invio dei dati del login)
        username = request.form.get("e-mail")  # ottieni il nome utente
        password = request.form.get("password")  # ottieni la password

        try:
            # connessione al database per verificare le credenziali
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()  # recupera l'utente corrispondente al nome utente
            conn.close()

            # se l'utente esiste e la password è corretta, login riuscito
            if user and check_password_hash(user[2], password):  
                print(f"Login riuscito per l'utente: {username}")
                response = make_response(redirect(url_for("telecomando")))  # redirige alla route telecomando
                response.set_cookie("username", username, max_age=60*60*24)  # imposta un cookie con il nome utente per la sessione
                return response
            else:
                # se la password non è corretta, restituisci un messaggio di errore
                print(f"Tentativo di login fallito per l'utente: {username}")
                return render_template("login.html", error="Credenziali errate o utente inesistente!")
        except Exception as e:
            # in caso di errore nel processo, restituisci un messaggio di errore
            print(f"Errore durante il login: {e}")
            return render_template("login.html", error=f"Errore di sistema: {e}")

    # se il metodo è GET, restituisce la pagina di login
    return render_template("login.html", error="")

# gestione della creazione di un nuovo account
@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        # ottieni l'e-mail e la password dal modulo di creazione account
        username = request.form.get("e-mail")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")  # cripta la password

        try:
            # verifica se l'utente esiste già nel database
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()  # controlla se l'utente esiste già
            if user:
                conn.close()
                print(f"Utente {username} già esistente nel database")
                return render_template("login.html", error="Email già registrata! Effettua il login.")

            # se l'utente non esiste, inserisci il nuovo utente nel database
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            print(f"Nuovo utente registrato: {username}")
            
            conn.close()
            
            return redirect(url_for("login"))  # reindirizza alla pagina di login
        except Exception as e:
            # gestione degli errori durante la registrazione
            print(f"Errore durante la registrazione dell'utente {username}: {e}")
            return render_template("create_account.html", error=f"Errore durante la registrazione: {e}")

    # se il metodo è GET, restituisce la pagina di creazione dell'account
    return render_template("create_account.html")

# gestione del logout
@app.route("/logout")
def logout():
    username = request.cookies.get("username")  # ottieni il nome utente dal cookie
    print(f"Logout utente: {username}")
    response = make_response(redirect(url_for("login")))  # redirige alla pagina di login
    response.delete_cookie("username")  # cancella il cookie dell'utente
    return response

# protezione dell'accesso al telecomando: solo utenti loggati possono accedere
@app.route("/telecomando")
def telecomando():
    username = request.cookies.get("username")  # ottieni il nome utente dal cookie
    if not username:  # se l'utente non è loggato
        print("Tentativo di accesso al telecomando senza autorizzazione")
        return redirect(url_for("login"))  # reindirizza alla pagina di login
    
    print(f"Accesso al telecomando da parte dell'utente: {username}")
    return render_template("telecomando.html", username=username)  # restituisce la pagina del telecomando

# endpoint per inviare comandi ad alphabot
@app.route("/comando", methods=["POST"])
def comando():
    username = request.cookies.get("username")  # ottieni il nome utente dal cookie
    if not username:  # se l'utente non è loggato
        print("Tentativo di inviare comandi senza autorizzazione")
        return jsonify({"status": "errore", "messaggio": "Accesso negato"}), 403  # ritorna un errore 403

    # leggi i dati inviati dal client (il comando per il bot)
    data = request.get_json()
    comando = data.get('comando')  # ottieni il comando

    print(f"Comando ricevuto: {comando} da {username}")

    # esegui il comando su alphabot
    if comando == "avanti":
        bot.forward()  # sposta il bot avanti
    elif comando == "indietro":
        bot.backward()  # sposta il bot indietro
    elif comando == "sinistra":
        bot.left()  # gira il bot a sinistra
    elif comando == "destra":
        bot.right()  # gira il bot a destra
    elif comando == "stop":
        bot.stop()  # ferma il bot
    else:
        print(f"Comando non valido: {comando}")
        return jsonify({"status": "errore", "messaggio": "Comando non valido"}), 400  # errore se il comando non è valido

    # ritorna una risposta JSON con lo stato del comando
    return jsonify({"status": "ok", "messaggio": f"Comando {comando} eseguito"})

# avvio dell'app flask con inizializzazione del database e fermata iniziale del bot
if __name__ == "__main__":
    stop_bot()  # fermiamo il bot appena si avvia l'app
    init_db()  # inizializza il database
    app.run(debug=True, host="0.0.0.0", port=4444)  # avvia l'app Flask in modalità debug