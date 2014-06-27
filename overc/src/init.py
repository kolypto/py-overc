from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def init_sqlalchemy(app, connect):
    """ Init SqlAlchemy

        :param app: Flask application
        :type app: Flask
        :param connect: Database connection string
        :type connect: str
        :rtype: (sqlalchemy.engine.Engine, sqlalchemy.orm.session.Session)
        """
    # Connect
    engine = create_engine(connect, convert_unicode=True)
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    # Models
    from overc.lib.db.models import Base
    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)  # TODO: remove automatic table creation

    # teardown
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    # Finish
    return (engine, db_session)
