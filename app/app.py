from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from crypto import *
import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from crypto import *


load_dotenv()

# Configuração do aplicativo
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Inicialização do banco de dados
db = SQLAlchemy()
db.init_app(app)


class IA(db.Model):
    __tablename__ = 'ias'
    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, nullable=False)
    status = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    # Relacionamentos
    prompts = relationship("Prompt", back_populates="ia", cascade="all, delete-orphan")
    ia_config = relationship("IAConfig", back_populates="ia", uselist=False, cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="ia", uselist=False, cascade="all, delete-orphan")
    
    @property
    def active_prompt(self):
        active = [p for p in self.prompts if p.is_active]
        return active[0] if active else None

class Prompt(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.Integer, primary_key=True, index=True)
    ia_id = db.Column(db.Integer, db.ForeignKey('ias.id'), nullable=False)
    prompt_text = db.Column(db.String, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    ia = relationship("IA", back_populates="prompts")

class IAConfig(db.Model):
    __tablename__ = 'ia_config'
    id = db.Column(db.Integer, primary_key=True, index=True)
    ia_id = db.Column(db.Integer, db.ForeignKey('ias.id'), nullable=False)
    channel = db.Column(db.String, nullable=False)
    ai_api = db.Column(db.String, nullable=False)
    encrypted_credentials = db.Column(db.String, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    ia = relationship("IA", back_populates="ia_config")

    @property
    def credentials(self):
        return decrypt_data(self.encrypted_credentials)
    
class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True, index=True)
    ia_id = db.Column(db.Integer, db.ForeignKey('ias.id'), nullable=False)
    name = db.Column(db.String, nullable=True)
    phone = db.Column(db.String, nullable=True, unique=True)
    message = db.Column(db.JSON, nullable=False)
    resume = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    ia = relationship("IA", back_populates="leads")

# Protect all existing routes with 
@app.route('/')
def index():
    ias = IA.query.all()
    ia_list = []
    for ia in ias:
        config_data = []
        if ia.ia_config:
            config_data = [{
                "id": ia.ia_config.id,
                "channel": ia.ia_config.channel,
                "ai_api": ia.ia_config.ai_api,
                "credentials": ia.ia_config.credentials
            }]
            
        ia_info = {
            'id': ia.id,
            'name': ia.name,
            'phone_number': ia.phone_number,
            'status': ia.status,
            'configs': config_data,
            'prompts': [{'id': ia.active_prompt.id, 'text': ia.active_prompt.prompt_text, 'is_active': ia.active_prompt.is_active}] if ia.active_prompt else []
        }
        ia_list.append(ia_info)
    return render_template('index.html', ias=ia_list)

@app.route('/create-ia', methods=['GET', 'POST'])
def create_ia():
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            phone_number = request.form.get('phone_number')
            channel = request.form.get('channel')
            ia_used = request.form.get('ia_used')
            apikey = request.form.get('apikey')
            model = request.form.get('model')
            new_ia = IA(
                name=name,
                phone_number=phone_number,
                status=True
            )
            
            db.session.add(new_ia)
            db.session.commit()
            data = {
                "api_key": apikey,
                "api_secret": "openai",
                "ai_model":model
            }
            ia_config = IAConfig(
                ia_id=new_ia.id,
                channel=channel,
                ai_api= ia_used,
                encrypted_credentials=encrypt_data(data)
            )
            
            db.session.add(ia_config)
            db.session.commit()
    except Exception as ex:
        print(ex)     
           
    return redirect(url_for('index'))

@app.route('/edit-ia/<int:id_ia>', methods=['GET', 'POST'])
def edit_ia(id_ia):
    if request.method == 'POST':
        ia = IA.query.filter_by(id=id_ia).first()
        if not ia:
            return redirect(url_for('index'))
        
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        status = request.form.get('status')
        channel = request.form.get('channel')
        ia_used = request.form.get('ia_used')
        apikey = request.form.get('apikey')
        model = request.form.get('model')
        ia.name = name
        ia.phone_number = phone_number
        ia.status = True if status == 'True' else False 

         # Se não existe config, cria!
        if ia.ia_config is None:
            ia.ia_config = IAConfig(ia_id=ia.id)

        ia.ia_config.channel = channel
        ia.ia_config.ai_api = ia_used
        
        if apikey:
            apikey = apikey.strip()
        if model:
            model = model.strip()

        data = {
            "api_key": apikey,
            "api_secret": "openai",
            "ai_model":model
        }   
        encrypted_data = encrypt_data(data)
        
        ia.ia_config.encrypted_credentials = encrypted_data
        
        db.session.commit()
        
    return redirect(url_for('index'))

@app.route('/delete-ia/<int:id_ia>', methods=['GET', 'POST'])
def delete_ia(id_ia):
    if request.method == 'POST':
        ia = IA.query.filter_by(id=id_ia).first()
        if not ia:
            return redirect(url_for('index'))
        
        db.session.delete(ia)
        db.session.commit()
        
    return redirect(url_for('index'))

@app.route('/get-prompts-ia', methods=['GET'])
def get_prompts_ia():
    prompts = Prompt.query.all()
    ias = IA.query.all()
    prompts_list = []
    for prompt in prompts:
        prompt_dict = {
            'id': prompt.id,
            'ia_name': prompt.ia.name,
            'ia_id': prompt.ia.id,
            'text': prompt.prompt_text,
            'status': prompt.is_active,
            'created_at': prompt.created_at.strftime('%d-%m-%Y %H:%M:%S'),
            'updated_at': prompt.updated_at.strftime('%d-%m-%Y %H:%M:%S'),
        }
        prompts_list.append(prompt_dict)
    unique_ias = [{"id":ia.id, "ia_name": ia.name} for ia in ias]
    return render_template('prompt.html', prompts=prompts_list, unique_ias=unique_ias)

@app.route('/new-prompt/<int:id_ia>', methods=['GET', 'POST'])
def new_prompt(id_ia):
    if request.method == 'POST':
        
        new_prompt_text = request.form.get("text")
        status = request.form.get("status")
        
        new_prompt = Prompt(
            prompt_text=new_prompt_text,
            is_active=True if status == 'True' else False,
            ia_id=id_ia
        )
        
        db.session.add(new_prompt)
        db.session.commit()
        
    return redirect(url_for('get_prompts_ia'))

@app.route('/edit-prompt/<int:id_prompt>', methods=['GET', 'POST'])
def edit_prompt(id_prompt):
    if request.method == 'POST':
        promtp = Prompt.query.filter_by(id=id_prompt).first()
        if not promtp:
            return redirect(url_for('get_prompts_ia'))
        
        new_prompt = request.form.get("text")
        status = request.form.get("status")
        
        promtp.prompt_text = new_prompt
        promtp.is_active = True if status == 'True' else False
        db.session.commit()
        
    return redirect(url_for('get_prompts_ia'))

@app.route('/delete-prompt/<int:id_prompt>', methods=['GET', 'POST'])
def delete_prompt(id_prompt):
    if request.method == 'POST':
        promtp = Prompt.query.filter_by(id=id_prompt).first()
        if not promtp:
            return redirect(url_for('get_prompts_ia'))
        
        db.session.delete(promtp)
        db.session.commit()
        
    return redirect(url_for('get_prompts_ia'))


@app.route('/delete-lead/<int:id_lead>', methods=['GET', 'POST'])
def delete_lead(id_lead):
    if request.method == 'POST':
        lead = Lead.query.filter_by(id=id_lead).first()
        if not lead:
            return redirect(url_for('get_leads_ia'))
        
        db.session.delete(lead)
        db.session.commit()
        
    return redirect(url_for('get_leads_ia', ia_id = lead.ia_id))


@app.route('/get-leads-ia/<int:ia_id>', methods=['GET', 'POST'])
def get_leads_ia(ia_id):
    leads = Lead.query.filter_by(ia_id=ia_id).all()
    leads_list = []
    lead_id = int(request.args.get("lead_id", 0))
    selected_lead = {}
    for lead in leads:
        lead_dict = {
            'id': lead.id,
            'ia_name': lead.ia.name,
            'ia_id': lead.ia.id,
            'name': lead.name,
            'phone': lead.phone,
            'message': lead.message,
            'resume': lead.resume,
            'created_at': lead.created_at.strftime('%d-%m-%Y %H:%M:%S'),
            'updated_at': lead.updated_at.strftime('%d-%m-%Y %H:%M:%S'),
        }
        if lead_id == lead.id:
            selected_lead = lead_dict
            
        leads_list.append(lead_dict)
    
    
    return render_template('lead.html', leads=leads_list, selected_lead= selected_lead)

@app.route('/get-infos-lead/<int:ia_lead>', methods=['GET', 'POST'])
def get_info_lead(ia_lead):
    lead = Lead.query.filter_by(id=ia_lead).first()
    leads_list = []

    lead_dict = {
        'id': lead.id,
        'ia_name': lead.ia.name,
        'ia_id': lead.ia.id,
        'name': lead.name,
        'phone': lead.phone,
        'message': lead.message,
        'resume': lead.resume,
        'created_at': lead.created_at.strftime('%d-%m-%Y %H:%M:%S'),
        'updated_at': lead.updated_at.strftime('%d-%m-%Y %H:%M:%S'),
    }
    leads_list.append(lead_dict)

    return render_template('lead.html', selected_lead=lead_dict)

# Executar o aplicativo
if __name__ == '__main__':
    #db.create_all()  # Cria as tabelas no banco de dados
    app.run(debug=True)