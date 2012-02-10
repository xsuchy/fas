-- Copyright © 2008  Red Hat, Inc.
-- Copyright © 2012  Xavier Lamien
--
-- This copyrighted material is made available to anyone wishing to use, modify,
-- copy, or redistribute it subject to the terms and conditions of the GNU
-- General Public License v.2.  This program is distributed in the hope that it
-- will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
-- implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
-- See the GNU General Public License for more details.  You should have
-- received a copy of the GNU General Public License along with this program;
-- if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
-- Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
-- incorporated in the source code or documentation are not subject to the GNU
-- General Public License and may only be used or replicated with the express
-- permission of Red Hat, Inc.
--
-- Author(s): Toshio Kuratomi <tkuratom@redhat.com>
--            Ricky Zhou <ricky@fedoraproject.org>
--            Mike McGrath <mmcgrath@redhat.com>
--            Xavier Lamien <laxathom@lxtnow.net>
--

create database fas2 encoding = 'UTF8';
\c fas2

create procedural language plpythonu
  handler plpythonu_call_handler
  validator plpythonu_validator;

-- Prevent UID conflict from local account user addition on the system.
CREATE SEQUENCE person_seq;
SELECT setval('person_seq', 10000);

CREATE TABLE people (
    -- tg_user::user_id
    id INTEGER PRIMARY KEY NOT NULL DEFAULT nextval('person_seq'),
    -- tg_user::user_name
    username VARCHAR(32) UNIQUE NOT NULL,
    -- tg_user::display_name
    human_name TEXT NOT NULL,
    -- TODO: Switch to this?
    -- Also, app would be responsible for eliminating spaces and
    -- uppercasing
    -- gpg_fingerprint varchar(40),
    gpg_keyid VARCHAR(64),
    ssh_key TEXT,
    -- tg_user::password
    password VARCHAR(127) NOT NULL,
    old_password VARCHAR(127),
    passwordtoken text null,
    password_changed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    email TEXT not null unique,
    emailtoken TEXT,
    unverified_email TEXT,
    comments TEXT,
    postal_address TEXT,
    country_code char(2),
    telephone TEXT,
    facsimile TEXT,
    affiliation TEXT,
    certificate_serial INTEGER DEFAULT 1,
    -- tg_user::created
    creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    --approval_status TEXT DEFAULT 'unapproved',
    internal_comments TEXT,
    ircnick TEXT,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'active',
    status_change TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    locale TEXT not null DEFAULT 'C',
    timezone TEXT null DEFAULT 'UTC',
    latitude numeric,
    longitude numeric,
    privacy BOOLEAN DEFAULT FALSE,
    alias_enabled BOOLEAN DEFAULT TRUE
    --check (gpg_keyid ~ '^[0-9A-F]{17}$')
);

create index people_status_idx on people(status);
cluster people_status_idx on people;

CREATE TABLE configs (
    id SERIAL PRIMARY KEY,
    person_id integer references people(id) not null,
    application TEXT not null,
    attribute TEXT not null,
    -- The value should be a simple value or a json string.
    -- Please create more config keys rather than abusing this with
    -- large datastructures.
    value TEXT
);

create index configs_person_id_idx on configs(person_id);
create index configs_application_idx on configs(application);
cluster configs_person_id_idx on configs;

CREATE TABLE groups (
    -- tg_group::group_id
    id INTEGER PRIMARY KEY NOT NULL DEFAULT nextval('person_seq'),
    -- tg_group::group_name
    name VARCHAR(32) UNIQUE NOT NULL,
    -- tg_group::display_name
    display_name TEXT,
    url TEXT,
    mailing_list TEXT,
    mailing_list_url TEXT,
    irc_channel TEXT,
    irc_network TEXT,
    owner_id INTEGER NOT NULL REFERENCES people(id),
    group_type VARCHAR(16),
    needs_sponsor BOOLEAN DEFAULT FALSE,
    user_can_remove BOOLEAN DEFAULT TRUE,
    invite_only BOOLEAN DEFAULT FALSE,
    prerequisite_id INTEGER REFERENCES groups(id),
    joinmsg TEXT NULL DEFAULT '',
    apply_rules TEXT,
    -- tg_group::created
    creation TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

create index groups_group_type_idx on groups(group_type);
cluster groups_group_type_idx on groups;

CREATE TABLE person_roles (
    person_id INTEGER NOT NULL REFERENCES people(id),
    group_id INTEGER NOT NULL REFERENCES groups(id),
    --  role_type is something like "user", "administrator", etc.
    --  role_status tells us whether this has been approved or not
    role_type text NOT NULL,
    role_status text DEFAULT 'unapproved',
    internal_comments text,
    sponsor_id INTEGER REFERENCES people(id),
    creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approval TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    primary key (person_id, group_id)
);

create index person_roles_person_id_idx on person_roles(person_id);
create index person_roles_group_id_idx on person_roles(group_id);
-- We could cluster on either person or group.  The choice of group is because
-- groups are larger and therefore will take more memory if guessed wrong.
-- Open to reevaluation.
cluster person_roles_group_id_idx on person_roles;

-- View for mod_auth_pgsql
create view user_group as select username, name as groupname from people as p, groups as g, person_roles as r where r.person_id=p.id and r.group_id=g.id and r.role_status='approved'; 

-- Log changes to the account system
create table log (
    id serial primary key,
    author_id INTEGER references people(id) not null,
    changetime TIMESTAMP WITH TIME ZONE default NOW(),
    description TEXT
);

create index log_changetime_idx on log(changetime);
cluster log_changetime_idx on log;

--
-- This table allows certain services to be restricted by hostname/ip/person.
--
-- Any time a request for a restricted action is requested, the FAS server
-- consults this table to see if the user@(hostname/ip) is allowed to access
-- the resource.  If approved is true, the request is granted.  If false or
-- null, the request is denied.
--
-- New records are created when a request is first made by a specific
-- username@(hostname/id)
--
create table requests (
    id serial primary key,
    person_id INTEGER not null references people(id),
    hostname TEXT not null,
    ip TEXT not null,
    action TEXT not null default 'trust_all',
    last_request TIMESTAMP WITH TIME ZONE default now() not null,
    approved boolean,
    unique (person_id, hostname, ip, action)
);

create index requests_last_request_idx on requests(last_request);
create index hostname_idx on requests(hostname);
create index ip_idx on requests(ip);
create index person_id_idx on requests(person_id);
cluster requests_last_request_idx on requests;

--
-- turbogears session tables
--
create table visit (
    visit_key CHAR(40) primary key,
    created TIMESTAMP WITH TIME ZONE not null default now(),
    expiry TIMESTAMP WITH TIME ZONE
);

create index visit_expiry_idx on visit(expiry);
cluster visit_expiry_idx on visit;

create table visit_identity (
    visit_key CHAR(40) primary key references visit(visit_key),
    user_id INTEGER references people(id),
    -- True if the user was authenticated using SSL
    ssl boolean
);

create table session (
  id varchar(40) primary key,
  data text,
  expiration_time timestamp
);

-- action r == remove
-- action a == add
CREATE TABLE bugzilla_queue (
    email text not null,
    group_id INTEGER references groups(id) not null,
    person_id INTEGER references people(id) not null,
    action CHAR(1) not null,
    primary key (email, group_id),
    check (action ~ '[ar]')
);

-- For Fas to connect to the database with user/role : fedora
GRANT ALL ON TABLE people, groups, person_roles, bugzilla_queue, configs, configs_id_seq, person_seq, visit, visit_identity, log, log_id_seq, session TO GROUP fedora;
