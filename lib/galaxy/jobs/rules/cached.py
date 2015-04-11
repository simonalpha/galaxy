from galaxy.jobs import JobDestination

def cached_or_normal(job):
    if not job.is_cached():
        return JobDestination(id="local", runner="local")
    else:
        return JobDestination(id="sleeper", runner="sleeper")
