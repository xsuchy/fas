# -*- coding: utf-8 -*-
from turbogears import identity
from turbogears import config

# A list of functions to call to get the various entries that
#   should be shown in the sidebar
entryfuncs = []

# Generator that returns each of the entries
def getEntries():
    for f in entryfuncs:
        entries = f()
        for entry in entries:
            yield entry


# Stock entries used by FAS everywhere
def stockentries():
    entries = []
    if not identity.current.anonymous and (
            config.get('admingroup') in identity.current.groups
            or 'sysadmin' in identity.current.groups # this is FedoraProject specific
        ):
        entries.append((_('New Group'), '/group/new'))
        entries.append((_('User List'), '/user/list'))
    if not identity.current.anonymous:
        entries.append((_('Group List'), '/group/list/A*'))
        entries.append((_('Join a Group'), '/group/list/A*'))
    return entries

entryfuncs.append(stockentries)
