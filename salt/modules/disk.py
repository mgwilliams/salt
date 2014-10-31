# -*- coding: utf-8 -*-
'''
Module for gathering disk information
'''
from __future__ import absolute_import

# Import python libs
import logging
import os
import re

# Import salt libs
import salt.utils
import salt.utils.decorators as decorators
from salt.exceptions import CommandExecutionError
from salt.ext.six.moves import zip
from salt.utils.monitoring import check_thresholds


__monitor__ = [
    'check_usage',
]


log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only work on POSIX-like systems
    '''
    if salt.utils.is_windows():
        return False
    return True


def _clean_flags(args, caller):
    '''
    Sanitize flags passed into df
    '''
    flags = ''
    if args is None:
        return flags
    allowed = ('a', 'B', 'h', 'H', 'i', 'k', 'l', 'P', 't', 'T', 'x', 'v')
    for flag in args:
        if flag in allowed:
            flags += flag
        else:
            raise CommandExecutionError(
                'Invalid flag passed to {0}'.format(caller)
            )
    return flags


def usage(args=None):
    '''
    Return usage information for volumes mounted on this minion

    CLI Example:

    .. code-block:: bash

        salt '*' disk.usage
    '''
    flags = _clean_flags(args, 'disk.usage')
    if not os.path.isfile('/etc/mtab') and __grains__['kernel'] == 'Linux':
        log.warn('df cannot run without /etc/mtab')
        if __grains__.get('virtual_subtype') == 'LXC':
            log.warn('df command failed and LXC detected. If you are running '
                     'a Docker container, consider linking /proc/mounts to '
                     '/etc/mtab or consider running Docker with -privileged')
        return {}
    if __grains__['kernel'] == 'Linux':
        cmd = 'df -P'
    elif __grains__['kernel'] == 'OpenBSD':
        cmd = 'df -kP'
    else:
        cmd = 'df'
    if flags:
        cmd += ' -{0}'.format(flags)
    ret = {}
    out = __salt__['cmd.run'](cmd, python_shell=False).splitlines()
    oldline = None
    for line in out:
        if not line:
            continue
        if line.startswith('Filesystem'):
            continue
        if oldline:
            line = oldline + " " + line
        comps = line.split()
        if len(comps) == 1:
            oldline = line
            continue
        else:
            oldline = None
        while not comps[1].isdigit():
            comps[0] = '{0} {1}'.format(comps[0], comps[1])
            comps.pop(1)
        try:
            if __grains__['kernel'] == 'Darwin':
                ret[comps[8]] = {
                        'filesystem': comps[0],
                        '512-blocks': comps[1],
                        'used': comps[2],
                        'available': comps[3],
                        'capacity': comps[4],
                        'iused': comps[5],
                        'ifree': comps[6],
                        '%iused': comps[7],
                }
            else:
                ret[comps[5]] = {
                        'filesystem': comps[0],
                        '1K-blocks': comps[1],
                        'used': comps[2],
                        'available': comps[3],
                        'capacity': comps[4],
                }
        except IndexError:
            log.warn('Problem parsing disk usage information')
            ret = {}
    return ret


def check_usage(mountpoint, thresholds, **kwargs):
    '''
    Return monitoring information for a mount point.
    '''
    def _fmt(num, blocksize):
        num = float(num) * blocksize
        for x in ['B', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return "%0.1f %s" % (num, x)
            num /= 1024.0

    data = {}
    for k, v in kwargs.items():
        if k.startswith('__'):
            continue
        data[k] = v

    data.update({'info': {},
                 'metrics': {},
                 'details': '',
                 'name': mountpoint})
    ret = {'result': False, 'data': data}

    info = usage()

    if mountpoint not in info:
        data['details'] = 'Disk "({0})" not mounted.'.format(mountpoint)
        return ret
    info = info[mountpoint]
    cap = int(info['capacity'].strip('%'))
    
    status, level, threshold, result = check_thresholds(cap, thresholds)

    if threshold:
        threshold = int(threshold)

    warning = ''
    if result is False:
        if level == 'high':
            warning = ' (above {0}% threshold)'.format(threshold)
        elif level == 'low':
            warning = ' (below {0}% threshold)'.format(threshold)

    data['details'] = ('Disk "{0}" is at {1}% '
                       'capacity{2}.').format(mountpoint, cap,
                                              warning)
    data['status'] = status

    if level:
        data['threshold'] = [level, threshold]

    if __grains__['kernel'] == 'Darwin':
        blocksize = 512
        size = info['512-blocks']
    else:
        blocksize = 1024
        size = info['1K-blocks']
        
    data['info'] = {'size': _fmt(size, blocksize),
                    'used': _fmt(info['used'], blocksize),
                    'available': _fmt(info['available'], blocksize),
                    'capacity': info['capacity'],
                    'filesystem': info['filesystem']}

    data['metrics'] = {'size_kb': info['1K-blocks'],
                       'used_kb': info['used'],
                       'available_kb': info['available'],
                       'percent_capacity': cap}
    return ret


def inodeusage(args=None):
    '''
    Return inode usage information for volumes mounted on this minion

    CLI Example:

    .. code-block:: bash

        salt '*' disk.inodeusage
    '''
    flags = _clean_flags(args, 'disk.inodeusage')
    cmd = 'df -iP'
    if flags:
        cmd += ' -{0}'.format(flags)
    ret = {}
    out = __salt__['cmd.run'](cmd, python_shell=False).splitlines()
    for line in out:
        if line.startswith('Filesystem'):
            continue
        comps = line.split()
        # Don't choke on empty lines
        if not comps:
            continue

        try:
            if __grains__['kernel'] == 'OpenBSD':
                ret[comps[8]] = {
                    'inodes': int(comps[5]) + int(comps[6]),
                    'used': comps[5],
                    'free': comps[6],
                    'use': comps[7],
                    'filesystem': comps[0],
                }
            else:
                ret[comps[5]] = {
                    'inodes': comps[1],
                    'used': comps[2],
                    'free': comps[3],
                    'use': comps[4],
                    'filesystem': comps[0],
                }
        except (IndexError, ValueError):
            log.warn('Problem parsing inode usage information')
            ret = {}
    return ret


def percent(args=None):
    '''
    Return partition information for volumes mounted on this minion

    CLI Example:

    .. code-block:: bash

        salt '*' disk.percent /var
    '''
    if __grains__['kernel'] == 'Linux':
        cmd = 'df -P'
    elif __grains__['kernel'] == 'OpenBSD':
        cmd = 'df -kP'
    else:
        cmd = 'df'
    ret = {}
    out = __salt__['cmd.run'](cmd, python_shell=False).splitlines()
    for line in out:
        if not line:
            continue
        if line.startswith('Filesystem'):
            continue
        comps = line.split()
        while not comps[1].isdigit():
            comps[0] = '{0} {1}'.format(comps[0], comps[1])
            comps.pop(1)
        try:
            if __grains__['kernel'] == 'Darwin':
                ret[comps[8]] = comps[4]
            else:
                ret[comps[5]] = comps[4]
        except IndexError:
            log.warn('Problem parsing disk usage information')
            ret = {}
    if args:
        return ret[args]
    else:
        return ret


@decorators.which('blkid')
def blkid(device=None):
    '''
    Return block device attributes: UUID, LABEL, etc.  This function only works
    on systems where blkid is available.

    CLI Example:

    .. code-block:: bash

        salt '*' disk.blkid
        salt '*' disk.blkid /dev/sda
    '''
    args = ""
    if device:
        args = " " + device

    ret = {}
    for line in __salt__['cmd.run_stdout']('blkid' + args, python_shell=False).split('\n'):
        if not line:
            continue
        comps = line.split()
        device = comps[0][:-1]
        info = {}
        device_attributes = re.split(('\"*\"'), line.partition(' ')[2])
        for key, value in zip(*[iter(device_attributes)]*2):
            key = key.strip('=').strip(' ')
            info[key] = value.strip('"')
        ret[device] = info

    return ret
