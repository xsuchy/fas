# -*- coding: utf-8 -*-
import turbogears
from turbogears import controllers, expose, paginate, identity, redirect, widgets, validate, validators, error_handler
from turbogears.database import session

import cherrypy

from genshi.template.plugin import TextTemplateEnginePlugin

import fas.sidebar as sidebar
import logging
import fas.plugin as plugin

import os
import re
import sys

import totpcgi
import totpcgi.backends

class GoogleAuthPlugin(controllers.Controller):
    capabilities = ['gauth_plugin']

    def __init__(self):
        '''Create a GoogleAuth Controller.'''
        self.path = ''

    @classmethod
    def initPlugin(cls, controller):
        cls.log = logging.getLogger('plugin.gauth')
        cls.log.info('GoogleAuth plugin initializing')
        try:
            path, self = controller.requestpath(cls, '/google-auth')
            cls.log.info('GoogleAuth plugin hooked')
            self.path = path
            if self.sidebarentries not in sidebar.entryfuncs:
                sidebar.entryfuncs.append(self.sidebarentries)
        except (plugin.BadPathException,
            plugin.PathUnavailableException), e:
            cls.log.info('GoogleAuth plugin hook failure: %s' % e)

    def delPlugin(self, controller):
        self.log.info('GoogleAuth plugin shutting down')
        if self.sidebarentries in sidebar.entryfuncs:
            sidebar.entryfuncs.remove(self.sidebarentries)

    def sidebarentries(self):
        return [('GoogleAuth plugin', self.path)]

    def bad_request(reply):
        output = 'ERR\n' + reply + '\n'
        cls.log.error('Status: 400 BAD REQUEST\n')
        cls.log.error('Content-type: text/plain\n')
        cls.log.error('Content-Length: %s\n' % len(output))
        cls.log.error('\n')

        cls.log.error(output)
        #TODO: Return or redirect to index or such.

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fas_gauth.templates.index")
    def index(self):
        return dict()

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fas_gauth.templates.verify")
    def verify(self, auth_data):

       # We don't really need this for fas but keep it around for now.
       # must_keys = ('user', 'token', 'mode')

       # for must_key in must_keys:
       #     if must_key not in auth_data:
       #         bad_request("Missing field: %s" % must_key)

        user  = auth_data['user']
        token = auth_data['token']
        mode  = auth_data['mode']

        #This is for pam_url
        remote_host = os.environ['REMOTE_ADDR']

        if mode != 'PAM_SM_AUTH':
            bad_request('We only support PAM_SM_AUTH')

        if parse_token(token):
            # This should come from yubikey plugin - stop embed stuff everywhere!
            ga = YubikeyAuthenticator(require_pincode)
        else:
            # totp/googleauth
            ga = totpcgi.GoogleAuthenticator(backends, require_pincode)

        try:
            status = ga.verify_user_token(user, token)
        except Exception, ex:
            cls.log.error(
                'Failure: user=%s, mode=%s, host=%s, message=%s' % (user, mode,
                    remote_host, str(ex)))
            bad_request(str(ex))

        cls.log.debug('Success: user=%s, mode=%s, host=%s, message=%s' %
                    (user, mode, remote_host, status))

        cls.log.info('Status: 200 OK\n')
        cls.log.info('Content-type: text/plain\n')
        #cls.log.info('Content-Length: %s\n' % len(success_string))
        #cls.log.info(success_string)

        return dict(value="Google Authenticator")

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fas_gauth.templates.provision")
    def provision(self, username):
        return dict(person=username)

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fas_gauth.templates.delete") 
    def delete(self, username):
        return dict(person=username)

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fas_gauth.templates.reset") 
    def reset(self, username):
        return dict(person=username)
