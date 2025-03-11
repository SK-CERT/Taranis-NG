"""Create, update and delete Collector, Bot, Presenter and Publisher parameters."""

from model.collectors_node import CollectorsNode
from model.collector import Collector, CollectorParameter
from model.presenters_node import PresentersNode
from model.presenter import Presenter, PresenterParameter
from model.publishers_node import PublishersNode
from model.publisher import Publisher, PublisherParameter
from model.bots_node import BotsNode
from model.bot import Bot, BotParameter
from model.parameter import Parameter
from model.parameter_value import ParameterValue
from model.osint_source import OSINTSource, OSINTSourceParameterValue
from model.bot_preset import BotPreset, BotPresetParameterValue
from model.product_type import ProductType, ProductTypeParameterValue
from model.publisher_preset import PublisherPreset, PublisherPresetParameterValue
from shared.config_collector import ConfigCollector
from shared.config_bot import ConfigBot
from shared.config_presenter import ConfigPresenter
from shared.config_publisher import ConfigPublisher
from model import attribute  # noqa: F401  Don't remove this line otherwise relationship problems
from sqlalchemy.orm import declarative_base, Session


Base = declarative_base()


def regenerate_all(connection):
    """Regenerate all nodes.

    Args:
        connection: Connection to DTB.
    """
    session = Session(bind=connection)
    RegenerateParameters("bots", session)
    RegenerateParameters("collectors", session)
    RegenerateParameters("presenters", session)
    RegenerateParameters("publishers", session)


# this allow us add new module/parameters to nodes without deleting and manually recreating it (we don't loose existing data)
# existing objects like OSINT sources, Bots presets... that depend on these parameters stay untouched and need to be updated/recrated manually
def RegenerateParameters(type, session):
    """
    Create new, update existing, and delete old Collector, Bot, Presenter and Publisher parameters.

    Args:
        type (str): The type of module to regenerate. Valid values are "collectors", "bots", "presenters", and "publishers".
        session (sqlalchemy.orm.session.Session): The SQLAlchemy session to use for database operations.
    """
    try:
        match type:
            case "collectors":
                def_modules = ConfigCollector().modules
                db_nodes = session.query(CollectorsNode).all()
                class_module = Collector
            case "bots":
                def_modules = ConfigBot().modules
                db_nodes = session.query(BotsNode).all()
                class_module = Bot
            case "presenters":
                def_modules = ConfigPresenter().modules
                db_nodes = session.query(PresentersNode).all()
                class_module = Presenter
            case "publishers":
                def_modules = ConfigPublisher().modules
                db_nodes = session.query(PublishersNode).all()
                class_module = Publisher
            case _:
                print(f"ERROR: Invalid module type '{type}' to regenerate", flush=True)
                return

        for db_node in db_nodes:
            print(f"Regenarating parameters for node: {db_node.name}", flush=True)
            # create/update
            db_modules = session.query(class_module).filter_by(node_id=db_node.id).all()
            for def_mod in def_modules:
                # create/update module
                db_mod = next((m for m in db_modules if m.type == def_mod.type), None)
                if not db_mod:
                    print(f"+++  {def_mod.type}", flush=True)
                    db_mod = class_module(name=def_mod.name, description=def_mod.description, type=def_mod.type, parameters=[])
                    db_mod.node_id = db_node.id
                    session.add(db_mod)
                else:
                    db_mod.name = def_mod.name
                    db_mod.description = def_mod.description
                session.commit()
                # create/update module parameters
                for def_par in def_mod.parameters:
                    db_par = next((p for p in db_mod.parameters if p.key == def_par.key), None)
                    if not db_par:
                        print(f"+++  {def_mod.type}.{def_par.key}", flush=True)
                        db_par = Parameter(def_par.key, def_par.name, def_par.description, def_par.type.name, def_par.default_value)
                        session.add(db_par)
                        session.commit()
                        db_mod_par = get_new_mod_param(type, db_mod.id, db_par.id)
                        session.add(db_mod_par)
                    else:
                        db_par.name = def_par.name
                        db_par.description = def_par.description
                        db_par.type = def_par.type.name
                        db_par.default_value = def_par.default_value
                    session.commit()
            # delete old module/parameters
            db_modules = session.query(class_module).filter_by(node_id=db_node.id).all()
            for db_mod in db_modules:
                def_mod = next((m for m in def_modules if m.type == db_mod.type), None)
                if not def_mod:
                    for db_par in db_mod.parameters:
                        print(f"---  {db_mod.type}.{db_par.key}", flush=True)
                        # this delete via DB constraints also osint_source_parameter_value, bot_preset_parameter_value,
                        # publisher_preset_parameter_value, product_type_parameter_value tables
                        session.delete(db_par)
                    print(f"---  {db_mod.type}", flush=True)
                    session.delete(db_mod)
                else:
                    for db_par in db_mod.parameters:
                        if not any(m.key == db_par.key for m in def_mod.parameters):
                            print(f"---  {db_mod.type}.{db_par.key}", flush=True)
                            session.delete(db_par)
            session.commit()

        # Add new parameter_values in depending objects, delete was processed up via db constraints
        added = 0
        match type:
            case "collectors":
                caption = "OSINT Sources"
                query = session.query(Collector, OSINTSource)
                sources = query.join(OSINTSource, OSINTSource.collector_id == Collector.id).all()
                for col, osint in sources:
                    def_mod = next((m for m in def_modules if m.type == col.type), None)
                    if def_mod:
                        query = session.query(OSINTSourceParameterValue, ParameterValue, Parameter)
                        query = query.join(ParameterValue, ParameterValue.id == OSINTSourceParameterValue.parameter_value_id)
                        query = query.join(Parameter, Parameter.id == ParameterValue.parameter_id)
                        results = query.filter(OSINTSourceParameterValue.osint_source_id == osint.id).all()

                        db_param_lookup = {param.key: param for _, _, param in results}
                        for def_par in def_mod.parameters:
                            if def_par.key not in db_param_lookup:
                                print(f"+++  {def_par.key}: {osint.name}", flush=True)
                                db_param = next((p for p in col.parameters if p.key == def_par.key), None)
                                if db_param:
                                    added += 1
                                    db_param_value = ParameterValue(def_par.default_value, db_param)
                                    osint.parameter_values.append(db_param_value)
            case "bots":
                caption = "Bot Presets"
                query = session.query(Bot, BotPreset)
                bots = query.join(BotPreset, BotPreset.bot_id == Bot.id).all()
                for bot, preset in bots:
                    def_mod = next((m for m in def_modules if m.type == bot.type), None)
                    if def_mod:
                        query = session.query(BotPresetParameterValue, ParameterValue, Parameter)
                        query = query.join(ParameterValue, ParameterValue.id == BotPresetParameterValue.parameter_value_id)
                        query = query.join(Parameter, Parameter.id == ParameterValue.parameter_id)
                        results = query.filter(BotPresetParameterValue.bot_preset_id == preset.id).all()

                        db_param_lookup = {param.key: param for _, _, param in results}
                        for def_par in def_mod.parameters:
                            if def_par.key not in db_param_lookup:
                                print(f"+++  {def_par.key}: {preset.name}", flush=True)
                                db_param = next((p for p in bot.parameters if p.key == def_par.key), None)
                                if db_param:
                                    added += 1
                                    db_param_value = ParameterValue(def_par.default_value, db_param)
                                    preset.parameter_values.append(db_param_value)
            case "presenters":
                caption = "Product Types"
                query = session.query(Presenter, ProductType)
                product_types = query.join(ProductType, ProductType.presenter_id == Presenter.id).all()
                for presenter, prod_type in product_types:
                    def_mod = next((m for m in def_modules if m.type == presenter.type), None)
                    if def_mod:
                        query = session.query(ProductTypeParameterValue, ParameterValue, Parameter)
                        query = query.join(ParameterValue, ParameterValue.id == ProductTypeParameterValue.parameter_value_id)
                        query = query.join(Parameter, Parameter.id == ParameterValue.parameter_id)
                        results = query.filter(ProductTypeParameterValue.product_type_id == prod_type.id).all()

                        db_param_lookup = {param.key: param for _, _, param in results}
                        for def_par in def_mod.parameters:
                            if def_par.key not in db_param_lookup:
                                print(f"+++  {def_par.key}: {prod_type.title}", flush=True)
                                db_param = next((p for p in presenter.parameters if p.key == def_par.key), None)
                                if db_param:
                                    added += 1
                                    db_param_value = ParameterValue(def_par.default_value, db_param)
                                    prod_type.parameter_values.append(db_param_value)
            case "publishers":
                caption = "Publisher Presets"
                query = session.query(Publisher, PublisherPreset)
                publisher_presets = query.join(PublisherPreset, PublisherPreset.publisher_id == Publisher.id).all()
                for pub, preset in publisher_presets:
                    def_mod = next((m for m in def_modules if m.type == pub.type), None)
                    if def_mod:
                        query = session.query(PublisherPresetParameterValue, ParameterValue, Parameter)
                        query = query.join(ParameterValue, ParameterValue.id == PublisherPresetParameterValue.parameter_value_id)
                        query = query.join(Parameter, Parameter.id == ParameterValue.parameter_id)
                        results = query.filter(PublisherPresetParameterValue.publisher_preset_id == preset.id).all()

                        db_param_lookup = {param.key: param for _, _, param in results}
                        for def_par in def_mod.parameters:
                            if def_par.key not in db_param_lookup:
                                print(f"+++  {def_par.key}: {preset.name}", flush=True)
                                db_param = next((p for p in pub.parameters if p.key == def_par.key), None)
                                if db_param:
                                    added += 1
                                    db_param_value = ParameterValue(def_par.default_value, db_param)
                                    preset.parameter_values.append(db_param_value)
            case _:
                print(f"ERROR: Invalid module type '{type}' to refresh parameters in depending objects", flush=True)
                return
        session.commit()
        print(f"{caption} parameters: {added} added", flush=True)

    except Exception as e:
        session.rollback()
        print(f"Regeneration error: {e}", flush=True)
        raise Exception("Regeneration failed")  # don't allow migration process continue to next step


def get_new_mod_param(type, module_id, parameter_id):
    """
    Create a new module parameter based on the type.

    Args:
        type (str): The type of module. Valid values are "collectors", "bots", "presenters", and "publishers".
        module_id (int): The ID of the module.
        parameter_id (int): The ID of the parameter.

    Returns:
        An instance of the appropriate parameter class based on the type, or None if the type is invalid.
    """
    match type:
        case "collectors":
            return CollectorParameter(collector_id=module_id, parameter_id=parameter_id)
        case "bots":
            return BotParameter(bot_id=module_id, parameter_id=parameter_id)
        case "presenters":
            return PresenterParameter(presenter_id=module_id, parameter_id=parameter_id)
        case "publishers":
            return PublisherParameter(publisher_id=module_id, parameter_id=parameter_id)
        case _:
            print(f"ERROR: Invalid type '{type}' to create module parameter: {type}", flush=True)
            return None
