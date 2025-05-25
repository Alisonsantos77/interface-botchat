from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import os
from models import db, IA, Prompt, IAConfig, Lead
from crypto import encrypt_data
from loguru import logger
from datetime import datetime
from flask import request

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


@app.context_processor
def inject_now():
    return {"now": datetime.now}


@app.route("/")
def index():
    items_per_page = 6  # numero por pagina
    current_page = request.args.get("page", 1, type=int)

    # Contar total de IAs
    total_ias = IA.query.count()

    # Calcular total de páginas
    total_pages = (total_ias + items_per_page - 1) // items_per_page

    # Garantir que current_page seja válido
    current_page = max(1, min(current_page, total_pages))

    # Consultar IAs para a página atual
    ias = (
        IA.query.offset((current_page - 1) * items_per_page).limit(items_per_page).all()
    )

    ia_list = []
    for ia in ias:
        config_data = []
        if ia.ia_config:
            credentials = ia.ia_config.credentials
            logger.info(
                f"[INDEX] Lendo IA: {ia.name} - ai_api: {ia.ia_config.ai_api} - credentials: { {k:v for k,v in credentials.items() if k != 'api_key'} }"
            )
            config_data = [
                {
                    "id": ia.ia_config.id,
                    "channel": ia.ia_config.channel,
                    "ai_api": ia.ia_config.ai_api,
                    "credentials": credentials,
                }
            ]
        ia_info = {
            "id": ia.id,
            "name": ia.name,
            "phone_number": ia.phone_number,
            "status": ia.status,
            "configs": config_data,
            "prompts": (
                [
                    {
                        "id": ia.active_prompt.id,
                        "text": ia.active_prompt.prompt_text,
                        "is_active": ia.active_prompt.is_active,
                    }
                ]
                if ia.active_prompt
                else []
            ),
        }
        ia_list.append(ia_info)

    logger.info(
        f"[INDEX] IA list montada: {[{'id': i['id'], 'name': i['name'], 'ai_api': i['configs'][0]['ai_api'] if i['configs'] else None} for i in ia_list]}"
    )

    return render_template(
        "index.html", ias=ia_list, current_page=current_page, total_pages=total_pages
    )


@app.route("/create-ia", methods=["GET", "POST"])
def create_ia():
    if request.method == "POST":
        try:
            name = request.form.get("name")
            phone_number = request.form.get("phone_number")
            channel = request.form.get("channel")
            ia_used = request.form.get("ia_used")
            apikey = request.form.get("apikey")
            model = request.form.get("model")
            # Se precisar de api_secret para algum provedor
            # api_secret = request.form.get("api_secret")

            logger.info(
                f"[CREATE-IA] Recebido: name={name}, phone={phone_number}, channel={channel}, ia_used={ia_used}, apikey={'***' if apikey else ''}, model={model}"
            )

            new_ia = IA(name=name, phone_number=phone_number, status=True)
            db.session.add(new_ia)
            db.session.commit()
            data = {"api_key": apikey, "ai_model": model}
            logger.info(
                f"[CREATE-IA] Salvando IA: {name} - ai_api: {ia_used} - data: { {k:v for k,v in data.items() if k != 'api_key'} }"
            )
            ia_config = IAConfig(
                ia_id=new_ia.id,
                channel=channel,
                ai_api=ia_used,
                encrypted_credentials=encrypt_data(data),
            )
            db.session.add(ia_config)
            db.session.commit()
            logger.success(
                f"[CREATE-IA] IA criada com sucesso: {name} ({phone_number})"
            )
        except Exception as ex:
            logger.error(f"[CREATE-IA] Erro ao criar IA: {ex}")
        return redirect(url_for("index"))
    logger.info("[CREATE-IA] Exibindo formulário de criação de IA")
    return render_template("ia_form.html", ia=None, action="Criar")


@app.route("/edit-ia/<int:id_ia>", methods=["GET", "POST"])
def edit_ia(id_ia):
    ia = IA.query.filter_by(id=id_ia).first()
    if not ia:
        logger.warning(f"[EDIT-IA] IA id {id_ia} não encontrada")
        return redirect(url_for("index"))
    if request.method == "POST":
        try:
            name = request.form.get("name")
            phone_number = request.form.get("phone_number")
            status = request.form.get("status")
            channel = request.form.get("channel")
            ia_used = request.form.get("ia_used")
            apikey = request.form.get("apikey")
            model = request.form.get("model")
            # api_secret = request.form.get("api_secret")

            logger.info(
                f"[EDIT-IA] Recebido: name={name}, phone={phone_number}, status={status}, channel={channel}, ia_used={ia_used}, apikey={'***' if apikey else ''}, model={model}"
            )

            ia.name = name
            ia.phone_number = phone_number
            ia.status = True if status == "True" else False

            if ia.ia_config is None:
                ia.ia_config = IAConfig(ia_id=ia.id)
            ia.ia_config.channel = channel
            ia.ia_config.ai_api = ia_used

            # Sempre atualizar as credenciais, mantendo as antigas se não vier valor novo
            old_credentials = (
                ia.ia_config.credentials if ia.ia_config.encrypted_credentials else {}
            )
            api_key_to_save = apikey if apikey else old_credentials.get("api_key", "")
            model_to_save = model if model else old_credentials.get("ai_model", "")
            data = {"api_key": api_key_to_save, "ai_model": model_to_save}
            logger.info(
                f"[EDIT-IA] Salvando encrypted_credentials: { {k:v for k,v in data.items() if k != 'api_key'} }"
            )
            ia.ia_config.encrypted_credentials = encrypt_data(data)

            db.session.commit()
            logger.success(f"[EDIT-IA] IA editada com sucesso: {name} ({phone_number})")
        except Exception as ex:
            logger.error(f"[EDIT-IA] Erro ao editar IA: {ex}")
        return redirect(url_for("index"))
    logger.info(f"[EDIT-IA] Exibindo formulário de edição para IA id {id_ia}")
    return render_template("ia_form.html", ia=ia, action="Editar")


@app.route("/delete-ia/<int:id_ia>", methods=["POST"])
def delete_ia(id_ia):
    ia = IA.query.filter_by(id=id_ia).first()
    if not ia:
        logger.warning(f"[DELETE-IA] IA id {id_ia} não encontrada")
        return redirect(url_for("index"))
    try:
        db.session.delete(ia)
        db.session.commit()
        logger.success(f"[DELETE-IA] IA deletada: {ia.name} ({ia.phone_number})")
    except Exception as ex:
        logger.error(f"[DELETE-IA] Erro ao deletar IA: {ex}")
    return redirect(url_for("index"))


@app.route("/get-prompts-ia", methods=["GET"])
def get_prompts_ia():
    prompts = Prompt.query.all()
    ias = IA.query.all()
    prompts_list = []
    for prompt in prompts:
        prompt_dict = {
            "id": prompt.id,
            "ia_name": prompt.ia.name,
            "ia_id": prompt.ia.id,
            "text": prompt.prompt_text,
            "status": prompt.is_active,
            "created_at": prompt.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            "updated_at": prompt.updated_at.strftime("%d-%m-%Y %H:%M:%S"),
        }
        prompts_list.append(prompt_dict)
    unique_ias = [{"id": ia.id, "ia_name": ia.name} for ia in ias]
    logger.info(
        f"[PROMPTS] Listando prompts: {[{'id': p['id'], 'ia_name': p['ia_name']} for p in prompts_list]}"
    )
    return render_template("prompt.html", prompts=prompts_list, unique_ias=unique_ias)


@app.route("/new-prompt/<int:id_ia>", methods=["GET", "POST"])
def new_prompt(id_ia):
    if request.method == "POST":
        try:
            new_prompt_text = request.form.get("text")
            status = request.form.get("status")
            ia_id = request.form.get("ia_id")
            logger.info(
                f"[NEW-PROMPT] Criando prompt para IA {ia_id}: texto={new_prompt_text}, status={status}"
            )
            # Validar se a IA existe
            ia = IA.query.filter_by(id=ia_id).first()
            if not ia:
                logger.error(f"[NEW-PROMPT] IA id {ia_id} não encontrada")
                return redirect(url_for("get_prompts_ia"))
            new_prompt = Prompt(
                prompt_text=new_prompt_text,
                is_active=True if status == "True" else False,
                ia_id=ia_id,
            )
            db.session.add(new_prompt)
            db.session.commit()
            logger.success(f"[NEW-PROMPT] Prompt criado para IA {ia_id}")
        except Exception as ex:
            logger.error(f"[NEW-PROMPT] Erro ao criar prompt: {ex}")
        return redirect(url_for("get_prompts_ia"))
    # Para GET, passar a lista de IAs e o id_ia como padrão
    ias = IA.query.all()
    logger.info(f"[NEW-PROMPT] Exibindo formulário de novo prompt para IA {id_ia}")
    return render_template("prompt_form.html", action="Criar", ia_id=id_ia, ias=ias)


@app.route("/edit-prompt/<int:id_prompt>", methods=["GET", "POST"])
def edit_prompt(id_prompt):
    prompt = Prompt.query.filter_by(id=id_prompt).first()
    if not prompt:
        logger.warning(f"[EDIT-PROMPT] Prompt id {id_prompt} não encontrado")
        return redirect(url_for("get_prompts_ia"))
    if request.method == "POST":
        try:
            new_prompt = request.form.get("text")
            status = request.form.get("status")
            ia_id = request.form.get("ia_id")  # Captura o ia_id do formulário
            logger.info(
                f"[EDIT-PROMPT] Editando prompt id {id_prompt}: texto={new_prompt}, status={status}, ia_id={ia_id}"
            )
            prompt.prompt_text = new_prompt
            prompt.is_active = True if status == "True" else False
            prompt.ia_id = ia_id  # Atualiza o ia_id
            db.session.commit()
            logger.success(f"[EDIT-PROMPT] Prompt editado id {id_prompt}")
        except Exception as ex:
            logger.error(f"[EDIT-PROMPT] Erro ao editar prompt: {ex}")
        return redirect(url_for("get_prompts_ia"))
    logger.info(
        f"[EDIT-PROMPT] Exibindo formulário de edição para prompt id {id_prompt}"
    )
    ias = IA.query.all()  # Carrega todas as IAs
    return render_template(
        "prompt_form.html", action="Editar", prompt=prompt, ias=ias, ia_id=prompt.ia_id
    )


@app.route("/delete-prompt/<int:id_prompt>", methods=["POST"])
def delete_prompt(id_prompt):
    prompt = Prompt.query.filter_by(id=id_prompt).first()
    if not prompt:
        logger.warning(f"[DELETE-PROMPT] Prompt id {id_prompt} não encontrado")
        return redirect(url_for("get_prompts_ia"))
    try:
        db.session.delete(prompt)
        db.session.commit()
        logger.success(f"[DELETE-PROMPT] Prompt deletado id {id_prompt}")
    except Exception as ex:
        logger.error(f"[DELETE-PROMPT] Erro ao deletar prompt: {ex}")
    return redirect(url_for("get_prompts_ia"))


@app.route("/delete-lead/<int:id_lead>", methods=["POST"])
def delete_lead(id_lead):
    lead = Lead.query.filter_by(id=id_lead).first()
    if not lead:
        logger.warning(f"[DELETE-LEAD] Lead id {id_lead} não encontrado")
        return redirect(url_for("index"))
    ia_id = lead.ia_id
    try:
        db.session.delete(lead)
        db.session.commit()
        logger.success(f"[DELETE-LEAD] Lead deletado id {id_lead}")
    except Exception as ex:
        logger.error(f"[DELETE-LEAD] Erro ao deletar lead: {ex}")
    return redirect(url_for("get_leads_ia", ia_id=ia_id))


@app.route("/get-leads-ia/<int:ia_id>", methods=["GET"])
def get_leads_ia(ia_id):
    leads_query = Lead.query.filter_by(ia_id=ia_id).order_by(Lead.created_at.desc()) # Changed to desc()
    search_query = request.args.get("search_query", "").strip()
    items_per_page = 6  # numero por pagina
    current_page = request.args.get("page", 1, type=int)

    # Consultar leads com filtro de busca
    leads_query = Lead.query.filter_by(ia_id=ia_id)
    if search_query:
        leads_query = leads_query.filter(
            (Lead.name.ilike(f"%{search_query}%"))
            | (Lead.phone.ilike(f"%{search_query}%"))
        )

    # Contar total de leads
    total_leads = leads_query.count()

    # Calcular total de páginas
    total_pages = (total_leads + items_per_page - 1) // items_per_page

    # Garantir que current_page seja válido
    current_page = max(1, min(current_page, total_pages))

    # Consultar leads para a página atual
    leads = (
        leads_query.order_by(Lead.created_at.desc()) # Added order_by
        .offset((current_page - 1) * items_per_page)
        .limit(items_per_page)
        .all()
    )

    leads_list = []
    lead_id = int(request.args.get("lead_id", 0))
    selected_lead = {}
    for lead in leads:
        lead_dict = {
            "id": lead.id,
            "ia_name": lead.ia.name,
            "ia_id": lead.ia.id,
            "name": lead.name,
            "phone": lead.phone,
            "message": lead.message,
            "resume": lead.resume,
            "created_at": lead.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            "updated_at": lead.updated_at,
        }
        if lead_id == lead.id:
            selected_lead = lead_dict
        leads_list.append(lead_dict)

    logger.info(
        f"[LEADS] Listando leads para IA {ia_id}: {[{'id': l['id'], 'name': l['name']} for l in leads_list]}"
    )

    return render_template(
        "lead.html",
        leads=leads_list,
        selected_lead=selected_lead,
        search_query=search_query,
        current_page=current_page,
        total_pages=total_pages,
    )

    leads_list = []
    lead_id = int(request.args.get("lead_id", 0))
    selected_lead = {}
    for lead in leads:
        lead_dict = {
            "id": lead.id,
            "ia_name": lead.ia.name,
            "ia_id": lead.ia.id,
            "name": lead.name,
            "phone": lead.phone,
            "message": lead.message,
            "resume": lead.resume,
            "created_at": lead.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            "updated_at": lead.updated_at,
        }
        if lead_id == lead.id:
            selected_lead = lead_dict
        leads_list.append(lead_dict)

    logger.info(
        f"[LEADS] Listando leads para IA {ia_id}: {[{'id': l['id'], 'name': l['name']} for l in leads_list]}"
    )

    return render_template(
        "lead.html",
        leads=leads_list,
        selected_lead=selected_lead,
        search_query=search_query,
        current_page=current_page,
        total_pages=total_pages,
    )


@app.route("/get-infos-lead/<int:ia_lead>", methods=["GET"])
def get_info_lead(ia_lead):
    lead = Lead.query.filter_by(id=ia_lead).first()
    if not lead:
        logger.warning(f"[INFO-LEAD] Lead id {ia_lead} não encontrado")
        return redirect(url_for("index"))
    lead_dict = {
        "id": lead.id,
        "ia_name": lead.ia.name,
        "ia_id": lead.ia.id,
        "name": lead.name,
        "phone": lead.phone,
        "message": lead.message,
        "resume": lead.resume,
        "created_at": lead.created_at.strftime("%d-%m-%Y %H:%M:%S"),
        "updated_at": lead.updated_at.strftime("%d-%m-%Y %H:%M:%S"),
    }
    logger.info(f"[INFO-LEAD] Exibindo informações do lead id {ia_lead}: {lead_dict}")
    return render_template("lead.html", selected_lead=lead_dict)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    logger.info("[MAIN] Aplicação iniciada")
    app.run(debug=True)
