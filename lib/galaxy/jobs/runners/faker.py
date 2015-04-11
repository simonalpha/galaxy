"""
Job runner plugin for faking the execution of jobs.
"""
import logging
import threading

from Queue import Queue

from galaxy import model
from galaxy.jobs.runners import BaseJobRunner
from galaxy.jobs.runners import STOP_SIGNAL

log = logging.getLogger( __name__ )

__all__ = [ 'FakeJobRunner' ]

class FakeJobRunner( BaseJobRunner ):
    """
    Job runner that's a slacker, just pretending to do work.
    Currently just uses threads and sleeps.
    """
    runner_name = "FakeRunner"

    def __init__( self, app, nworkers ):
        super( FakeJobRunner, self ).__init__( app, nworkers )
        self._init_worker_threads()

    def _init_worker_threads(self):
        self.work_queue = Queue()
        self.work_threads = []
        self.thread_events = {}
        log.debug('Starting %s %s workers' % (self.nworkers, self.runner_name))
        for i in range(self.nworkers):
            thread_name = "work_thread-%d" % i
            thread_event = threading.Event()
            self.thread_events[thread_name] = thread_event
            worker = threading.Thread( name=thread_name, target=self.run_next )
            worker.setDaemon( True )
            worker.start()
            self.work_threads.append( worker )

    def queue_job( self, job_wrapper ):
        # basic sanity checks, using overriden method
        if not self.prepare_job( job_wrapper ):
            return

        event = self.thread_events[threading.current_thread().name]

        job = job_wrapper.get_job()
        base_job = job.caching_details.base_job

        log.debug( '(%s) executing on %s' % ( job.id, self.runner_name ) )

        job_wrapper.set_job_destination(job_wrapper.job_destination, threading.current_thread().name )
        job_wrapper.change_state( model.Job.states.RUNNING )

        event.wait( job.caching_details.duration )

        while base_job.state == model.Job.states.RUNNING:
            event.wait(10)
            self.sa_session.refresh(base_job)

        # check not deleted
        if event.is_set():
            self._delete_cached_job( job_wrapper )
            return

        # check for failure in base job
        if base_job.state != model.Job.states.OK:
            log.debug( "(%s) cached job on %s failed: base job (%s) wasn't OK"
                        % ( job.id, self.runner_name, base_job.id ) )
            job_wrapper.fail( base_job.info, stdout=base_job.stdout,
                    stderr=base_job.stderr, exit_code=base_job.exit_code )
            return

        log.debug( '(%s) execution on %s finished' % ( job.id, self.runner_name ) )

        # Finish the job!
        self._finish_cached_job(job_wrapper)

    def prepare_job(self, job_wrapper, include_metadata=False, include_work_dir_outputs=True):
        """
        Replaces BaseJobRunner prepare_job method; only performs checks
        and doesn't call job_wrapper prepare, as it is unneeded if we
        are only pretending to do work.
        """
        job_id = job_wrapper.get_id_tag()
        job_state = job_wrapper.get_state()

        # Make sure the job hasn't been deleted
        if job_state == model.Job.states.DELETED:
            log.debug( "(%s) Job deleted by user before it entered the %s queue"  % ( job_id, self.runner_name ) )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return False
        elif job_state != model.Job.states.QUEUED:
            log.info( "(%d) Job is in state %s, skipping execution"  % ( job_id, job_state ) )
            # cleanup may not be safe in all states
            return False

        # Prepare the job
        job_wrapper.is_ready = True
        return True

    def stop_job(self, job):
        """
        Cuts short the waiting.
        Signals via threading.Event object for the running thread.
        """
        event = self.thread_events[job.get_job_runner_external_id()]
        event.set()

    def recover( self, job, job_wrapper ):
        # TODO: investigate restarting timer, as we have update times
        job_wrapper.change_state( model.Job.states.OK )

    def _finish_cached_job(self, job_wrapper):
        # not the most ideal, but reduces having to alter existing code as much
        # (JobWrapper in this case).
        job = job_wrapper.get_job()
        self.sa_session.refresh(job)
        base_job = job.caching_details.base_job
        if job.state == model.Job.states.RUNNING:
            job_wrapper.change_state( model.Job.states.OK )
        else:
            job_wrapper.change_state( base_job.state )
            log.exception("(%s) Job marked as %s, assuming something is wrong"
                                    % (job.id, job.state))

    def _delete_cached_job( self, job_wrapper ):
        job_wrapper.fail( "Job was deleted" )
        log.warning( "Cached job %d was deleted/interrupted" % job_wrapper.job_id )
