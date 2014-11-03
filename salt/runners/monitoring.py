'''
Monitoring Runner
'''

# Import python libs
import logging

# Import salt libs
import salt.payload
import salt.loader
from salt._compat import string_types


db = '/var/lib/salt/master/monitoring.db/'
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


def process_checks(minion_id, data):
    utils = _utils()

    mopts = __opts__.get('monitoring', {})
    profiles = __opts__['monitoring']['alert_profiles']['devops']

    if isinstance(data, string_types):
        job_cache = mopts.get('job_cache')
        if not job_cache:
            log.warning('No job cache and no return data. '
                        'Nothing to be done.')
            return
        data = __salt__['jobs.lookup_jid'](data, ext_source=job_cache)
        data = data[minion_id]
    else:
        data = data['return']

    for _, result in data.items():
        result = result['data']
        name = result['name']
        check = result['check']

        if result['status']['changed'] is True:
            check = '{0} ({1})'.format(check, name)
            for x in profiles:
                for service, info in x.items():
                    profile = info['profile']
                    status = result['status']
                    utils['bigpanda.alert'](profile, minion_id, check,
                                            status['current'],
                                            result['message'],
                                            result['info'],
                                            failure=status['failure'])
