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

-- This is default values used to get quick access to FAS
-- NOTE : If you intend to make some changes on the admin user and group name
-- do it into fas.cfg.sample before run this script.

\c fas2

-- Create default admin user & default Password : "admin"
INSERT INTO people (id, username, human_name, password, email) VALUES (100001, 'admin', 'Admin User', '$1$djFfnacd$b6NFqFlac743Lb4sKWXj4/', 'root@localhost');

-- Add default FAS admin group
-- FAS requires at least one admin group to grant privileges, see fas.cfg.sample
INSERT INTO groups (id, name, display_name, owner_id, group_type) VALUES (100006, 'fas-admin', 'Account System Admins', (SELECT id from people where username='admin'), 'tracking');

-- Add FAS System-User group, see fas.cfg.sample
INSERT INTO groups (name, display_name, owner_id, group_type) VALUES ('fas-system', 'System users allowed to get password and key information', (SELECT id from people where username='admin'), 'system');

-- Add default Admin account to group fas-admin
INSERT INTO person_roles (person_id, group_id, role_type, role_status, internal_comments, sponsor_id) VALUES ((SELECT id from people where username='admin'), (select id from groups where name='fas-admin'), 'administrator', 'approved', 'created at install time', (SELECT id from people where username='admin'));
