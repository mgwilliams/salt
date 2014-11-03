# Import python libs
import logging


log = logging.getLogger(__name__)


def returner(ret):
    mopts = __opts__.get('monitoring', {})
    if mopts.get('direct_return', True):
        return __salt__['event.fire_master'](ret, 'salt/monitor/' + ret['id'])
    else:
        return __salt__['event.fire_master'](ret['jid'],
                                             'salt/monitor/' + ret['id'])
    return
