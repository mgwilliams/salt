'''
Monitoring Runner
'''

# Import python libs
import logging

# Import salt libs
from salt._compat import string_types


db = '/var/lib/salt/master/monitoring.db/'
log = logging.getLogger(__name__)


def process_checks(minion_id, data):

    mopts = __opts__.get('monitoring', {})
    onchange = mopts.get('onchange', [])

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

        if True: #result['status']['changed'] is True:
            for r in onchange:
                result = __salt__[r.keys()[0]](minion_id, result,
                                               r.values()[0])
