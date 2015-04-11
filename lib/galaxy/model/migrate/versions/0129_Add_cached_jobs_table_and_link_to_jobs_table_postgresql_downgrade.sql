-- remove column linking to cached_job table from job.
ALTER TABLE job DROP COLUMN cached_id;

-- drop indices on cached_job.
DROP INDEX cached_job_tool_id;
DROP INDEX cached_job_tool_version;
DROP INDEX cached_job_inputs;
DROP INDEX cached_job_parameters;
DROP INDEX cached_job_deleted;

-- finally, drop the cached job table.
DROP TABLE cached_job;

-- after this point, the hstore extension can be disabled, but this requires
-- superuser privileges, so cannot be done automatically.
