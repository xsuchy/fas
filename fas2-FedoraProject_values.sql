-- Copyright © 2008  Red Hat, Inc.
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

-- Create Fedora Project required groups
INSERT INTO groups (id, name, display_name, owner_id, group_type, user_can_remove) VALUES (100002, 'cla_done', 'CLA Done Group', (SELECT id from people where username='admin'), 'cla', false);
INSERT INTO groups (id, name, display_name, owner_id, group_type, user_can_remove) VALUES (101441, 'cla_fedora', 'Fedora CLA Group', (SELECT id from people where username='admin'), 'cla', false);
INSERT INTO groups (id, name, display_name, owner_id, group_type, user_can_remove) VALUES (155928, 'cla_fpca', 'Signers of the Fedora Project Contributor Agreement', (SELECT id from people where username='admin'), 'cla', false);
INSERT INTO groups (id, name, display_name, owner_id, group_type) VALUES (100148, 'fedorabugs', 'Fedora Bugs Group', (SELECT id from people where username='admin'), 'tracking');

--
-- Constraint based on Fedora Project purpose
--

-- Define specific account status
ALTER TABLE people ADD CONSTRAINT people_status_check CHECK (status in ('active', 'inactive', 'expired', 'admin_disabled'));

-- Define specific person_roles status & type
ALTER TABLE person_roles ADD CONSTRAINT person_roles_role_status CHECK (role_status in ('approved', 'unapproved'));
ALTER TABLE person_roles ADD CONSTRAINT person_roles_role_type CHECK (role_type in ('user', 'administrator', 'sponsor'));

-- Define specific groups type list
ALTER TABLE groups ADD CONSTRAINT groups_group_type_check CHECK (group_type in ('cla', 'system', 'bugzilla','cvs', 'bzr', 'git', 'hg', 'mtn', 'svn', 'shell', 'torrent', 'tracker', 'tracking', 'user'));

-- Specific application list (fas plugins)
ALTER TABLE configs ADD CONSTRAINT configs_application_check CHECK (application in ('asterisk', 'moin', 'myfedora' ,'openid', 'yubikey', 'bugzilla'), unique (person_id, application, attribute));
