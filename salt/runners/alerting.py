# -*- coding: utf-8 -*-

# Import python libs
import logging

# Import salt libs
import salt.loader


log = logging.getLogger(__name__)

# cache the utility modules
UTILS = None


def __virtual__():
    return True


def _utils():
    '''
    Load the utility modules exactly once.
    '''
    global UTILS

    if UTILS is None:
        UTILS = salt.loader.utils(__opts__)

    return UTILS


def onchange(minion_id, data, config):
    log.debug('onchange')
    utils = _utils()

    name = data['name']
    check = data['check']
    status = data['status']
    check = '{0} ({1})'.format(check, name)

    profiles = data.get('alert_profiles',
                        config.get('default', []))
    for p in profiles:
        profile = config['profiles'][p]
        for service in profile:
            modcfg = service.values()[0].get('profile', None)
            f = '{0}.alert'.format(service.keys()[0])
            log.warning(data)
            r = utils[f](modcfg, minion_id, check,
                     status['current'],
                     data['details'],
                     data['info'],
                     failure=status['failure'])
            log.warning(r)
    return data
