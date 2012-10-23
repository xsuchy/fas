# -*- coding: utf-8 -*-
import turbogears
from turbogears import controllers, expose, paginate, identity, redirect, widgets, validate, validators, error_handler
from turbogears.database import metadata, mapper, get_engine, session

from sqlalchemy import Table, Column, Integer, String, MetaData, Boolean, create_engine, DateTime, func, ForeignKey
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import relationship

import cherrypy
from datetime import datetime
from genshi.template.plugin import TextTemplateEnginePlugin

from fas.model import People, PeopleTable, PersonRolesTable, Groups, GroupsTable, Configs


# Create mapping
cla_table = Table('cla', metadata,
	Column('id', Integer, primary_key=True),
	Column('name', String, nullable=False, unique=True),
	Column('description', String, nullable=True),
	# TODO: maybe add constraint here : CheckConstraint(name='cla_format', 'txt, html, etc')
	Column('type', String, default='html'),
	Column('active', Boolean, default=False),
	Column('created_at', DateTime, default=func.now()),
        Column('last_modified', DateTime, default=func.now(), onupdate=func.utc_timestamp())) 

cla_form_table = Table('cla_form', metadata,
	Column('person_id', Integer, ForeignKey(People.id)),
	Column('cla_id', Integer, ForeignKey('cla.id'), primary_key=True),
	Column('signed', Boolean, default=False),
	Column('revoked', Boolean, default=False),
	Column('last_modified', DateTime, default=func.now(), onupdate=func.utc_timestamp()))

cla_link_table = Table('cla_link', metadata,
        Column('group_id', Integer, ForeignKey(Groups.id)),
        Column('cla_id', Integer, ForeignKey('cla.id'), primary_key=True),
        Column('created_at', DateTime, default=func.now()))

class Cladb(object):

    @classmethod
    def all(cls):
        '''
        A class method that can be used to fetch
        all availabled cla.

        :returns: Cla Object
        '''
        return cls.query.all()

    @classmethod
    def by_id(cls, id):
        '''
        A class method that can be used to search
        Cla based on their ID

        Arguments
        :id: Integer
        
        Returns: Data Object
        '''
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, name):
        '''
        A class method that can be used to search
        Cla based on their name

        Arguments
        :name: String

        :returns: Data Object
        '''
        return cls.query.filter_by(name=name).one()

    @classmethod
    def by_active(cls, cla_status):
        '''
        A class method than can be used to search
        Cla based on their status

        Arguments
        :name: Cla name

        Returns: Cla Object
        '''
        return cls.query.filter_by(active=cla_status).one()

    def isActive(cls, cla_id):
        '''
        A method that check if requested Cla is
        active.

        Arguments
        :cla_id: Integer

        :returns: True if Cla is active otherwise, False
        '''
        return cls.query(self.active).filter_by(id=cla_id).one()

    def add(cls, cla_name, cla_desc, cla_type, active=False, cla_comment=None):
        '''
        A method to add new cla form

        Arguments
        :cla_name: String
        :cla_desc: String
        :cla_type: String
        :cla_active: Boolean, Default: False
        :cla_comment: String, Default: None

        :returns:
        '''
        cls.name = cla_name
        cls.description = cla_desc
        cls.type = type
        if cla_active:
            cls.active = cla_active
        if cla_comment:
            cls.comment = cla_comment
        session.flush()

    def delete(cls, cla_name):
        '''
        A method to remove Cla Form

        Arguments
        :cla_name: String

        :returns:
        '''
        cla = cls.by_name(cla_name)
        cla_form = ClaForm.by_id(cla.id)
        cla_link = ClaLink.by_id(cla.id)
        session.delete(cla)
        #session.delete(cla_form)
        #session.delete(cla_link)

class ClaForm(object):

    @classmethod
    def by_cla_id(cls, cla_id):
        '''
        A class method that can be used to search for
        assigned Cla's form based on their applied groups
        
        Arguments
        :id: Group ID

        :returns: Cla forms for requested group
        '''
        return cls.query.filter_by(cla_id=cla_id).all()

    def add(cls, cla_id, person_id, signed=False, revoked=False):
        '''
        A method that can be used to add people
        to Cla Form table

        Arguments
        :claId: Integer
        :personId: Integer

        :returns:
        '''
        cls.person_id = person_id
        cls.cla_id = cla_id
        cls.signed = signed
        cls.revoked = revoked
        #session.flush()

    def remove(cls, cla_id, person_id):
        '''
        A method that can be used to remove people
        from Cla Form table

        Arguments
        :Cla_id: Integer
        :person_id: Integer

        :returns:
        '''
        cla = cls.query.filter_by(person_id=person_id, cla_id=cla_id).one()
        session.delete(cla)

    def apply(cls, cla_id, person_id):
        '''
        A method to sign Cla Form

        Arguments
        :claId: Integer
        :personId: Integer

        :returns:
        '''
        #cls.person_id = person_id
        #cls.cla_id = cla_id
        #cls.signed = True
        #cls.revoked = False
        cls.add(cla_id, person_id, signed=True)

    def reject(cls, cla_id, person_id):
        '''
        A method to Reject Cla Form based on person,
        cla & group's ID
        
        Arguments
        :claId: Integer
        :personId: Integer

        :returns:
        '''
        #cls.person_id = person_id
        #cls.cla_id = cla_id
        #cls.revoked = True
        cls.add(cla_id, person_id, signed=False, revoked=True)

    def is_signed(cls, cla_id, person_id):
        '''
        A method to check if Cla form has been signed
        by given person data.

        Arguments
        :cla_id: Integer
        :person_id: Integer

        :returns: True if given Cla is signed otherwise, False
        '''
        form = cls.query.filter_by(cla_id=cla_id, person_id=person_id).all()
        if form:
            return form[0].signed
        else:
            return False

class ClaLink(object):

    @classmethod
    def by_cla(cls, cla_id):
        '''
        A class method that can be used to search Cla linked
        groups based on their attached Cla.

        Arguments
        :cla_id: cla ID

        :returns: Groups ID linked to request CLA
        '''
        return cls.query.filter_by(cla_id=cla_id).all()

    @classmethod
    def by_group(cls, group_id):
        '''
        A class method that can be used to search attached
        Cla's form based on requested group.

        Arguments
        :group_id: group ID

        :returns: attached Cla's ID
        '''
        return cls.query.filter_by(group_id=group_id).all()
         
    @classmethod
    def exists(cls, group_id):
        '''
        A class method that can be used to check attached
        Cla's form based on requested group.

        Arguments
        :group_id: group ID

        :returns: True if group id present 
        '''
        try:
            link = cls.query.filter_by(group_id=group_id).one()
            if link.group_id:
                return True
        except:
            pass

        return False

    def apply(cls, cla_id, group_id):
        '''
        A method that can be used to apply a Cla Form
        against a given group

        Arguments
        :claId: Integer
        :groupId: Integer

        :returns:
        '''
        #if cls.exists(group_id):
        #    cla = cls.by_cla(cla_id)
        #    session.delete(cla[0])
        #    ins = cls.insert()
        #    str(ins)

        #    cls.cla_id = cla_id
        #    cls.group_id = group_id
        #    #session.execute(cls.update().where(cla_link_table.c.group_id==group_id).values(cla_id=cla_id))
        #    #session.update(cls)
        #    #session.save_or_update(cls)
        #else:
        cls.cla_id = cla_id
        cls.group_id = group_id

    def remove(cls, group_id):
        '''
        A method that can be used to remove an
        attached Cla form to a requested group

        Arguments
        :group_id: Integer

        :returns:
        '''
        link = cls.query.filter_by(group_id=group_id).one()
        session.delete(link)

# Initialize mapping against CLA tables
mapper(Cladb, cla_table)
mapper(ClaForm, cla_form_table, properties={ 'cla' : relationship(Cladb, backref='cla', order_by=cla_table.c.id) })
mapper(ClaLink, cla_link_table)
