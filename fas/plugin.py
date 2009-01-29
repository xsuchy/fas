# -*- coding: utf-8 -*-
#
# Copyright © 2008 Ignacio Vazquez-Abrams All rights reserved.
# Copyright © 2008 Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Author(s): Ignacio Vazquez-Abrams <ivazquez@fedoraproject.org>
#            Yaakov M. Nemoy <ynemoy@redhat.com>
#

import turbogears.controllers as controllers
import turbogears.startup as startup
import pkg_resources

from collections import deque

class BadPathException(Exception):
    pass

class PathUnavailableException(Exception):
    pass

class PluginMissingException(Exception):
    pass

class PluginControllerMixin(object):
    def requestpath(controller, plugin, path):
        '''Used by a plugin to request addition to a path'''
        if isinstance(path, basestring):
            path = path.split('/')
            if len(path) > 0 and len(path[0]) == 0:
                del path[0]
        if len(path) == 0:
            raise BadPathException('Empty path specified')
        frag = getattr(controller, path[0], None)
        if frag is None:
            p = plugin()
            p._root = controller
            setattr(controller, path[0], p)
            controller.plugins.append(p)
            return '/' + path[0] + '/', p
        if hasattr(frag, 'requestpath'):
            if len(path) > 1:
                return '/' + path[0] + frag.requestpath(plugin, path[1:])
            raise PathUnavailableException('Path not deep enough')
        raise PathUnavailableException('Path already in use')

    def getpluginident(controller):
        '''The string returned by this method is prepended to ".plugins"
        in order to search for plugins'''
        raise NotImplementedError('Whoops! Forgot to override getpluginident!')

    def loadplugins(controller):
        for pluginEntry in pkg_resources.iter_entry_points('%s.plugins' %
            controller.getpluginident()): 
            pluginClass = pluginEntry.load() 
            if hasattr(pluginClass, 'initPlugin'): 
                pluginClass.initPlugin(controller)
        startup.call_on_shutdown.append(controller.unloadplugins)

    def unloadplugins(controller):
        for plugin in controller.plugins:
            if hasattr(plugin, 'delPlugin'):
                plugin.delPlugin(controller)

class RootController(controllers.RootController, PluginControllerMixin):
    def __init__(self, *args, **kwargs):
        super(controllers.RootController, self).__init__(*args, **kwargs)
        PluginControllerMixin.__init__(self, *args, **kwargs)
        self.plugins = []
        self.loadplugins()
    

class Controller(controllers.Controller, PluginControllerMixin):
    def __init__(self, *args, **kwargs):
        super(controllers.Controller, self).__init__(*args, **kwargs)
        self.plugins = []
        self.loadplugins()

# This code is airlifted from the Python 2.5 codebase
# NB: The Python License is compatible with the GPL, so this is kosher
WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
WRAPPER_UPDATES = ('__dict__',)
def update_wrapper(wrapper,
                   wrapped,
                   assigned = WRAPPER_ASSIGNMENTS,
                   updated = WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function

       wrapper is the function to be updated
       wrapped is the original function
       assigned is a tuple naming the attributes assigned directly
       from the wrapped function to the wrapper function (defaults to
       functools.WRAPPER_ASSIGNMENTS)
       updated is a tuple naming the attributes off the wrapper that
       are updated with the corresponding attribute from the wrapped
       function (defaults to functools.WRAPPER_UPDATES)
    """
    for attr in assigned:
        setattr(wrapper, attr, getattr(wrapped, attr))
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper

def pluggable(func):
    '''Marks a function as pluginable'''
    def set_plugs(x):
        func.__plugs__ = x
    func._set_plugs = set_plugs
    def get_plugs():
        return func.__plugs__
    func._get_plugs = get_plugs
    func.__plugs__ = DependencyChain()
    def wrapper(*args, **keys):
        try:
            functions = func.__plugs__.exec_functions()
        except MissingDepedencyException, e:
            raise PluginMissingException('The plugin %s is missing. It is required for the following plugins: %s' % (e.reason, str(func.__plugs__.rltable[e.reason])))
    return update_wrapper(wrapper, func)

def plugin(func, aspect, name, dependencies=[]):
    '''A decorator that adds a plugin to the dependency chain

    func is the function to run at the right time
    the name is the name of the plugin adding an intercept function
    dependencies are a list of plugins that must be run first before this one can run
    '''
    func._get_plugs().add_dependency(name, aspect, dependencies)
    return func

class FunctionTable(object):
    '''A convenient way of threading through a list of functions'''
    def __init__(self, functions):
        self.functions = deque(functions)
    
    def __call__(self, *args, **keys):
        if len(self.functions) > 1:
            return self.functions.pop()(self, *args, **keys)
        else:
            new_func = self.functions.pop()
            from inspect import getargspec
            vals = deque(args)
            for arg in getargspec(new_func)[0][1:]:
                keys[arg] = vals.popleft()
            return new_func(*args, **keys)

class RLTable(object):
    '''A reverse lookup table'''
    def __init__(self):
        self.table = dict()

    def add_r_depend(self, depender, dependee):
        if depdendee in self.table:
            self.table[dependee].append(depender)
        else:
            self.table[dependee] = [depender]

    def add_many_r_depends(self, depender, dependees):
        for dependee in dependees:
            self.add_r_depend(depender, dependee)

class DependencyChain(object):
    def __init__(self):
        self.dependencies = dict()
        self.exec_order = list()
        self.rltable = RLTable()
    
    def add_dependency(self, name, func, dependencies=[]):
        if name in self.dependencies:
            return
        new_dependencies = realize_dependencies(self.dependencies, dependencies)
        if Missing(name) in self.exec_order:
            replace(self.exec_order, Missing(name), Present(name))
        else:
            self.exec_order.append(Present(name))
        a, b = split(self.exec_order, Present(name))
        a = update_dependencies(a, new_dependencies)
        self.exec_order = a + b
        self.dependencies[Present(name)] = (func, dependencies)
        self.rltable.add_many_r_depends(name, dependencies)
    
    def exec_functions(self):
        if not all(self.exec_order, lambda x: type(x) is Present):
            raise MissingDepedencyException(one(self.exec_order, lambda x: type(x) is Missing))
        return [self.dependencies[name][0] for name in self.exec_order]

def MissingDepedencyException(Exception):
    '''flags that not all depedencies have been encountered'''
    def __init__(self, reason):
        self.reason = reason

def all(iter, cond):
    '''if all items in iter are true according to the condition, return true, othrewise false'''
    for elem in iter:
        if not cond(elem):
            return False
    return True

def one(iter, cond):
    '''returns the first item in an iter that is true under the condition'''
    for elem in iter:
        if cond(elem):
            return elem

#These four classes are meant to be immutable singletons, similar to data types in Haskell        
class MetaMarked(type):
    '''Provides a suitable repr function for all marked strings'''
    def __init__(cls, name, bases, attrs):
        def __repr__(self):
            return name + "(" + repr(super(cls, self)) + ")"
        cls.__repr__ = __repr__
        cls.names = dict()

class Dependency(str):
    '''Base class for handling whether a depedency is present or missing'''
    __metaclass__ = MetaMarked
    def __new__(cls, name):
        if name in cls.names:
            return cls.names[name]
        else:
            ret = cls.names[name] = str.__new__(cls, name)
            return ret
    names = dict()

class Missing(Dependency): 
    '''connotes a dependency that is not present'''
    pass

class Present(Dependency):
    '''connotes a dependency that is present'''
    pass

def split(l, item):
    '''Splits a list on the first occurence of an item.'''
    index = l.index(item)
    return l[:index], l[index:]

def realize_dependencies(loaded, new):
    '''Converts a list of dependencies into a marked list of dependencies based on which ones are already loaded'''
    return [Present(dependency) if dependency in loaded else Missing(dependency) 
            for dependency in new]

def update_dependencies(loaded, new):
    '''For each new dependency, if new to the list, add it.'''
    for dependency in new:
        if Present(dependency) not in loaded or Missing(dependency) not in loaded:
            loaded.append(Missing(dependency))
    return loaded

def replace(l, old, new):
    '''Replaces one item in a list with another'''
    l[l.index(old)] = new


__all__ = [PluginControllerMixin, RootController, Controller,
           BadPathException, PathUnavailableException, update_wrapper, 
           pluggable, plugin]
