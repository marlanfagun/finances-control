from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Banco de dados SQLite
DB_NAME = 'financeiro.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS lancamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                data TEXT NOT NULL,
                status TEXT CHECK(status IN ('pendente','pago')) NOT NULL,
                tipo TEXT CHECK(tipo IN ('entrada','saida')) NOT NULL,
                parcelas INTEGER DEFAULT 1
            )
        ''')
        conn.commit()

init_db()

def listar_lancamentos(mes_ano):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if mes_ano:
            try:
                data_ini = datetime.strptime(mes_ano, "%Y-%m").strftime("%Y-%m-01")
                if int(mes_ano[5:]) == 12:
                    data_fim = datetime.strptime(mes_ano, "%Y-%m").replace(year=int(mes_ano[:4])+1, month=1, day=1).strftime("%Y-%m-%d")
                else:
                    data_fim = datetime.strptime(mes_ano, "%Y-%m").replace(month=int(mes_ano[5:])+1, day=1).strftime("%Y-%m-%d")
                c.execute("SELECT * FROM lancamentos WHERE data >= ? AND data < ? ORDER BY data DESC", (data_ini, data_fim))
            except:
                c.execute("SELECT * FROM lancamentos ORDER BY data DESC")
        else:
            c.execute("SELECT * FROM lancamentos ORDER BY data DESC")
        return c.fetchall()


def resumo_valores(lancamentos):
    entradas = sum(l[2] for l in lancamentos if l[5] == 'entrada')
    saidas = sum(l[2] for l in lancamentos if l[5] == 'saida')
    return entradas, saidas, entradas - saidas

def meses_disponiveis():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT strftime('%m/%Y', data) as mes FROM lancamentos ORDER BY mes DESC")
        meses = c.fetchall()
        return [datetime.strptime(m[0], "%m/%Y").strftime("%b/%y") for m in meses]
    
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value

@app.route('/', methods=['GET'])
def index():
    mes = request.args.get('mes')

    # Se não houver mês informado na URL, redireciona para o mês atual
    if not mes:
        mes_atual = datetime.today().strftime("%Y-%m")
        return redirect(f"/?mes={mes_atual}")

    lancamentos = listar_lancamentos(mes)
    entradas, saidas, saldo = resumo_valores(lancamentos)
    meses = meses_disponiveis()    
    mes_atual_input = mes or datetime.today().strftime("%Y-%m")
    return render_template('index.html', lancamentos=lancamentos, entradas=entradas, saidas=saidas,
                           saldo=saldo, meses=meses, mes_atual_input=mes_atual_input)

@app.route('/salvar', methods=['POST'])
def salvar():
    id = request.form.get('id')
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    data = request.form['data']
    status = request.form['status']
    tipo = request.form['tipo']
    parcelas = int(request.form['parcelas'])
    mes_atual = request.form.get('mes_atual')

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if id:
            c.execute('''UPDATE lancamentos SET descricao=?, valor=?, data=?, status=?, tipo=?, parcelas=? WHERE id=?''',
                      (descricao, valor, data, status, tipo, parcelas, id))
        elif parcelas > 1:
            for i in range(parcelas):
                desc_parcela = f"{descricao} ({i+1}/{parcelas})"
                data_parcela = datetime.strptime(data, "%Y-%m-%d") + relativedelta(months=i)
                data_lanc = data_parcela.strftime("%Y-%m-%d")
                c.execute("INSERT INTO lancamentos (descricao, valor, data, status, tipo, parcelas) VALUES (?, ?, ?, ?, ?, ?)",
                (desc_parcela, valor, data_lanc, status, tipo, 1))
        else:
            c.execute("INSERT INTO lancamentos (descricao, valor, data, status, tipo, parcelas) VALUES (?, ?, ?, ?, ?, ?)",
                      (descricao, valor, data, status, tipo, 1))
        conn.commit()
    return redirect(f"/?mes={mes_atual}" if mes_atual else "/")

if __name__ == '__main__':
    app.run(debug=True)
