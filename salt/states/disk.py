# -*- coding: utf-8 -*-
'''
Disk monitoring state

Monitor the state of disk resources
'''
from __future__ import absolute_import

# Import salt libs
from salt.ext.six import string_types


__monitor__ = [
    'status',
]


def status(name,
           maximum=None,
           minimum=None,
           thresholds=None,
           **kwargs):
    '''
    Return the current disk usage stats for the named mount point
    '''
    # Monitoring state, no changes will be made so no test interface needed
    ret = {'name': name,
           'result': False,
           'comment': '',
           'changes': {},
           'data': {}}

    if thresholds is None:
        thresholds = [
            {'failure':
                {'minimum': minimum,
                 'maximum': maximum,
                 'result': False}},
        ]

    r = __salt__['disk.check_usage'](name, thresholds, **kwargs)
    ret['data'] = r['data']
    ret['result'] = r['result']
    ret['data']['check'] = 'disk.status'
    if r['data']['status']['changed']:
        ret['changes'] = {'status': r['data']['status']['current']}
    ret['comment'] = ret['data']['details']
    return ret
