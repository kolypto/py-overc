from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import Column, ColumnDefault
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint, Index
from sqlalchemy import Boolean, SmallInteger, Integer, BigInteger, Float, String, Text, Unicode, UnicodeText, Binary, DateTime, Enum
from sqlalchemy.orm import relationship

from sqlalchemy.sql.expression import select, and_, func

Base = declarative_base()

# TODO: server grouping
# TODO: service grouping

class Server(Base):
    """ A server being monitored """
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(Unicode(64), nullable=False, doc="Server title")
    name = Column(String(32), nullable=False, doc="Server machine name (as reported from the remote)")
    key = Column(String(32), nullable=False, doc="Authentication key")

    __table_args__ = (
        UniqueConstraint(name),
    )



class Service(Base):
    """ A service being monitored """
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, nullable=False)
    server_id = Column(Integer, ForeignKey(Server.id, ondelete='CASCADE'), nullable=False, doc="Server id")

    period = Column(Integer, nullable=True, doc="Expected reporting period, seconds")

    name = Column(String(32), nullable=False, doc="Service machine name (as reported from the remote)")
    title = Column(Unicode(64), nullable=False, default=u'', doc="Service title")

    server = relationship(Server, foreign_keys=server_id, backref='services')

    __table_args__ = (
        UniqueConstraint(name),
        Index('idx_serverid', server_id),
    )



class ServiceState(Base):
    """ Service state """
    __tablename__ = 'service_states'

    id = Column(BigInteger, primary_key=True, nullable=False)
    service_id = Column(Integer, ForeignKey(Service.id, ondelete='CASCADE'), nullable=False, doc="Service id")

    checked = Column(Boolean, nullable=False, default=False, doc="State checked (alerts created)?")
    rtime = Column(DateTime, default=datetime.utcnow, doc="Received time")

    state = Column(Enum('', 'OK', 'WARN', 'FAIL', name='service_state'), default='', nullable=False, doc='Service status')
    info = Column(UnicodeText, nullable=False, doc='Service info')

    service = relationship(Service, foreign_keys=service_id, backref='states')

    __table_args__ = (
        Index('idx_serviceid_rtime', service_id, rtime),
        Index('idx_checked', checked)
    )


latest_state = select([func.max(ServiceState.id)]). \
    where(Service.id == ServiceState.service_id). \
    correlate(Service). \
    as_scalar()
Service.state = relationship(ServiceState, viewonly=True,
                             primaryjoin=and_(
                                 ServiceState.id == latest_state,
                                 ServiceState.service_id == Service.id
                             ), uselist=False)



class Alert(Base):
    """ Reported alerts """
    __tablename__ = 'alerts'

    id = Column(BigInteger, primary_key=True, nullable=False)
    server_id = Column(Integer, ForeignKey(Server.id, ondelete='CASCADE'), nullable=True, doc="Server id")
    service_id = Column(Integer, ForeignKey(Service.id, ondelete='CASCADE'), nullable=True, doc="Service id")

    reported = Column(Boolean, nullable=False, default=False, doc="Alert reported (notifications sent)?")
    ctime = Column(DateTime, default=datetime.utcnow, doc="Creation time")

    channel = Column(String(32), nullable=False, doc="Alert channel")
    event = Column(String(32), nullable=False, doc="Alert event")

    title = Column(UnicodeText, nullable=False, doc="Title")
    message = Column(UnicodeText, nullable=False, doc="Alert details")

    server = relationship(Server, foreign_keys=server_id, backref='alerts')
    service = relationship(Service, foreign_keys=service_id, backref='alerts')

    __table_args__ = (
        Index('idx_reported', reported),
    )



class Notification(Base):
    """ Notifications configuration """

    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, nullable=False)
    script = Column(String(255), nullable=False, doc="Notification script to invoke")
    arguments = Column(String(255), nullable=False, doc="Notification script arguments")
