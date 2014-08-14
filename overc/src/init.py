from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def init_db_engine(connect):
    """ Init Sqlalchemy engine
    :param connect: Database connection string
    :type connect: str
    :rtype: sqlalchemy.engine.Engine
    """
    return create_engine(connect, convert_unicode=True)

def init_db_session(engine):
    """ Init DB session
    :param engine: Engine
    :type engine: sqlalchemy.engine.Engine
    :rtype: sqlalchemy.orm.scoped_session
    """
    Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    # Models
    from overc.lib.db.models import Base
    Base.query = Session.query_property()
    Base.metadata.create_all(bind=engine)  # TODO: remove automatic table creation

    return Session


def init_db_session_for_flask(engine, app):
    """ Init DB session for Flask app
    :param engine: Engine
    :type engine: sqlalchemy.engine.Engine
    :param app: Flask application
    :type app: Flask
    :rtype: sqlalchemy.orm.session.scoped_session
    """
    Session = init_db_session(engine)

    # Tear-down
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        Session.remove()

    return Session
