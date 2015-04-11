-- HStore must be enabled in Postgres for this database, this must be done by
-- a superuser, by running:
--    CREATE EXTENSION IF NOT EXISTS hstore;

CREATE TABLE cached_job (
    id serial PRIMARY KEY,
    create_time timestamp without time zone,
    update_time timestamp without time zone,
    job_id int REFERENCES job(id) NOT NULL,
    tool_id varchar(255) NOT NULL,
    tool_version text,
    inputs hstore,
    outputs hstore,
    parameters hstore,
    duration int,
    deleted boolean
);

-- Add indices for efficient searching: B-trees for simple cols,
-- for hstore values, use gist (gin also possible).
CREATE INDEX cached_job_tool_id ON cached_job (tool_id);
CREATE INDEX cached_job_tool_version ON cached_job (tool_version);
CREATE INDEX cached_job_deleted ON cached_job(deleted);
CREATE INDEX cached_job_inputs ON cached_job USING gist(inputs);
CREATE INDEX cached_job_parameters ON cached_job USING gist(parameters);

-- Add a column to job table to track the relevant cached_job entry, if cached.
ALTER TABLE job ADD COLUMN cached_id int REFERENCES cached_job(id);
