from galaxy.jobs import JobDestination
from galaxy.jobs.mapper import JobMappingException

def admin_only(app, user_email):
    if user_email and user_email in app.config.admin_users.split(','):
        return JobDestination(id="local", runner="local")
    else:
        raise JobMappingException("This tool is restricted to administrators.")
