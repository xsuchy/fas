# -*- coding: utf-8 -*-
import turbogears
from turbogears import controllers, expose, paginate, identity, redirect, widgets, validate, validators, error_handler
from turbogears.database import metadata, mapper, get_engine, session

#from sqlalchemy import Table, Column, Integer, String, MetaData, Boolean, create_engine, DateTime, func, ForeignKey
#from sqlalchemy.exc import IntegrityError
#from sqlalchemy.orm import relationship

import cherrypy

from datetime import datetime
import GeoIP
from genshi.template.plugin import TextTemplateEnginePlugin

import re

import fas.sidebar as sidebar
import logging
import fas.plugin as plugin

from fas.model import People, PeopleTable, PersonRolesTable, Groups, GroupsTable, Configs
from fas.model import Log

from fas.auth import *
from fas.util import send_mail
from fas.user import KnownUser
from fas.util import available_languages
import fas

from bunch import Bunch


# Initialize system group
admin_group = config.get('admingroup', 'accounts')
system_group = config.get('systemgroup', 'fas-system')
thirdparty_group = config.get('thirdpartygroup', 'thirdparty')

from clamodel import Cladb, ClaForm, ClaLink

def get_configs(configs_list):
    configs = {}
    for config in configs_list:
        configs[config.attribute] = config.value
    if 'enabled' not in configs:
        configs['enabled'] = '0'
    if 'pass' not in configs:
        configs['pass'] = 'Not Defined'
    return configs

class claPlugin(controllers.Controller):
    capabilities = ['cla_plugin']
    # Group name for people having signed the FPCA
    CLAGROUPNAME = config.get('cla_standard_group')
    # Meta group for everyone who has satisfied the requirements of the FPCA
    # (By signing or having a corporate signatue or, etc)
    CLAMETAGROUPNAME = config.get('cla_done_group')

    # Values legal in phone numbers
    PHONEDIGITS = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '+',
            '-', ')' ,'(', ' ')

    def __init__(self):
        '''Create CLA Controller.'''
        self.path = ''
        # Add default entry into cla
        #try:
        #    session.add( Cladb(name='fpca', comment='Fedora Contributors License Agreement'))
        #    session.flush()
        #except IndexError:
        #    pass

    def cla_dependent(self, cla, group):
        '''
        Check whether a group has the cla in its prerequires.

         Arguments
        :cla: Cla Object
        :group: Groups Object

        :returns: True if the group requires the cla_group_name otherwise
        '''
        if ClaLink.by_groupId(group.id):
            return True
        else:
            return False

    def json_request(self):
        ''' Helps define if json is being used for this request

        :returns: 1 or 0 depending on if request is json or not
        '''

        return 'tg_format' in cherrypy.request.params and \
                cherrypy.request.params['tg_format'] == 'json'

    @identity.require(turbogears.identity.not_anonymous())
    @validate(validators= {'username': KnownUser })
    @expose(template="fpca/index.html", allow_json=True)
    def index(self, username=None):
        ''' View CLA list '''

        show = {}
        show['show_postal_address'] = config.get('show_postal_address')

        if not username:
            username = identity.current.user_name
        person = People.by_username(username)
        if identity.current.user_name == username:
            personal = True
        else:
            personal = False
        admin = is_admin(identity.current)
        (cla, undeprecated_cla) = undeprecated_cla_done(person)

        #cla_data = Cladb.all()
        cla_data = {}
        cla_data['form'] = []
        for cla in Cladb.all():
            #__desc = session.query(Cladb.description).filter_by(name=cla).all()[0]
            #__signed = session.query(ClaForm.signed).filter_by(cla_id=Cladb.id).all()
            #cla_data['form'].append(Bunch(name=str(cla[0]), desc=str(__desc[0]), signed=__signed))
            #session.rollback()
            claform = ClaForm()
            __signed = claform.is_signed(cla.id, person.id)
            #__signed = True
            cla_data['form'].append(Bunch(id=cla.id, name=cla.name, desc=cla.description, signed=__signed))

        person_data = person.filter_private()
        person_data['approved_memberships'] = list(person.approved_memberships)
        person_data['unapproved_memberships'] = list(person.unapproved_memberships)
        person_data['roles'] = person.roles
        clla = 'tttest'

        roles = person.roles
        roles.json_props = {
                'PersonRole': ('group',),
                'Groups': ('unapproved_roles',),
                }
        if session.is_active:
            session.rollback()
        return dict(person=person_data, cla=clla, undeprecated=undeprecated_cla, cla_data=cla_data, personal=personal, admin=admin, show=show)

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fpca/cla_form.html")
    def form(self, cla_data):
        '''Display the CLAs (and accept/do not accept buttons)'''
        show = {}
        show['show_postal_address'] = config.get('show_postal_address')

        username = turbogears.identity.current.user_name
        person = People.by_username(username)
        try:
            code_len = len(person.country_code)
        except TypeError:
            code_len = 0
        if show['show_postal_address']:
            contactInfo = person.telephone or person.postal_address
            if person.country_code == 'O1' and not person.telephone:
                turbogears.flash(_('A telephone number is required to ' + \
                    'complete the FPCA.  Please fill out below.'))
            elif not person.country_code or not person.human_name \
                or not contactInfo:
                turbogears.flash(_('A valid country and telephone number ' + \
                    'or postal address is required to complete the FPCA.  ' + \
                    'Please fill them out below.'))
        else:
            if not person.telephone or code_len != 2 or \
                person.country_code == '  ':
                turbogears.flash(_('A valid country and telephone number are' +
                        ' required to complete the FPCA.  Please fill them ' +
                        'out below.'))
        (cla, undeprecated_cla) = undeprecated_cla_done(person)
        person = person.filter_private()
        return dict(cla=undeprecated_cla, cla_data=eval(cla_data), person=person, date=datetime.utcnow().ctime(),
                    show=show) 

    @expose(template="error.html")
    def error(self, tg_errors=None):
        '''Show a friendly error message'''
        if not tg_errors:
            turbogears.redirect('/')
        return dict(tg_errors=tg_errors)


    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fpca/edit.html")
    def edit(self, targetname=None):
        username = turbogears.identity.current.user_name
        person = People.by_username(username)
        target = People.by_username(targetname)
        if not cla_done(target):
            turbogears.flash(_('You must sign the CLA to have access to this service.'))
            turbogears.redirect('/user/view/%s' % target.username)
            return dict()
        admin = is_admin(person)
        configs = get_configs(Configs.query.filter_by(person_id=target.id, application='fpca').all())
        return dict(admin=admin, person=person, configs=configs,target=target)

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fpca/index.html")
    def sign(self, cla, human_name, telephone, country_code, postal_address=None,
        confirm=False, agree=False):
        '''Sign CLA form'''

        cla = eval(cla)
        claform = ClaForm()
        # TO DO: Pull show_postal_address in at the class level
        # as it's used in three methods now
        show = {}
        show['show_postal_address'] = config.get('show_postal_address')

        session.rollback()
        username = turbogears.identity.current.user_name
        person = People.by_username(username)
        if claform.is_signed(cla.id, person.id):
            turbogears.flash(_('You have already completed the FPCA.'))
            turbogears.redirect('/cla/')
            return dict()
        if not agree:
            turbogears.flash(_("You have not completed the FPCA."))
            turbogears.redirect('/cla/form/%s' % cla)
        if not confirm:
            turbogears.flash(_(
                'You must confirm that your personal information is accurate.'
            ))
            turbogears.redirect('/cla/form/%s' % cla)

        # Compare old information to new to see if any changes have been made
        if human_name and person.human_name != human_name:
            person.human_name = human_name
        if telephone and person.telephone != telephone:
            person.telephone = telephone
        if postal_address and person.postal_address != postal_address:
            person.postal_address = postal_address
        if country_code and person.country_code != country_code:
            person.country_code = country_code
        # Save it to the database
        try:
            session.flush()
        except Exception:
            turbogears.flash(_("Your updated information could not be saved."))
            turbogears.redirect('/cla/')
            return dict()

        # Heuristics to detect bad data
        if show['show_postal_address']:
            contactInfo = person.telephone or person.postal_address
            if person.country_code == 'O1':
                if not person.human_name or not person.telephone:
                    # Message implemented on index
                    turbogears.redirect('/cla/')
            else:
                if not person.country_code or not person.human_name \
                    or not contactInfo:
                    # Message implemented on index
                    turbogears.redirect('/cla/')
        else:
            if not person.telephone or \
                not person.human_name or \
                not person.country_code:
                turbogears.flash(_('To complete the %s, we must have your ' + \
                    'name telephone number, and country.  Please ensure they ' + \
                    'have been filled out.') % cla.name.upper())
                turbogears.redirect('/cla/')

        blacklist = config.get('country_blacklist', [])
        country_codes = [c for c in GeoIP.country_codes if c not in blacklist]

        if person.country_code not in country_codes:
            turbogears.flash(_('To complete the FPCA, a valid country code' + \
            'must be specified.  Please select one now.'))
            turbogears.redirect('/cla/')
        if [True for char in person.telephone if char not in self.PHONEDIGITS]:
            turbogears.flash(_('Telephone numbers can only consist of ' + \
                'numbers, "-", "+", "(", ")", or " ".  Please reenter using' +\
                'only those characters.'))
            turbogears.redirect('/cla/')

        #group = Groups.by_name(self.CLAGROUPNAME)
        try:
            # Everything is correct, apply license.
            claform = ClaForm()
            claform.add(cla.id, person.id, signed=True)
            #person.apply(group, person) # Apply for the new group
            session.flush()
        except fas.ApplyError:
            pass
        except Exception:
            turbogears.flash(_("Your license Agreement could not be signed."))
            turbogears.redirect('/cla/')
            return dict()

        #try:
        #    # Everything is correct.
        #    person.sponsor(group, person) # Sponsor!
        #    session.flush()
        #except fas.SponsorError:
        #    turbogears.flash(_("You are already a part of the '%s' group.") %
        #                        group.name)
        #    turbogears.redirect('/cla/')
        #except:
        #    turbogears.flash(_("You could not be added to the '%s' group.") %
        #                        group.name)
        #    turbogears.redirect('/cla/')

        date_time = datetime.utcnow()
        Log(author_id = person.id, description = 'Completed FPCA',
            changetime = date_time)
        cla_subject = \
            'Fedora ICLA completed for %(human_name)s (%(username)s)' % \
            {'username': person.username, 'human_name': person.human_name}
        cla_text = '''
Fedora user %(username)s has completed an ICLA (below).
Username: %(username)s
Email: %(email)s
Date: %(date)s

If you need to revoke it, please visit this link:
    https://admin.fedoraproject.org/accounts/cla/reject/%(cla_name)s/%(username)s

=== FPCA ===

''' % {'username': person.username,
'email': person.email,
'cla_name': cla.name,
'date': date_time.ctime(),}
        # Sigh..  if only there were a nicer way.
        plugin = TextTemplateEnginePlugin()
        cla_text += plugin.transform(dict(person=person),
                    'fas.templates.plugins.fpca.fpca').render(method='text',
                    encoding=None)

        send_mail(config.get('legal_cla_email'), cla_subject, cla_text)

        turbogears.flash(_("You have successfully completed the %s. You are now eligible to any applicable group.") % cla.name.upper())
        turbogears.redirect('/user/view/%s' % person.username)
        return dict()

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="fpca/index.html")
    def revoke(self, cla_id):
        '''
        Revoke CLA from user.

        This method will remove a user from signed Cla's form list.
        It is used when a person want to revoked its signed cla's form.
        '''
        #TODO: Send an email notification?
        username = turbogears.identity.current.user_name
        person = People.by_username(username)
        cla_form = ClaForm()

        try:
            cla_form.remove(cla_id, person.id)
            session.flush()
        except StatementError(e, s, p):
            print 'Error on SQL: %s' % e

        turbogears.redirect('/cla/')
        return dict()
         
    @identity.require(turbogears.identity.not_anonymous())
    @expose(template="user/view.html", allow_json=True)
    def reject(self, cla_name, person_name):
        '''Reject a user's FPCA.

        This method will remove a user from the FPCA group and any other groups
        that they are in that require the FPCA.  It is used when a person has
        to fulfill some more legal requirements before having a valid FPCA.

        Arguments
        :person_name: Name of the person to reject.
        '''
        show = {}
        show['show_postal_address'] = config.get('show_postal_address')
        exc = None
        user = People.by_username(turbogears.identity.current.user_name)
        if not is_admin(user):
            # Only admins can use this
            turbogears.flash(_('You are not allowed to reject FPCAs.'))
            exc = 'NotAuthorized'
        else:
            # Unapprove the cla and all dependent groups
            person = People.by_username(person_name)
            for role in person.roles:
                #TODO: update this statement to claform.group_dependent(role.group) like
                if self._cla_dependent(role.group):
                    role.role_status = 'unapproved'
            try:
                session.flush()
            except DBAPIError, error:
                turbogears.flash(_('Error removing cla and dependent groups' \
                        ' for %(person)s\n Error was: %(error)s') %
                        {'person': person_name, 'error': str(error)})
                exc = 'DBAPIError'

        if not exc:
            # Send a message that the ICLA has been revoked
            date_time = datetime.utcnow()
            Log(author_id=user.id, description='Revoked %s FPCA' %
                person.username, changetime=date_time)
            revoke_subject = 'Fedora ICLA Revoked'
            revoke_text = '''
Hello %(human_name)s,

We're sorry to bother you but we had to reject your FPCA for now because
information you provided has been deemed incorrect.  The most common cause
of this is people abbreviating their name like "B L Couper" instead of
providing their actual full name "Bill Lay Couper".  Other causes of this
include are using a country, or phone number that isn't accurate [1]_.
If you could edit your account [2]_ to fix any of these problems and resubmit
the FPCA we would appreciate it.

.. [1]: Why does it matter that we have your real name and phone
        number?   It's because the FPCA is a legal document and should we ever
        need to contact you about one of your contributions (as an example,
        because someone contacts *us* claiming that it was really they who
        own the copyright to the contribution) we might need to contact you
        for more information about what's going on.

.. [2]: Edit your account by logging in at this URL:
        https://admin.fedoraproject.org/accounts/user/edit/%(username)s

If you have questions about what specifically might be the problem with your
account, please contact us at accounts@fedoraproject.org.

Thanks!
    ''' % {'username': person.username, 'human_name': person.human_name}

            send_mail(person.email, revoke_subject, revoke_text)

            # Yay, sweet success!
            turbogears.flash(_('FPCA Successfully Removed.'))
        # and now we're done
        if request_format() == 'json':
            return_val = {}
            if exc:
                return_val['exc'] = exc
            return return_val
        else:
            turbogears.redirect('/user/view/%s' % person_name)

    @identity.require(turbogears.identity.not_anonymous())
    @expose(format="json", allow_json=True)
    def dump(self):
        person = People.by_username(identity.current.user_name)
        if identity.in_group(admin_group) or \
            identity.in_group(system_group):
            fpca_attrs = {}
            for attr in Configs.query.filter_by(application='fpca').all():
                if attr.person_id not in fpca_attrs:
                    fpca_attrs[attr.person_id] = {}
                fpca_attrs[attr.person_id][attr.attribute] = attr.value
            return dict(fpca_attrs=fpca_attrs)
        return dict()
    
    @expose(template="help.html")
    def help(self, id='none'):
        help = { 'none' :               [_('Error'), _('<p>We could not find that help item</p>')],
            'fpca_pass':        [_('Asterisk Password'), _('<p>Your Asterisk password needs to be numeric only and should not match your Fedora Password.  <b> You will use this password to log in to fpca <u>not</u> your normal user account password.</b></p>')],
            'fpca_enabled':     [_('Asterisk Active?'), _('<p>If set to false, your fpca extension will not exist and you will not get calls nor be able to log in.  If set to enabled you will be able to receive calls and log in</p>')],
            'fpca_voicemail':   [_('Asterisk Voicemail'), _('<p>Would you like to receive voice mail when people call and you are not around?  It will come to you via email and an attachment</p>')],
            'fpca_sms':         [_('Asterisk SMS Notification'), _('<p>When someone leaves you an email, a notification will get sent to this address.  It will not contain the actual message, just a notification that a message is waiting.</p>')],
            'fpca_extension':   [_('Asterisk Extension'), _('<p>This is your extension number.  Others can reach you via this number or via your sip address.</p>')],
            'fpca_sip_address': [_('Asterisk SIP Address'), _('<p>This is your SIP address.  When using phones that support it (or Ekiga or Twinkle for example) people can contact you by typing this address.</p>')],
            }

        try:
            helpItem = help[id]
        except KeyError:
            return dict(title=_('Error'), helpItem=[_('Error'), _('<p>We could not find that help item</p>')])
        return dict(help=helpItem)

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template = "genshi-text:fpca/fpca.txt", format = "text",
            content_type = 'text/plain; charset=utf-8')
    def text(self):
        '''View FPCA as text'''
        username = turbogears.identity.current.user_name
        person = People.by_username(username)
        person = person.filter_private()
        return dict(person=person, date=datetime.utcnow().ctime())

    @identity.require(turbogears.identity.not_anonymous())
    @expose(template = "genshi-text:fpca/fpca.txt", format = "text",
            content_type = 'text/plain; charset=utf-8')
    def download(self):
        '''Download FPCA'''
        username = turbogears.identity.current.user_name
        person = People.by_username(username)
        person = person.filter_private()
        return dict(person=person, date=datetime.utcnow().ctime())
    
    @classmethod
    def initPlugin(cls, controller):
        cls.log = logging.getLogger('plugin.cla')
        cls.log.info('CLA plugin initializing')
        try:
            path, self = controller.requestpath(cls, '/cla')
            cls.log.info('CLA plugin hooked')
            self.path = path
            if self.sidebarentries not in sidebar.entryfuncs:
                sidebar.entryfuncs.append(self.sidebarentries)
        except (plugin.BadPathException,
            plugin.PathUnavailableException), e:
            cls.log.info('CLA plugin hook failure: %s' % e)

    def delPlugin(self, controller):
        ''' Remove plugin from core application

        :arg controller: TG controller object
        :returns: 
        '''
        self.log.info('CLA plugin shutting down')
        if self.sidebarentries in sidebar.entryfuncs:
            sidebar.entryfuncs.remove(self.sidebarentries)

    def sidebarentries(self):
        ''' Add CLA plugin to Sidebare actions

        :returns: Data list of CLa's name and tg.url
        '''
        return [('CLA', self.path)]

    def isSigned(self, cla, person, group):
        ''' Check if cla has been signed for related group

        :arg cla: CLA Object
        :arg person: People Object
        :arg group: Groups Object

        :returns: True if person has signed request CLA,
         otherwise, False.
        '''
        return

    def isRevoked(self, cla, person, **kw):
        ''' Check if CLA has been revoked for requested group

        :arg cla: CLA Object
        :arg person: People Object
        :arg group: Groups Object

        :returns: True if person's Cla has been revoked,
        otherwise, False
        '''
        return

    def signForm(self, cla_name, person, group):
        ''' Sign CLA form

        :arg claName:
        :arg person: People Object
        :arg group: Groups Object

        :returns: 
        '''
        
        ClaForm.apply(cla_name.id, person.id)

    @classmethod
    def setGroupViewField(self, group=None):
        '''
        A class method which add new fields to
        core application for Groups/view page

        Arguments
        :group: Groups Object

        :returns: A list of Dict() data
        '''

        if group:
            group_link = ClaLink.by_group(group.id)
        else:
            group_link = None

        field_data = {}
        field_data['name'] = _('CLA requirement')
        field_data['data'] = 'None'

        if group_link:
            for cla in Cladb.all():
                if group_link[0].cla_id == cla.id:
                    field_data['data'] = Bunch(name=cla.name, desc=cla.description)
                    break
        else:
            field_data['data'] = Bunch(name='None')
        

        return [field_data]

    @classmethod
    def setGroupEditField(self, group=None):
        ''' 
        A class method which add new fields
        to core application for Groups
        
        Arguments
        :group: Groups Object

        :returns: A list of hash and Dict() of Cla's data

        [{'field_name' :'', 'field_data' : [Bunch(name=''),]}]
        '''

        # Check if Cla has been applied to given group
        if group:
            cla_applied = ClaLink.by_group(group.id)
        else:
            cla_applied = None

        field_data = {}
        field_data['name'] = _('Select CLA')
        field_data['data'] = []

        group_linked = False
        for cla in Cladb.all():

            # Make sure we're dealing with right cla among groups
            if cla_applied:
                if cla_applied[0].cla_id == cla.id:
                    group_linked = True
                else:
                    group_linked = False

            field_data['data'].append(Bunch(name=cla.name, desc=cla.description, data_set=group_linked))
        session.flush()

        return [field_data]

    @classmethod
    def saveGroupFieldData(self, person, group, dataField):
        ''' Store data from Group's extras fields '''

        cla_link = ClaLink()
        #cla_form = ClaForm()

        if dataField > 0:
            for data in dataField:
                cla = Cladb.by_name(data['extras_list'])
                if ClaLink.exists(group.id):
                    session.rollback()
                    cla_link.remove(group.id)
                    #cls.execute(ClaLink.update().where(ClaLink.c.group_id==group.id).values(cla_id=cla_id))
                else:
                    cla_link.apply(cla.id, group.id)
                #cla_form.add(cla.id, person.id)
                session.flush()
                  #  except Exception:
                  #      #session.rollback()
                  #      pass
