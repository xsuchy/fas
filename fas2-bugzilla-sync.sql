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
--

-- action r == remove
-- action a == add
-- CREATE TABLE bugzilla_queue (
--     email text not null,
--     group_id INTEGER references groups(id) not null,
--     person_id INTEGER references people(id) not null,
--     action CHAR(1) not null,
--     primary key (email, group_id),
--     check (action ~ '[ar]')
-- );
-- GRANT ALL ON TABLE bugzilla_queue TO fedora; -- using default pgsql fas's user

--
-- When the fedorabugs role is updated for a person, add them to bugzilla queue.
--
create or replace function bugzilla_sync() returns trigger as $bz_sync$
    # Decide which row we are operating on and the action to take
    if TD['event'] == 'DELETE':
        # 'r' for removing an entry from bugzilla
        newaction = 'r'
        row = TD['old']
    else:
        # insert or update
        row = TD['new']
        if row['role_status'] == 'approved':
            # approved so add an entry to bugzilla
            newaction = 'a'
        else:
            # no longer approved so remove the entry from bugzilla
            newaction = 'r'

    # Get the group id for fedorabugs
    result = plpy.execute("select id from groups where name = 'fedorabugs'", 1)
    if not result:
        # Danger Will Robinson!  A basic FAS group does not exist!
        plpy.error('Basic FAS group fedorabugs does not exist')
    # If this is not a fedorabugs role, no change needed
    if row['group_id'] != result[0]['id']:
        return None

    # Retrieve the bugzilla email address
    ### FIXME: Once we implement it, we will want to add a check for an email
    # address in configs::application='bugzilla',person_id=person_id,
    # attribute='login'
    plan = plpy.prepare("select email from people where id = $1", ('int4',))
    result = plpy.execute(plan, (row['person_id'],))
    if not result:
        # No email address so nothing can be done
        return None
    email = result[0]['email']

    # If there is already a row in bugzilla_queue update, otherwise insert
    plan = plpy.prepare("select email from bugzilla_queue where email = $1",
            ('text',))
    result = plpy.execute(plan, (email,), 1)
    if result:
        plan = plpy.prepare("update bugzilla_queue set action = $1"
                " where email = $2", ('char', 'text'))
        plpy.execute(plan, (newaction, email))
    else:
        plan = plpy.prepare("insert into bugzilla_queue (email, group_id"
            ", person_id, action) values ($1, $2, $3, $4)",
                ('text', 'int4', 'int4', 'char'))
        plpy.execute(plan, (email, row['group_id'], row['person_id'], newaction))
    return None
$bz_sync$ language plpythonu;

create trigger role_bugzilla_sync before update or insert or delete
  on person_roles
  for each row execute procedure bugzilla_sync();

--
-- When an email address changes, check whether it needs to be changed in
-- bugzilla as well.
--
create or replace function bugzilla_sync_email() returns trigger AS $bz_sync_e$
    if TD['old']['email'] == TD['new']['email']:
        # We only care if the email has been changed
        return None;

    # Get the group id for fedorabugs
    result = plpy.execute("select id from groups where name = 'fedorabugs'", 1)
    if not result:
        # Danger Will Robinson!  A basic FAS group does not exist!
        plpy.error('Basic FAS group fedorabugs does not exist')
    fedorabugsId = result[0]['id']

    plan = plpy.prepare("select person_id from person_roles where"
        " role_status = 'approved' and group_id = $1 "
        " and person_id = $2", ('int4', 'int4'))
    result = plpy.execute(plan, (fedorabugsId, TD['old']['id']), 1)
    if not result:
        # We only care if Person belongs to fedorabugs
        return None;

    # Remove the old Email and add the new one
    changes = []
    changes.append((TD['old']['email'], fedorabugsId, TD['old']['id'], 'r'))
    changes.append((TD['new']['email'], fedorabugsId, TD['new']['id'], 'a'))

    for change in changes:
        # Check if we already have a pending change
        plan = plpy.prepare("select b.email from bugzilla_queue as b where"
            " b.email = $1", ('text',))
        result = plpy.execute(plan, (change[0],), 1)
        if result:
            # Yes, update that change
            plan = plpy.prepare("update bugzilla_queue set email = $1,"
                " group_id = $2, person_id = $3, action = $4 where "
                " email = $1", ('text', 'int4', 'int4', 'char'))
            plpy.execute(plan, change)
        else:
            # No, add a new change
            plan = plpy.prepare("insert into bugzilla_queue"
                " (email, group_id, person_id, action)"
                " values ($1, $2, $3, $4)", ('text', 'int4', 'int4', 'char'))
            plpy.execute(plan, change)

    return None
$bz_sync_e$ language plpythonu;

create trigger email_bugzilla_sync before update on people
  for each row execute procedure bugzilla_sync_email();
