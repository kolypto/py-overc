from datetime import datetime, timedelta

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import object_session
from sqlalchemy.sql.schema import Column, ColumnDefault
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql.sqltypes import Boolean, SmallInteger, Integer, BigInteger, Float, String, Text, Unicode, UnicodeText, Binary, DateTime, Enum
from sqlalchemy.orm import relationship, backref, remote, foreign

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
    ip = Column(String(46), nullable=True, doc='IP-address')

    __table_args__ = (
        UniqueConstraint(name),
    )

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.title or self.name

class Service(Base):
    """ A service being monitored """
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, nullable=False)
    server_id = Column(Integer, ForeignKey(Server.id, ondelete='CASCADE'), nullable=False, doc="Server id")

    period = Column(Integer, nullable=True, doc="Expected reporting period, seconds")
    timed_out = Column(Boolean, nullable=False, default=False, doc="Is currently timed out?")

    name = Column(String(32), nullable=False, doc="Service machine name (as reported from the remote)")
    title = Column(Unicode(64), nullable=False, default=u'', doc="Service title")

    server = relationship(Server, foreign_keys=server_id, backref=backref('services', passive_deletes=True))

    __table_args__ = (
        UniqueConstraint(server_id, name),
    )

    def update_timed_out(self):
        """ Update service's `timed_out` field
        :returns: How long ago it was last seen (if timed out)
        :rtype: timedelta
        """
        if not self.state:
            return timedelta(seconds=0)
        dt = datetime.utcnow() - self.state.rtime
        self.timed_out = dt > timedelta(seconds=self.period)
        return dt

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.title or self.name


class state_t(int):
    """ Comparable enum for state """
    states = ('OK', 'WARN', 'FAIL',   'UNK')

    OK = 0
    WARN = 1
    FAIL = 2
    UNK = 3

    def __new__(cls, state):
        intval = cls.states.index(state)
        return super(state_t, cls).__new__(cls, intval)

    @classmethod
    def is_valid(cls, state):
        """ Test whether the state value is valid """
        try:
            cls.states.index(state)
            return True
        except ValueError:
            return False



class ServiceState(Base):
    """ Service state """
    __tablename__ = 'service_states'

    id = Column(BigInteger, primary_key=True, nullable=False)
    service_id = Column(Integer, ForeignKey(Service.id, ondelete='CASCADE'), nullable=False, doc="Service id")

    checked = Column(Boolean, nullable=False, default=False, doc="State checked (alerts created)?")
    rtime = Column(DateTime, default=datetime.utcnow, doc="Received time")

    state = Column(Enum(*state_t.states, name='service_state'), default='UNK', nullable=False, doc='Service status')
    info = Column(UnicodeText, nullable=False, doc='Service info')

    service = relationship(Service, foreign_keys=service_id, backref=backref('states', passive_deletes=True))

    __table_args__ = (
        Index('idx_serviceid_rtime_id', service_id, rtime, id),
        Index('idx_checked', checked)
    )

    @property
    def prev(self):
        # FIXME: learn how to apply .limit() to the relationship() query and uncomment the definition below
        return object_session(self)\
            .query(ServiceState)\
            .filter(
                ServiceState.id < self.id,
                ServiceState.service_id == self.service_id
            )\
            .order_by(ServiceState.id.desc())\
            .first()

    # prev = relationship("ServiceState", viewonly=True, uselist=False,
    #                                  primaryjoin=and_(
    #                                      remote(id) < foreign(id),
    #                                      remote(service_id) == foreign(service_id)
    #                                  ), order_by=id.desc(), doc="Previous state, if any")


latest_state = select([func.max(ServiceState.id)]). \
    where(Service.id == ServiceState.service_id). \
    correlate(Service). \
    as_scalar()
Service.state = relationship(ServiceState, viewonly=True, uselist=False,
                             primaryjoin=and_(
                                 ServiceState.id == latest_state,
                                 ServiceState.service_id == Service.id
                             ), doc="Current service state")


class Alert(Base):
    """ Reported alerts """
    __tablename__ = 'alerts'

    id = Column(BigInteger, primary_key=True, nullable=False)
    server_id = Column(Integer, ForeignKey(Server.id, ondelete='CASCADE'), nullable=True, doc="Server id")
    service_id = Column(Integer, ForeignKey(Service.id, ondelete='CASCADE'), nullable=True, doc="Service id")
    service_state_id = Column(BigInteger, ForeignKey(ServiceState.id, ondelete='SET NULL'), nullable=True, doc="Service state id (if any)")

    reported = Column(Boolean, nullable=False, default=False, doc="Alert reported (notifications sent)?")
    ctime = Column(DateTime, default=datetime.utcnow, doc="Creation time")

    channel = Column(String(32), nullable=False, doc="Alert channel")
    event = Column(String(32), nullable=False, doc="Alert event")
    message = Column(UnicodeText, nullable=False, doc="Alert details")

    server = relationship(Server, foreign_keys=server_id, backref=backref('alerts', passive_deletes=True, order_by=id.desc()))
    service = relationship(Service, foreign_keys=service_id, backref=backref('alerts', passive_deletes=True, order_by=id.desc()))
    service_state = relationship(ServiceState, foreign_keys=service_state_id, uselist=False, backref=backref('alerts', passive_deletes=True, order_by=id.desc()))

    __table_args__ = (
        Index('idx_reported', reported),
    )

    def __unicode__(self):
        server_service = u' '.join(filter(lambda x: x is not None, [
            unicode(self.server) if self.server else None,
            unicode(self.service) if self.service else None,
        ]))
        return u''.join([
            # server `service`:
            u'{}: '.format(server_service) if server_service else u'',
            # [channel/event]
            u'[{}/{}] '.format(self.channel, self.event),
            # message
            self.message
        ])

    @property
    def severity(self):
        """ Alert severity as a number
        :return: Number: {0..3}
        :rtype: int
        """
        return {
            'plugin/online': state_t.OK,
            'plugin/offline': state_t.FAIL,

            'service:state/OK': state_t.OK,
            'service:state/WARN': state_t.WARN,
            'service:state/FAIL': state_t.FAIL,
            'service:state/UNK': state_t.UNK,

            'api/alert': state_t.FAIL
        }.get(
            '{}/{}'.format(self.channel, self.event),
            state_t.FAIL
        )
