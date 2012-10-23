-- Copyright © 2012  Red Hat, Inc.
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
-- Author(s): Xavier Lamien
--

CREATE TABLE cla (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    type TEXT,
    active BOOLEAN DEFAULT false,
    created_at TIME WITH time zone DEFAULT NOW(),
    last_modified TIMESTAMP WITH time zone NULL );

CREATE TABLE cla_form (
    cla_id INTEGER REFERENCES cla(id) NOT NULL,
    person_id INTEGER REFERENCES people(id) NOT NULL,
   -- group_id INTEGER REFERENCES groups(id) NOT NULL,
    signed BOOLEAN DEFAULT False,
    revoked BOOLEAN DEFAULT False,
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT NOW() );

CREATE TABLE cla_link (
    cla_id INTEGER REFERENCES cla(id) NOT NULL,
    group_id INTEGER REFERENCES groups(id) UNIQUE NOT NULL,
    created_at TIME WITH TIME ZONE DEFAULT NOW() );

CREATE INDEX cla_form_person_id_idx ON cla_form(person_id);
-- CREATE INDEX cla_form_group_id_idx ON cla_form(group_id);
CREATE INDEX cla_form_cla_id_idx ON cla_form(cla_id);
CREATE INDEX cla_link_group_id_idx ON cla_link(group_id);

-- ALTER TABLE groups ADD COLUMN prerequicla_id INTEGER REFERENCES cla(id) NULL;

-- Default entry for Fedora Project
INSERT INTO cla (name, description, type, active) VALUES ('fpca', 'Fedora Contributor License Agreement', 'html', True);
