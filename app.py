from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
import sqlite3
import os
from datetime import datetime
import smtplib
from email.message import EmailMessage
import ssl
from dotenv import load_dotenv
import urllib.request
import certifi

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__, template_folder='.')
app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui_123456')

# Configurações do banco de dados
DATABASE = 'banco.db'

def get_db_connection():
    """Conecta ao banco de dados existente"""
    if not os.path.exists(DATABASE):
        raise FileNotFoundError(f"Banco de dados '{DATABASE}' não encontrado!")
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def verificar_banco_dados():
    """
    Verifica se o banco de dados existe e mostra informações detalhadas
    """
    print("=" * 60)
    print("VERIFICAÇÃO DO BANCO DE DADOS")
    print("=" * 60)
    
    if os.path.exists(DATABASE):
        tamanho = os.path.getsize(DATABASE) / 1024  # Tamanho em KB
        print(f"✅ Banco de dados encontrado: {DATABASE}")
        print(f"📏 Tamanho: {tamanho:.2f} KB")
        
        # Verificar tabelas existentes
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Listar todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tabelas = cursor.fetchall()
            
            if tabelas:
                print("📋 Tabelas encontradas:")
                for tabela in tabelas:
                    tabela_nome = tabela[0]
                    # Contar registros em cada tabela
                    try:
                        cursor.execute(f"SELECT COUNT(*) as total FROM [{tabela_nome}]")
                        total = cursor.fetchone()[0]
                        
                        # Mostrar estrutura da tabela
                        cursor.execute(f"PRAGMA table_info([{tabela_nome}])")
                        colunas = cursor.fetchall()
                        
                        print(f"   • {tabela_nome}: {total} registros")
                        
                        # Para tabela de usuários, mostrar alguns registros
                        if tabela_nome == 'usuarios' and total > 0:
                            print(f"     📝 Exibindo {min(5, total)} usuários:")
                            cursor.execute(f"SELECT id, nome, email FROM [{tabela_nome}] LIMIT 5")
                            usuarios = cursor.fetchall()
                            for usuario in usuarios:
                                print(f"       - ID: {usuario[0]}, Nome: {usuario[1]}, Email: {usuario[2]}")
                        
                    except Exception as e:
                        print(f"   • {tabela_nome}: erro ao acessar - {str(e)}")
            else:
                print("⚠️ Nenhuma tabela encontrada no banco de dados")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Erro ao verificar tabelas: {str(e)}")
        
    else:
        print(f"❌ Banco de dados '{DATABASE}' NÃO ENCONTRADO!")
        print("\n⚠️ Você precisa:")
        print("   1. Copiar o arquivo 'banco.db' do seu outro PC")
        print("   2. Colocar na mesma pasta deste script")
        print("   3. Reiniciar o sistema")
        
        resposta = input("\nDeseja criar um novo banco de dados vazio? (s/n): ").strip().lower()
        
        if resposta == 's':
            criar_banco_vazio()
        else:
            print("\n⚠️ ATENÇÃO: Sistema continuará sem banco de dados.")
            print("   Login não funcionará até você colocar o banco.db")
            print("   Você pode colocar o banco de dados depois e reiniciar.")
    
    print("=" * 60)

def criar_banco_vazio():
    """Cria um banco de dados vazio apenas se o usuário permitir"""
    print(f"\nCriando banco de dados vazio '{DATABASE}'...")
    
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Tabela de usuários
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de clientes
        conn.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                usuario_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Tabela de serviços
        conn.execute('''    
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                imagem TEXT,
                usuario_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Tabela de agendamentos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                servico_id INTEGER,
                data_agendamento DATE NOT NULL,
                hora_agendamento TIME NOT NULL,
                status TEXT DEFAULT 'pendente',
                usuario_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                FOREIGN KEY (servico_id) REFERENCES servicos (id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Adicionar usuário padrão
        conn.execute(
            'INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)',
            ('Administrador', 'admin@exemplo.com', '123456')
        )
        
        conn.commit()
        conn.close()
        
        print("✅ Banco de dados vazio criado com sucesso!")
        print("📋 Dados iniciais:")
        print("   • Usuário: admin@exemplo.com")
        print("   • Senha: 123456")
        print("\n⚠️ Você precisará:")
        print("   1. Fazer login com as credenciais acima")
        print("   2. Adicionar serviços e clientes manualmente")
        
    except Exception as e:
        print(f"❌ Erro ao criar banco de dados: {str(e)}")

# Verificar banco de dados ao iniciar
verificar_banco_dados()

# =====================
# FUNÇÃO DE ENVIO DE EMAIL COM CREDENCIAIS CORRETAS
# =====================

def enviar_email_gmail(cliente_email, cliente_nome, servico_nome, data_agendamento, hora_agendamento, status):
    """
    Envia email de notificação de agendamento usando Gmail
    """
    try:
        # CONFIGURAÇÃO DO EMAIL - CREDENCIAIS INSERIDAS DIRETAMENTE
        SEU_EMAIL = 'agendamentomais.suporte1@gmail.com'
        SENHA_APP = 'dvno ipft lbds dpzg'
        
        print(f"🔧 Configuração de email:")
        print(f"   Email: {SEU_EMAIL}")
        print(f"   Senha de app: {SENHA_APP}")
        
        if not cliente_email:
            print(f"⚠️ Cliente {cliente_nome} não tem email cadastrado")
            return False, "Cliente sem email"
        
        if "@" not in cliente_email or "." not in cliente_email:
            print(f"⚠️ Email inválido: {cliente_email}")
            return False, "Email inválido"
        
        # Converter data para formato brasileiro
        try:
            data_obj = datetime.strptime(data_agendamento, '%Y-%m-%d')
            data_formatada = data_obj.strftime('%d/%m/%Y')
        except:
            data_formatada = data_agendamento
        
        print(f"📧 Preparando email para: {cliente_email}")
        print(f"📤 Status: {status}")
        
        # Criar mensagem
        msg = EmailMessage()
        
        # Definir assunto baseado no status
        if status == 'pendente':
            msg['Subject'] = f'Confirmação de Agendamento - {servico_nome}'
        else:
            msg['Subject'] = f'Atualização do Agendamento - {servico_nome}'
        
        msg['From'] = f'Agendamento+ <{SEU_EMAIL}>'
        msg['To'] = cliente_email
        
        # Mensagens personalizadas por status
        if status == 'pendente':
            mensagem_titulo = "Aguardando Confirmação"
            mensagem_corpo = f"""
            <p>Seu agendamento está <strong>PENDENTE</strong>. Entre em contato conosco para confirmar.</p>
            <p><strong>Urgente:</strong> Precisamos da sua confirmação para garantir seu horário.</p>
            """
            cor_status = '#ffc107'
            cor_texto = '#212529'
            
        elif status == 'confirmado':
            mensagem_titulo = "Agendamento Confirmado!"
            mensagem_corpo = f"""
            <p>Seu agendamento foi <strong>CONFIRMADO</strong>. Estamos esperando por você!</p>
            <p><strong>Importante:</strong> Chegue com 10 minutos de antecedência.</p>
            """
            cor_status = '#17a2b8'
            cor_texto = 'white'
            
        elif status == 'realizado':
            mensagem_titulo = "Agendamento Realizado"
            mensagem_corpo = f"""
            <p>Seu agendamento foi <strong>REALIZADO</strong> com sucesso!</p>
            <p><strong>Obrigado por confiar em nós!</strong> Esperamos ter atendido suas expectativas.</p>
            """
            cor_status = '#28a745'
            cor_texto = 'white'
            
        elif status == 'cancelado':
            mensagem_titulo = "Agendamento Cancelado"
            mensagem_corpo = f"""
            <p>Seu agendamento foi <strong>CANCELADO</strong>.</p>
            <p>Entre em contato conosco para mais informações ou para reagendar.</p>
            """
            cor_status = '#dc3545'
            cor_texto = 'white'
        else:
            mensagem_titulo = "Atualização do Agendamento"
            mensagem_corpo = f"<p>Seu agendamento foi atualizado para: <strong>{status.upper()}</strong></p>"
            cor_status = '#6c757d'
            cor_texto = 'white'
        
        # HTML do email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agendamento+ - Atualização</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .logo {{
            font-size: 28px;
            font-weight: 700;
            margin: 0;
        }}
        
        .logo span {{
            color: #ffd700;
        }}
        
        .tagline {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .status-badge {{
            background: {cor_status};
            color: {cor_texto};
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: 600;
            display: inline-block;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #007bff;
        }}
        
        .info-item {{
            display: flex;
            margin: 10px 0;
            padding: 5px 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }}
        
        .info-label {{
            font-weight: 600;
            min-width: 120px;
            color: #343a40;
        }}
        
        .info-value {{
            color: #555;
        }}
        
        .message-box {{
            background: rgba(0, 123, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid #007bff;
        }}
        
        .contact-section {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 10px;
        }}
        
        .contact-buttons {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 20px;
        }}
        
        .contact-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: white;
            border-radius: 8px;
            text-decoration: none;
            color: #343a40;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .contact-btn.instagram {{
            border: 2px solid #E4405F;
            color: #E4405F;
        }}
        
        .contact-btn.whatsapp {{
            border: 2px solid #25D366;
            color: #25D366;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #eee;
            background: #f8f9fa;
        }}
        
        @media (max-width: 600px) {{
            .container {{
                margin: 10px;
            }}
            
            .contact-buttons {{
                flex-direction: column;
                align-items: center;
            }}
            
            .contact-btn {{
                width: 100%;
                max-width: 250px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Agendamento<span>+</span></div>
            <p class="tagline">Sistema de Agendamento Online Profissional</p>
        </div>
        
        <div class="content">
            <div class="status-badge">
                {status.upper()}
            </div>
            
            <h2 style="color: #343a40; margin-top: 0;">Olá, {cliente_nome}!</h2>
            <p style="color: #666;">Seu agendamento foi atualizado:</p>
            
            <div class="message-box">
                <h3 style="margin-top: 0; color: #007bff;">{mensagem_titulo}</h3>
                {mensagem_corpo}
            </div>
            
            <div class="info-card">
                <div class="info-item">
                    <span class="info-label">Serviço:</span>
                    <span class="info-value">{servico_nome}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Data:</span>
                    <span class="info-value">{data_formatada}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Hora:</span>
                    <span class="info-value">{hora_agendamento}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Status:</span>
                    <span class="info-value" style="color: {cor_status}; font-weight: 600;">{status.upper()}</span>
                </div>
            </div>
            
            <div class="contact-section">
                <p style="margin-bottom: 15px; color: #666;">Em caso de dúvidas, entre em contato conosco:</p>
                
                <div class="contact-buttons">
                    <a href="https://www.instagram.com/agendamentomais/" target="_blank" class="contact-btn instagram">
                        <i class="fab fa-instagram"></i>
                        <span>Instagram</span>
                    </a>
                    <a href="https://wa.me/5561985825956" target="_blank" class="contact-btn whatsapp">
                        <i class="fab fa-whatsapp"></i>
                        <span>WhatsApp</span>
                    </a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p style="margin: 0 0 10px 0; font-weight: 600;">© 2025 Agendamento+. Todos os direitos reservados.</p>
            <p style="margin: 0; color: #999;">
                Esta é uma mensagem automática do sistema Agendamento+.
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        # Versão texto simples
        if status == 'pendente':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento está PENDENTE de confirmação.

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

URGENTE: Entre em contato conosco para confirmar seu horário.

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        elif status == 'confirmado':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi CONFIRMADO!

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

Importante: Chegue com 10 minutos de antecedência.

Estamos esperando por você!

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        elif status == 'realizado':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi marcado como REALIZADO!

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

Obrigado por confiar em nós!

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        elif status == 'cancelado':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi CANCELADO.

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

Entre em contato conosco para mais informações.

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        else:
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi atualizado.

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}
Status: {status.upper()}

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        # Adicionar conteúdo
        msg.set_content(mensagem_texto)
        msg.add_alternative(html, subtype='html')
        
        # TENTATIVA 1: Usar SMTP com TLS (porta 587) - Método mais confiável
        try:
            print("🔄 Tentando conexão SMTP com TLS (porta 587)...")
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()  # Identifica-se com o servidor
            server.starttls()  # Habilita criptografia TLS
            server.ehlo()  # Re-identifica-se após TLS
            
            print(f"📤 Conectando como: {SEU_EMAIL}")
            server.login(SEU_EMAIL, SENHA_APP)
            print("✅ Login bem-sucedido!")
            
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email enviado com sucesso para {cliente_email}")
            return True, "Email enviado com sucesso"
            
        except Exception as e1:
            print(f"❌ Tentativa 1 (TLS) falhou: {str(e1)}")
            
            # TENTATIVA 2: Usar SMTP_SSL (porta 465)
            try:
                print("🔄 Tentando conexão SMTP_SSL (porta 465)...")
                # Criar contexto SSL com certificados do sistema
                context = ssl.create_default_context(cafile=certifi.where())
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                    server.login(SEU_EMAIL, SENHA_APP)
                    server.send_message(msg)
                
                print(f"✅ Email enviado com sucesso (SSL) para {cliente_email}")
                return True, "Email enviado com sucesso via SSL"
                
            except Exception as e2:
                print(f"❌ Tentativa 2 (SSL) falhou: {str(e2)}")
                
                # Resumo dos erros
                mensagem_erro = f"""
                ⚠️ FALHA NO ENVIO DE EMAIL ⚠️
                
                Erros encontrados:
                1. TLS (587): {str(e1)}
                2. SSL (465): {str(e2)}
                
                SOLUÇÕES:
                1. Verifique se as credenciais estão corretas:
                   - Email: {SEU_EMAIL}
                
                2. Verifique se a senha de app está correta
                
                3. Ative o acesso de apps menos seguros (apenas para testes):
                   Acesse: https://myaccount.google.com/lesssecureapps
                
                Dados da mensagem:
                - Para: {cliente_email}
                - Cliente: {cliente_nome}
                - Serviço: {servico_nome}
                - Status: {status}
                """
                print(mensagem_erro)
                return False, f"Erro no envio de email. Verifique suas credenciais do Gmail."
        
    except smtplib.SMTPAuthenticationError as e:
        erro_msg = str(e)
        print(f"❌ ERRO DE AUTENTICAÇÃO: {erro_msg}")
        
        if "Username and Password not accepted" in erro_msg:
            print("📋 PROBLEMA: Email ou senha incorretos")
            print("   Solução: Verifique as credenciais fornecidas")
        elif "Application-specific password required" in erro_msg:
            print("📋 PROBLEMA: Precisa de senha de app")
            print("   Solução: Use uma senha de app válida do Gmail")
        else:
            print("📋 PROBLEMA: Autenticação falhou")
        
        return False, "Erro de autenticação. Verifique email e senha de app."
        
    except Exception as e:
        print(f"❌ Erro geral ao enviar email: {str(e)}")
        return False, f"Erro: {str(e)}"

# =====================
# ROTAS PRINCIPAIS
# =====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro')
def cadastro_page():
    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/servicos')
def servicos():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('servicos.html')

@app.route('/clientes')
def clientes():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('clientes.html')

@app.route('/agendamentos')
def agendamentos():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('agendamentos.html')

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('perfil.html')

# =====================
# API - AUTENTICAÇÃO (COM DEBUG)
# =====================

@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    try:
        # Verificar se o banco existe antes de tentar usar
        if not os.path.exists(DATABASE):
            return jsonify({'success': False, 'message': 'Banco de dados não encontrado! Coloque o arquivo banco.db na pasta do sistema.'})
        
        data = request.get_json()
        nome = data.get('nome')
        email = data.get('email')
        senha = data.get('senha')
        
        if not nome or not email or not senha:
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
        
        conn = get_db_connection()
        
        # Verificar se email já existe
        usuario_existente = conn.execute(
            'SELECT id, nome, email FROM usuarios WHERE email = ?', (email,)
        ).fetchone()
        
        if usuario_existente:
            conn.close()
            print(f"⚠️ Tentativa de cadastro com email já existente: {email}")
            print(f"   ID: {usuario_existente['id']}, Nome: {usuario_existente['nome']}")
            return jsonify({'success': False, 'message': 'Email já cadastrado'})
        
        # Inserir novo usuário
        conn.execute(
            'INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)',
            (nome, email, senha)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Novo usuário cadastrado: {nome} ({email})")
        return jsonify({'success': True, 'message': 'Cadastro realizado com sucesso!'})
    
    except FileNotFoundError:
        return jsonify({'success': False, 'message': f'Banco de dados {DATABASE} não encontrado!'})
    except Exception as e:
        print(f"❌ Erro no cadastro: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no servidor: {str(e)}'})

@app.route('/api/login', methods=['POST'])
def login():
    try:
        # Verificar se o banco existe antes de tentar usar
        if not os.path.exists(DATABASE):
            return jsonify({'success': False, 'message': 'Banco de dados não encontrado! Coloque o arquivo banco.db na pasta do sistema.'})
        
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        print(f"🔐 Tentativa de login: {email}")
        
        # Verificar se a tabela usuarios existe
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        tabela_existe = cursor.fetchone()
        
        if not tabela_existe:
            conn.close()
            print("❌ Tabela 'usuarios' não encontrada no banco!")
            return jsonify({'success': False, 'message': 'Estrutura do banco de dados incompleta'})
        
        # Verificar colunas da tabela
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = cursor.fetchall()
        print(f"📋 Colunas da tabela usuarios: {[col[1] for col in colunas]}")
        
        # Buscar usuário
        usuario = conn.execute(
            'SELECT id, nome, email, senha FROM usuarios WHERE email = ?', (email,)
        ).fetchone()
        
        conn.close()
        
        if usuario:
            print(f"✅ Usuário encontrado: {usuario['nome']} ({usuario['email']})")
            print(f"   Senha no banco: {usuario['senha']}")
            print(f"   Senha fornecida: {senha}")
            
            # Comparação simples (sem hash para debug)
            if usuario['senha'] == senha:
                session['usuario_id'] = usuario['id']
                session['usuario_nome'] = usuario['nome']
                session['usuario_email'] = usuario['email']
                
                print(f"✅ Login bem-sucedido para: {usuario['nome']}")
                return jsonify({'success': True, 'message': 'Login realizado com sucesso!'})
            else:
                print("❌ Senha incorreta")
                return jsonify({'success': False, 'message': 'Senha incorreta'})
        else:
            print(f"❌ Usuário não encontrado: {email}")
            
            # Listar todos os usuários para debug
            conn = get_db_connection()
            todos_usuarios = conn.execute('SELECT id, nome, email FROM usuarios').fetchall()
            conn.close()
            
            if todos_usuarios:
                print("📋 Usuários existentes no banco:")
                for user in todos_usuarios:
                    print(f"   - ID: {user['id']}, Nome: {user['nome']}, Email: {user['email']}")
            
            return jsonify({'success': False, 'message': 'Email não cadastrado'})
    
    except FileNotFoundError:
        return jsonify({'success': False, 'message': f'Banco de dados {DATABASE} não encontrado!'})
    except Exception as e:
        print(f"❌ Erro no login: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no servidor: {str(e)}'})

@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso!'})

# =====================
# API - VERIFICAÇÃO DE BANCO
# =====================

@app.route('/api/verificar-banco')
def verificar_banco():
    """Rota para verificar o estado do banco de dados"""
    try:
        if not os.path.exists(DATABASE):
            return jsonify({
                'existe': False,
                'mensagem': f'Banco de dados {DATABASE} não encontrado',
                'sucesso': False
            })
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = [row[0] for row in cursor.fetchall()]
        
        # Contar registros em cada tabela
        contagens = {}
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{tabela}]")
                contagens[tabela] = cursor.fetchone()[0]
            except:
                contagens[tabela] = 'erro'
        
        # Verificar usuários
        usuarios = []
        if 'usuarios' in tabelas:
            cursor.execute("SELECT id, nome, email FROM usuarios")
            usuarios = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'existe': True,
            'tabelas': tabelas,
            'contagens': contagens,
            'usuarios': usuarios,
            'sucesso': True
        })
        
    except Exception as e:
        return jsonify({
            'existe': False,
            'mensagem': f'Erro ao verificar banco: {str(e)}',
            'sucesso': False
        })

# =====================
# API - SERVIÇOS (CRUD COMPLETO)
# =====================

@app.route('/api/servicos', methods=['GET', 'POST'])
def api_servicos():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            servicos = conn.execute(
                'SELECT * FROM servicos WHERE usuario_id = ? ORDER BY nome', 
                (usuario_id,)
            ).fetchall()
            conn.close()
            
            servicos_list = []
            for servico in servicos:
                servicos_list.append({
                    'id': servico['id'],
                    'nome': servico['nome'],
                    'descricao': servico['descricao'],
                    'imagem': servico['imagem']
                })
            
            return jsonify(servicos_list)
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                nome = data.get('nome')
                descricao = data.get('descricao')
                imagem = data.get('imagem')
                
                if not nome:
                    return jsonify({'success': False, 'message': 'Nome é obrigatório'})
                
                conn.execute(
                    'INSERT INTO servicos (nome, descricao, imagem, usuario_id) VALUES (?, ?, ?, ?)',
                    (nome, descricao, imagem, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Serviço adicionado com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao adicionar serviço: {str(e)}'})
    
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

@app.route('/api/servicos/<int:servico_id>', methods=['GET', 'PUT', 'DELETE'])
def api_servico(servico_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            servico = conn.execute(
                'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
                (servico_id, usuario_id)
            ).fetchone()
            
            conn.close()
            
            if servico:
                return jsonify({
                    'id': servico['id'],
                    'nome': servico['nome'],
                    'descricao': servico['descricao'],
                    'imagem': servico['imagem']
                })
            else:
                return jsonify({'error': 'Serviço não encontrado'}), 404
        
        elif request.method == 'PUT':
            try:
                data = request.get_json()
                nome = data.get('nome')
                descricao = data.get('descricao')
                imagem = data.get('imagem')
                
                if not nome:
                    return jsonify({'success': False, 'message': 'Nome é obrigatório'})
                
                # Verificar se o serviço pertence ao usuário
                servico = conn.execute(
                    'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
                    (servico_id, usuario_id)
                ).fetchone()
                
                if not servico:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Serviço não encontrado'})
                
                conn.execute(
                    'UPDATE servicos SET nome = ?, descricao = ?, imagem = ? WHERE id = ? AND usuario_id = ?',
                    (nome, descricao, imagem, servico_id, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Serviço atualizado com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao atualizar serviço: {str(e)}'})
        
        elif request.method == 'DELETE':
            try:
                # Verificar se o serviço pertence ao usuário
                servico = conn.execute(
                    'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
                    (servico_id, usuario_id)
                ).fetchone()
                
                if not servico:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Serviço não encontrado'})
                
                conn.execute(
                    'DELETE FROM servicos WHERE id = ? AND usuario_id = ?',
                    (servico_id, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Serviço excluído com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao excluir serviço: {str(e)}'})
    
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

# =====================
# API - CLIENTES (CRUD COMPLETO)
# =====================

@app.route('/api/clientes', methods=['GET', 'POST'])
def api_clientes():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            clientes = conn.execute(
                'SELECT * FROM clientes WHERE usuario_id = ? ORDER BY nome', 
                (usuario_id,)
            ).fetchall()
            conn.close()
            
            clientes_list = []
            for cliente in clientes:
                clientes_list.append({
                    'id': cliente['id'],
                    'nome': cliente['nome'],
                    'telefone': cliente['telefone'],
                    'email': cliente['email']
                })
            
            return jsonify(clientes_list)
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                nome = data.get('nome')
                telefone = data.get('telefone')
                email = data.get('email')
                
                if not nome:
                    return jsonify({'success': False, 'message': 'Nome é obrigatório'})
                
                conn.execute(
                    'INSERT INTO clientes (nome, telefone, email, usuario_id) VALUES (?, ?, ?, ?)',
                    (nome, telefone, email, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Cliente adicionado com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao adicionar cliente: {str(e)}'})
    
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

@app.route('/api/clientes/<int:cliente_id>', methods=['GET', 'PUT', 'DELETE'])
def api_cliente(cliente_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            cliente = conn.execute(
                'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
                (cliente_id, usuario_id)
            ).fetchone()
            
            conn.close()
            
            if cliente:
                return jsonify({
                    'id': cliente['id'],
                    'nome': cliente['nome'],
                    'telefone': cliente['telefone'],
                    'email': cliente['email']
                })
            else:
                return jsonify({'error': 'Cliente não encontrado'}), 404
        
        elif request.method == 'PUT':
            try:
                data = request.get_json()
                nome = data.get('nome')
                telefone = data.get('telefone')
                email = data.get('email')
                
                if not nome:
                    return jsonify({'success': False, 'message': 'Nome é obrigatório'})
                
                # Verificar se o cliente pertence ao usuário
                cliente = conn.execute(
                    'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
                    (cliente_id, usuario_id)
                ).fetchone()
                
                if not cliente:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Cliente não encontrado'})
                
                conn.execute(
                    'UPDATE clientes SET nome = ?, telefone = ?, email = ? WHERE id = ? AND usuario_id = ?',
                    (nome, telefone, email, cliente_id, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Cliente atualizado com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao atualizar cliente: {str(e)}'})
        
        elif request.method == 'DELETE':
            try:
                # Verificar se o cliente pertence ao usuário
                cliente = conn.execute(
                    'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
                    (cliente_id, usuario_id)
                ).fetchone()
                
                if not cliente:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Cliente não encontrado'})
                
                conn.execute(
                    'DELETE FROM clientes WHERE id = ? AND usuario_id = ?',
                    (cliente_id, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Cliente excluído com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao excluir cliente: {str(e)}'})
    
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

# =====================
# API - AGENDAMENTOS (CRUD COMPLETO)
# =====================

@app.route('/api/agendamentos', methods=['GET', 'POST'])
def api_agendamentos():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            agendamentos = conn.execute('''
                SELECT a.*, c.nome as cliente_nome, c.telefone as cliente_telefone, 
                       c.email as cliente_email, s.nome as servico_nome, 
                       c.id as cliente_id, s.id as servico_id
                FROM agendamentos a 
                LEFT JOIN clientes c ON a.cliente_id = c.id 
                LEFT JOIN servicos s ON a.servico_id = s.id 
                WHERE a.usuario_id = ? 
                ORDER BY a.data_agendamento DESC, a.hora_agendamento DESC
            ''', (usuario_id,)).fetchall()
            conn.close()
            
            agendamentos_list = []
            for agendamento in agendamentos:
                agendamentos_list.append({
                    'id': agendamento['id'],
                    'cliente_id': agendamento['cliente_id'],
                    'cliente_nome': agendamento['cliente_nome'],
                    'cliente_telefone': agendamento['cliente_telefone'],
                    'cliente_email': agendamento['cliente_email'],
                    'servico_id': agendamento['servico_id'],
                    'servico_nome': agendamento['servico_nome'],
                    'data_agendamento': agendamento['data_agendamento'],
                    'hora_agendamento': agendamento['hora_agendamento'],
                    'status': agendamento['status']
                })
            
            return jsonify(agendamentos_list)
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                cliente_id = data.get('cliente_id')
                servico_id = data.get('servico_id')
                data_agendamento = data.get('data_agendamento')
                hora_agendamento = data.get('hora_agendamento')
                status = data.get('status', 'pendente')
                
                if not cliente_id or not servico_id or not data_agendamento or not hora_agendamento:
                    return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
                
                # Verificar se cliente e serviço pertencem ao usuário
                cliente = conn.execute(
                    'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
                    (cliente_id, usuario_id)
                ).fetchone()
                
                servico = conn.execute(
                    'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
                    (servico_id, usuario_id)
                ).fetchone()
                
                if not cliente:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Cliente não encontrado'})
                
                if not servico:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Serviço não encontrado'})
                
                # Inserir agendamento
                conn.execute(
                    'INSERT INTO agendamentos (cliente_id, servico_id, data_agendamento, hora_agendamento, status, usuario_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (int(cliente_id), int(servico_id), data_agendamento, hora_agendamento, status, usuario_id)
                )
                conn.commit()
                
                # ========== ENVIAR EMAIL PARA NOVO AGENDAMENTO ==========
                email_enviado = False
                mensagem_email = ""
                
                if cliente['email']:
                    enviado, mensagem = enviar_email_gmail(
                        cliente['email'],
                        cliente['nome'],
                        servico['nome'],
                        data_agendamento,
                        hora_agendamento,
                        status
                    )
                    
                    if enviado:
                        email_enviado = True
                        mensagem_email = "Email enviado com sucesso!"
                    else:
                        mensagem_email = f"Email não enviado: {mensagem}"
                else:
                    mensagem_email = "Cliente não tem email cadastrado"
                
                conn.close()
                
                return jsonify({
                    'success': True, 
                    'message': f'Agendamento realizado com sucesso! {mensagem_email}',
                    'email_enviado': email_enviado
                })
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao criar agendamento: {str(e)}'})
    
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

@app.route('/api/agendamentos/<int:agendamento_id>', methods=['GET', 'PUT', 'DELETE'])
def api_agendamento(agendamento_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            agendamento = conn.execute('''
                SELECT a.*, c.nome as cliente_nome, c.telefone as cliente_telefone, 
                       c.email as cliente_email, s.nome as servico_nome
                FROM agendamentos a 
                LEFT JOIN clientes c ON a.cliente_id = c.id 
                LEFT JOIN servicos s ON a.servico_id = s.id 
                WHERE a.id = ? AND a.usuario_id = ?
            ''', (agendamento_id, usuario_id)).fetchone()
            
            conn.close()
            
            if agendamento:
                return jsonify({
                    'id': agendamento['id'],
                    'cliente_id': agendamento['cliente_id'],
                    'cliente_nome': agendamento['cliente_nome'],
                    'cliente_telefone': agendamento['cliente_telefone'],
                    'cliente_email': agendamento['cliente_email'],
                    'servico_id': agendamento['servico_id'],
                    'servico_nome': agendamento['servico_nome'],
                    'data_agendamento': agendamento['data_agendamento'],
                    'hora_agendamento': agendamento['hora_agendamento'],
                    'status': agendamento['status']
                })
            else:
                return jsonify({'error': 'Agendamento não encontrado'}), 404
        
        elif request.method == 'PUT':
            try:
                data = request.get_json()
                cliente_id = data.get('cliente_id')
                servico_id = data.get('servico_id')
                data_agendamento = data.get('data_agendamento')
                hora_agendamento = data.get('hora_agendamento')
                status = data.get('status')
                
                # Verificar se o agendamento pertence ao usuário
                agendamento = conn.execute(
                    'SELECT * FROM agendamentos WHERE id = ? AND usuario_id = ?', 
                    (agendamento_id, usuario_id)
                ).fetchone()
                
                if not agendamento:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Agendamento não encontrado'})
                
                # Verificar se cliente e serviço pertencem ao usuário (se for atualizar)
                if cliente_id:
                    cliente = conn.execute(
                        'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
                        (cliente_id, usuario_id)
                    ).fetchone()
                    
                    if not cliente:
                        conn.close()
                        return jsonify({'success': False, 'message': 'Cliente não encontrado'})
                
                if servico_id:
                    servico = conn.execute(
                        'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
                        (servico_id, usuario_id)
                    ).fetchone()
                    
                    if not servico:
                        conn.close()
                        return jsonify({'success': False, 'message': 'Serviço não encontrado'})
                
                # Atualizar agendamento
                update_query = 'UPDATE agendamentos SET '
                params = []
                
                if cliente_id:
                    update_query += 'cliente_id = ?, '
                    params.append(cliente_id)
                
                if servico_id:
                    update_query += 'servico_id = ?, '
                    params.append(servico_id)
                
                if data_agendamento:
                    update_query += 'data_agendamento = ?, '
                    params.append(data_agendamento)
                
                if hora_agendamento:
                    update_query += 'hora_agendamento = ?, '
                    params.append(hora_agendamento)
                
                if status:
                    update_query += 'status = ?, '
                    params.append(status)
                
                # Remover última vírgula e espaço
                update_query = update_query.rstrip(', ')
                update_query += ' WHERE id = ? AND usuario_id = ?'
                
                params.extend([agendamento_id, usuario_id])
                
                conn.execute(update_query, tuple(params))
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Agendamento atualizado com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao atualizar agendamento: {str(e)}'})
        
        elif request.method == 'DELETE':
            try:
                # Verificar se o agendamento pertence ao usuário
                agendamento = conn.execute(
                    'SELECT * FROM agendamentos WHERE id = ? AND usuario_id = ?', 
                    (agendamento_id, usuario_id)
                ).fetchone()
                
                if not agendamento:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Agendamento não encontrado'})
                
                conn.execute(
                    'DELETE FROM agendamentos WHERE id = ? AND usuario_id = ?',
                    (agendamento_id, usuario_id)
                )
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'Agendamento excluído com sucesso!'})
            
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': f'Erro ao excluir agendamento: {str(e)}'})
    
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

# =====================
# API - ATUALIZAR STATUS DO AGENDAMENTO (CORRIGIDO)
# =====================

@app.route('/api/agendamentos/<int:agendamento_id>/status', methods=['PUT'])
def atualizar_status_agendamento(agendamento_id):
    """
    Atualiza o status de um agendamento específico
    """
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        data = request.get_json()
        novo_status = data.get('status')
        
        if not novo_status:
            return jsonify({'success': False, 'message': 'Status é obrigatório'})
        
        # Validar status
        status_validos = ['pendente', 'confirmado', 'realizado', 'cancelado']
        if novo_status not in status_validos:
            return jsonify({'success': False, 'message': f'Status inválido. Use: {", ".join(status_validos)}'})
        
        conn = get_db_connection()
        
        # Verificar se o agendamento pertence ao usuário
        agendamento = conn.execute('''
            SELECT a.*, c.nome as cliente_nome, c.email as cliente_email, s.nome as servico_nome
            FROM agendamentos a
            LEFT JOIN clientes c ON a.cliente_id = c.id
            LEFT JOIN servicos s ON a.servico_id = s.id
            WHERE a.id = ? AND a.usuario_id = ?
        ''', (agendamento_id, usuario_id)).fetchone()
        
        if not agendamento:
            conn.close()
            return jsonify({'success': False, 'message': 'Agendamento não encontrado'})
        
        # Atualizar status
        conn.execute('''
            UPDATE agendamentos 
            SET status = ? 
            WHERE id = ? AND usuario_id = ?
        ''', (novo_status, agendamento_id, usuario_id))
        
        conn.commit()
        
        # ========== ENVIAR EMAIL DE ATUALIZAÇÃO ==========
        email_enviado = False
        mensagem_email = ""
        
        if agendamento['cliente_email']:
            enviado, mensagem = enviar_email_gmail(
                agendamento['cliente_email'],
                agendamento['cliente_nome'],
                agendamento['servico_nome'],
                agendamento['data_agendamento'],
                agendamento['hora_agendamento'],
                novo_status
            )
            
            if enviado:
                email_enviado = True
                mensagem_email = "Email enviado com sucesso!"
            else:
                mensagem_email = f"Email não enviado: {mensagem}"
        else:
            mensagem_email = "Cliente não tem email cadastrado"
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Status atualizado para {novo_status}. {mensagem_email}',
            'email_enviado': email_enviado,
            'agendamento': {
                'id': agendamento_id,
                'status': novo_status,
                'cliente_nome': agendamento['cliente_nome'],
                'servico_nome': agendamento['servico_nome'],
                'data_agendamento': agendamento['data_agendamento'],
                'hora_agendamento': agendamento['hora_agendamento']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        }), 500

# =====================
# API - DASHBOARD COMPLETO
# =====================

@app.route('/api/dashboard/completo')
def api_dashboard_completo():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    # Verificar se o banco existe
    if not os.path.exists(DATABASE):
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        
        # =====================
        # ESTATÍSTICAS
        # =====================
        
        # Agendamentos de hoje
        agendamentos_hoje = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND data_agendamento = ?
        ''', (usuario_id, hoje)).fetchone()['total']
        
        # Agendamentos deste mês
        agendamentos_mes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? 
            AND strftime('%m', data_agendamento) = ?
            AND strftime('%Y', data_agendamento) = ?
        ''', (usuario_id, f'{mes_atual:02d}', str(ano_atual))).fetchone()['total']
        
        # Total de serviços
        total_servicos = conn.execute('''
            SELECT COUNT(*) as total 
            FROM servicos 
            WHERE usuario_id = ?
        ''', (usuario_id,)).fetchone()['total']
        
        # Total de clientes
        total_clientes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM clientes 
            WHERE usuario_id = ?
        ''', (usuario_id,)).fetchone()['total']
        
        # Agendamentos por status
        agendamentos_pendentes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'pendente'
        ''', (usuario_id,)).fetchone()['total']
        
        agendamentos_confirmados = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'confirmado'
        ''', (usuario_id,)).fetchone()['total']
        
        agendamentos_realizados = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'realizado'
        ''', (usuario_id,)).fetchone()['total']
        
        agendamentos_cancelados = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'cancelado'
        ''', (usuario_id,)).fetchone()['total']
        
        # =====================
        # AGENDAMENTOS RECENTES (ÚLTIMOS 10)
        # =====================
        
        agendamentos = conn.execute('''
            SELECT a.*, c.nome as cliente_nome, c.telefone as cliente_telefone, 
                   c.email as cliente_email, s.nome as servico_nome
            FROM agendamentos a 
            LEFT JOIN clientes c ON a.cliente_id = c.id 
            LEFT JOIN servicos s ON a.servico_id = s.id 
            WHERE a.usuario_id = ? 
            ORDER BY a.data_agendamento DESC, a.hora_agendamento DESC
            LIMIT 10
        ''', (usuario_id,)).fetchall()
        
        # =====================
        # SERVIÇOS POPULARES (TOP 5)
        # =====================
        
        servicos_populares = conn.execute('''
            SELECT s.nome, COUNT(a.id) as total_agendamentos
            FROM servicos s
            LEFT JOIN agendamentos a ON s.id = a.servico_id
            WHERE s.usuario_id = ?
            GROUP BY s.id
            ORDER BY total_agendamentos DESC
            LIMIT 5
        ''', (usuario_id,)).fetchall()
        
        # =====================
        # CLIENTES FREQUENTES (TOP 5)
        # =====================
        
        clientes_frequentes = conn.execute('''
            SELECT c.nome, COUNT(a.id) as total_agendamentos
            FROM clientes c
            LEFT JOIN agendamentos a ON c.id = a.cliente_id
            WHERE c.usuario_id = ?
            GROUP BY c.id
            ORDER BY total_agendamentos DESC
            LIMIT 5
        ''', (usuario_id,)).fetchall()
        
        conn.close()
        
        # =====================
        # FORMATAR RESPOSTA
        # =====================
        
        estatisticas = {
            'agendamentos_hoje': agendamentos_hoje,
            'agendamentos_mes': agendamentos_mes,
            'total_servicos': total_servicos,
            'total_clientes': total_clientes,
            'agendamentos_pendentes': agendamentos_pendentes,
            'agendamentos_confirmados': agendamentos_confirmados,
            'agendamentos_realizados': agendamentos_realizados,
            'agendamentos_cancelados': agendamentos_cancelados,
            'timestamp': datetime.now().isoformat()
        }
        
        agendamentos_list = []
        for agendamento in agendamentos:
            agendamentos_list.append({
                'id': agendamento['id'],
                'cliente_nome': agendamento['cliente_nome'],
                'cliente_telefone': agendamento['cliente_telefone'],
                'cliente_email': agendamento['cliente_email'],
                'servico_nome': agendamento['servico_nome'],
                'data_agendamento': agendamento['data_agendamento'],
                'hora_agendamento': agendamento['hora_agendamento'],
                'status': agendamento['status']
            })
        
        servicos_populares_list = []
        for servico in servicos_populares:
            servicos_populares_list.append({
                'nome': servico['nome'],
                'total_agendamentos': servico['total_agendamentos']
            })
        
        clientes_frequentes_list = []
        for cliente in clientes_frequentes:
            clientes_frequentes_list.append({
                'nome': cliente['nome'],
                'total_agendamentos': cliente['total_agendamentos']
            })
        
        return jsonify({
            'estatisticas': estatisticas,
            'agendamentos_recentes': agendamentos_list,
            'servicos_populares': servicos_populares_list,
            'clientes_frequentes': clientes_frequentes_list,
            'sucesso': True
        })
        
    except FileNotFoundError:
        return jsonify({'error': 'Banco de dados não encontrado'}), 500
    except Exception as e:
        conn.close()
        return jsonify({
            'error': f'Erro ao carregar dashboard: {str(e)}',
            'sucesso': False
        }), 500

# =====================
# API - DADOS DO USUÁRIO
# =====================

@app.route('/api/usuario')
def api_usuario():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    return jsonify({
        'id': session['usuario_id'],
        'nome': session['usuario_nome'],
        'email': session['usuario_email']
    })

# =====================
# API - ATUALIZAR DADOS DO USUÁRIO
# =====================

@app.route('/api/usuario/atualizar', methods=['PUT'])
def atualizar_usuario():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    try:
        data = request.get_json()
        nome = data.get('nome')
        email = data.get('email')
        senha_atual = data.get('senha_atual')
        nova_senha = data.get('nova_senha')
        
        conn = get_db_connection()
        usuario_id = session['usuario_id']
        
        # Buscar usuário atual
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE id = ?', (usuario_id,)
        ).fetchone()
        
        if not usuario:
            conn.close()
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
        
        # Verificar senha atual se for alterar senha
        if nova_senha and senha_atual:
            if usuario['senha'] != senha_atual:
                conn.close()
                return jsonify({'success': False, 'message': 'Senha atual incorreta'})
        
        # Atualizar dados
        if nome:
            conn.execute(
                'UPDATE usuarios SET nome = ? WHERE id = ?',
                (nome, usuario_id)
            )
            session['usuario_nome'] = nome
        
        if email:
            # Verificar se email já existe
            usuario_existente = conn.execute(
                'SELECT id FROM usuarios WHERE email = ? AND id != ?', 
                (email, usuario_id)
            ).fetchone()
            
            if usuario_existente:
                conn.close()
                return jsonify({'success': False, 'message': 'Email já está em uso por outro usuário'})
            
            conn.execute(
                'UPDATE usuarios SET email = ? WHERE id = ?',
                (email, usuario_id)
            )
            session['usuario_email'] = email
        
        if nova_senha and senha_atual:
            conn.execute(
                'UPDATE usuarios SET senha = ? WHERE id = ?',
                (nova_senha, usuario_id)
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Dados atualizados com sucesso!',
            'usuario': {
                'id': usuario_id,
                'nome': session.get('usuario_nome'),
                'email': session.get('usuario_email')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar dados: {str(e)}'
        }), 500

# =====================
# API - ESTATÍSTICAS DO DASHBOARD
# =====================

@app.route('/api/dashboard/estatisticas')
def api_dashboard_estatisticas():
    """
    Retorna estatísticas para o dashboard
    """
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        
        # 1. Agendamentos de hoje
        agendamentos_hoje = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND data_agendamento = ?
        ''', (usuario_id, hoje)).fetchone()['total']
        
        # 2. Agendamentos deste mês
        agendamentos_mes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? 
            AND strftime('%m', data_agendamento) = ?
            AND strftime('%Y', data_agendamento) = ?
        ''', (usuario_id, f'{mes_atual:02d}', str(ano_atual))).fetchone()['total']
        
        # 3. Total de serviços
        total_servicos = conn.execute('''
            SELECT COUNT(*) as total 
            FROM servicos 
            WHERE usuario_id = ?
        ''', (usuario_id,)).fetchone()['total']
        
        # 4. Total de clientes
        total_clientes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM clientes 
            WHERE usuario_id = ?
        ''', (usuario_id,)).fetchone()['total']
        
        # 5. Agendamentos por status
        agendamentos_pendentes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'pendente'
        ''', (usuario_id,)).fetchone()['total']
        
        agendamentos_confirmados = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'confirmado'
        ''', (usuario_id,)).fetchone()['total']
        
        agendamentos_realizados = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'realizado'
        ''', (usuario_id,)).fetchone()['total']
        
        agendamentos_cancelados = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'cancelado'
        ''', (usuario_id,)).fetchone()['total']
        
        # 6. Receita total deste mês (exemplo)
        receita_mes = conn.execute('''
            SELECT COUNT(*) as total_agendamentos 
            FROM agendamentos 
            WHERE usuario_id = ? 
            AND strftime('%m', data_agendamento) = ?
            AND strftime('%Y', data_agendamento) = ?
        ''', (usuario_id, f'{mes_atual:02d}', str(ano_atual))).fetchone()['total_agendamentos']
        
        # Valor médio por serviço (exemplo: R$ 50.00)
        receita_mes = receita_mes * 50.00
        
        conn.close()
        
        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'agendamentos_hoje': agendamentos_hoje,
                'agendamentos_mes': agendamentos_mes,
                'total_servicos': total_servicos,
                'total_clientes': total_clientes,
                'agendamentos_pendentes': agendamentos_pendentes,
                'agendamentos_confirmados': agendamentos_confirmados,
                'agendamentos_realizados': agendamentos_realizados,
                'agendamentos_cancelados': agendamentos_cancelados,
                'receita_mes': receita_mes,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'error': f'Erro ao carregar estatísticas: {str(e)}'
        }), 500

# =====================
# API - BUSCA RÁPIDA
# =====================

@app.route('/api/busca/<termo>')
def api_busca(termo):
    """
    Busca rápida por clientes, serviços e agendamentos
    """
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        # Buscar clientes
        clientes = conn.execute('''
            SELECT id, nome, telefone, email
            FROM clientes 
            WHERE usuario_id = ? 
            AND (nome LIKE ? OR email LIKE ? OR telefone LIKE ?)
            LIMIT 5
        ''', (usuario_id, f'%{termo}%', f'%{termo}%', f'%{termo}%')).fetchall()
        
        # Buscar serviços
        servicos = conn.execute('''
            SELECT id, nome, descricao
            FROM servicos 
            WHERE usuario_id = ? 
            AND nome LIKE ?
            LIMIT 5
        ''', (usuario_id, f'%{termo}%')).fetchall()
        
        # Buscar agendamentos
        agendamentos = conn.execute('''
            SELECT a.*, c.nome as cliente_nome, s.nome as servico_nome
            FROM agendamentos a
            LEFT JOIN clientes c ON a.cliente_id = c.id
            LEFT JOIN servicos s ON a.servico_id = s.id
            WHERE a.usuario_id = ? 
            AND (c.nome LIKE ? OR s.nome LIKE ? OR a.data_agendamento LIKE ?)
            ORDER BY a.data_agendamento DESC
            LIMIT 5
        ''', (usuario_id, f'%{termo}%', f'%{termo}%', f'%{termo}%')).fetchall()
        
        conn.close()
        
        resultados = {
            'clientes': [dict(cliente) for cliente in clientes],
            'servicos': [dict(servico) for servico in servicos],
            'agendamentos': []
        }
        
        for agendamento in agendamentos:
            resultados['agendamentos'].append({
                'id': agendamento['id'],
                'cliente_nome': agendamento['cliente_nome'],
                'servico_nome': agendamento['servico_nome'],
                'data_agendamento': agendamento['data_agendamento'],
                'hora_agendamento': agendamento['hora_agendamento'],
                'status': agendamento['status']
            })
        
        return jsonify({
            'sucesso': True,
            'resultados': resultados
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'error': f'Erro na busca: {str(e)}'
        }), 500

# =====================
# API - NOTIFICAÇÕES
# =====================

@app.route('/api/notificacoes')
def api_notificacoes():
    """
    Retorna notificações do sistema
    """
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        
        # Agendamentos de hoje
        agendamentos_hoje = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND data_agendamento = ?
        ''', (usuario_id, hoje)).fetchone()['total']
        
        # Agendamentos pendentes
        agendamentos_pendentes = conn.execute('''
            SELECT COUNT(*) as total 
            FROM agendamentos 
            WHERE usuario_id = ? AND status = 'pendente'
        ''', (usuario_id,)).fetchone()['total']
        
        conn.close()
        
        notificacoes = []
        
        if agendamentos_hoje > 0:
            notificacoes.append({
                'id': 1,
                'titulo': 'Agendamentos hoje',
                'mensagem': f'Você tem {agendamentos_hoje} agendamento(s) para hoje',
                'tipo': 'info',
                'icone': 'calendar-day'
            })
        
        if agendamentos_pendentes > 0:
            notificacoes.append({
                'id': 2,
                'titulo': 'Agendamentos pendentes',
                'mensagem': f'Você tem {agendamentos_pendentes} agendamento(s) pendentes',
                'tipo': 'warning',
                'icone': 'clock'
            })
        
        return jsonify({
            'sucesso': True,
            'notificacoes': notificacoes
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'error': f'Erro ao carregar notificações: {str(e)}'
        }), 500

# =====================
# API - ATIVIDADE RECENTE
# =====================

@app.route('/api/atividade-recente')
def api_atividade_recente():
    """
    Retorna a atividade recente do sistema
    """
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    
    try:
        conn = get_db_connection()
        
        # Últimos agendamentos criados
        agendamentos = conn.execute('''
            SELECT a.*, c.nome as cliente_nome, s.nome as servico_nome
            FROM agendamentos a
            LEFT JOIN clientes c ON a.cliente_id = c.id
            LEFT JOIN servicos s ON a.servico_id = s.id
            WHERE a.usuario_id = ?
            ORDER BY a.data_criacao DESC
            LIMIT 10
        ''', (usuario_id,)).fetchall()
        
        # Últimos clientes cadastrados
        clientes = conn.execute('''
            SELECT nome, data_criacao
            FROM clientes
            WHERE usuario_id = ?
            ORDER BY data_criacao DESC
            LIMIT 5
        ''', (usuario_id,)).fetchall()
        
        conn.close()
        
        atividades = []
        
        # Adicionar agendamentos como atividades
        for agendamento in agendamentos[:5]:
            data_formatada = datetime.strptime(agendamento['data_agendamento'], '%Y-%m-%d').strftime('%d/%m/%Y')
            atividades.append({
                'tipo': 'agendamento',
                'descricao': f'Agendamento para {agendamento["cliente_nome"]} - {agendamento["servico_nome"]}',
                'detalhes': f'{data_formatada} às {agendamento["hora_agendamento"]}',
                'status': agendamento['status'],
                'data': agendamento['data_criacao']
            })
        
        # Adicionar clientes como atividades
        for cliente in clientes:
            atividades.append({
                'tipo': 'cliente',
                'descricao': f'Novo cliente cadastrado: {cliente["nome"]}',
                'detalhes': 'Cliente adicionado ao sistema',
                'data': cliente['data_criacao']
            })
        
        # Ordenar por data (mais recente primeiro)
        atividades.sort(key=lambda x: x['data'], reverse=True)
        
        return jsonify({
            'sucesso': True,
            'atividades': atividades[:10]  # Limitar a 10 atividades
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'error': f'Erro ao carregar atividade: {str(e)}'
        }), 500

# =====================
# ROTA PARA SERVIR ARQUIVOS
# =====================

@app.route('/<path:filename>')
def serve_files(filename):
    try:
        return send_from_directory('.', filename)
    except:
        return "Arquivo não encontrado", 404

# =====================
# INICIALIZAÇÃO
# =====================

if __name__ == '__main__':
    print("=" * 60)
    print("AGENDAMENTO+ - SISTEMA COMPLETO")
    print("=" * 60)
    print("🌐 Servidor: http://localhost:5000")
    print(f"💾 Banco de dados: {DATABASE}")
    print("📧 Sistema de email configurado com as credenciais fornecidas")
    print("=" * 60)
    print("📱 Redes Sociais:")
    print("   Instagram: @agendamentomais")
    print("   WhatsApp: (61) 98582-5956")
    print("=" * 60)
    print("📧 CREDENCIAIS DE EMAIL CONFIGURADAS:")
    print(f"   Email: agendamentomais.suporte1@gmail.com")
    print(f"   Senha de app: dvno ipft lbds dpzg")
    print("=" * 60)
    print("🔍 Para verificar o banco de dados, acesse:")
    print("   http://localhost:5000/api/verificar-banco")
    print("=" * 60)
    print("⚠️ IMPORTANTE:")
    print("   1. Se o email não funcionar, verifique se as credenciais estão corretas")
    print("   2. Certifique-se de que a senha de app do Gmail está ativa")
    print("   3. Caso necessário, gere uma nova senha de app")
    print("=" * 60)
    print("✅ Sistema pronto para uso!")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)