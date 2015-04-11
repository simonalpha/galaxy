from galaxy.exceptions import ObjectInvalid
from galaxy.model import LibraryDatasetDatasetAssociation
from galaxy import model
from galaxy.tools.parameters import DataToolParameter
from galaxy.tools.parameters import DataCollectionToolParameter
from galaxy.tools.parameters.wrapped import WrappedParameters
from galaxy.util.json import dumps
from galaxy.util.none_like import NoneDataset
from galaxy.util.odict import odict
from galaxy.util.template import fill_template
from galaxy.web import url_for

from sqlalchemy.orm import aliased
from galaxy.tools.actions import DefaultToolAction, ObjectStorePopulator, on_text_for_names, filter_output, determine_output_format
from galaxy.util.hstore import hstorify_dict

import logging
log = logging.getLogger( __name__ )


class CachedToolAction( DefaultToolAction ):
    """Default tool action is to run an external command"""

    def execute(self, tool, trans, incoming={}, return_job=False, set_output_hid=True, set_output_history=True, history=None, job_params=None, rerun_remap_job_id=None, mapping_over_collection=False):
        """
        Executes a tool, creating job and tool outputs, associating them, and
        submitting the job to the job queue. If history is not specified, use
        trans.history as destination for tool's output datasets.
        """
        assert tool.allow_user_access( trans.user ), "User (%s) is not allowed to access this tool." % ( trans.user )
        # Set history.
        if not history:
            history = tool.get_default_history_by_trans( trans, create=True )

        out_data = odict()
        out_collections = {}
        out_collection_instances = {}
        # Track input dataset collections - but replace with simply lists so collect
        # input datasets can process these normally.
        inp_dataset_collections = self.collect_input_dataset_collections( tool, incoming )
        # Collect any input datasets from the incoming parameters
        inp_data = self.collect_input_datasets( tool, incoming, trans )

        # Deal with input dataset names, 'dbkey' and types
        input_names = []
        input_ext = 'data'
        input_dbkey = incoming.get( "dbkey", "?" )
        for name, data in inp_data.items():
            if not data:
                data = NoneDataset( datatypes_registry=trans.app.datatypes_registry )
                continue

            # Convert LDDA to an HDA.
            if isinstance(data, LibraryDatasetDatasetAssociation):
                data = data.to_history_dataset_association( None )
                inp_data[name] = data

            else:  # HDA
                if data.hid:
                    input_names.append( 'data %s' % data.hid )
            input_ext = data.ext

            if data.dbkey not in [None, '?']:
                input_dbkey = data.dbkey

            identifier = getattr( data, "element_identifier", None )
            if identifier is not None:
                incoming[ "%s|__identifier__" % name ] = identifier

        # Collect chromInfo dataset and add as parameters to incoming
        ( chrom_info, db_dataset ) = trans.app.genome_builds.get_chrom_info( input_dbkey, trans=trans, custom_build_hack_get_len_from_fasta_conversion=tool.id != 'CONVERTER_fasta_to_len' )
        if db_dataset:
            inp_data.update( { "chromInfo": db_dataset } )
        incoming[ "chromInfo" ] = chrom_info

        # Determine output dataset permission/roles list
        existing_datasets = [ inp for inp in inp_data.values() if inp ]
        if existing_datasets:
            output_permissions = trans.app.security_agent.guess_derived_permissions_for_datasets( existing_datasets )
        else:
            # No valid inputs, we will use history defaults
            output_permissions = trans.app.security_agent.history_get_default_permissions( history )

        # Build name for output datasets based on tool name and input names
        on_text = on_text_for_names( input_names )

        # Add the dbkey to the incoming parameters
        incoming[ "dbkey" ] = input_dbkey

        CachedJob = trans.model.CachedJob
        base_job = aliased(trans.model.Job)
        inp_hs = hstorify_dict( self._collapse_inputs( tool, inp_data ) )
        inc_hs = hstorify_dict(dict((k, v) for k, v in incoming.iteritems() if k not in inp_data))

        cache_hits = (trans.sa_session.query(CachedJob).
                        filter_by(tool_id=tool.id, tool_version=tool.version).
                        filter(CachedJob.inputs.contains(inp_hs),
                               CachedJob.inputs.contained_by(inp_hs),
                               CachedJob.parameters.contains(inc_hs),
                               CachedJob.parameters.contained_by(inc_hs)).
                        join(base_job, CachedJob.base_job).
                        filter(base_job.state != base_job.states.DELETED).
                        filter(base_job.state != base_job.states.DELETED_NEW).
                        filter(base_job.state != base_job.states.ERROR))
        cache_hit = cache_hits.first()

        # wrapped params are used by change_format action and by output.label; only perform this wrapping once, as needed
        wrapped_params = WrappedParameters( trans, tool, incoming )
        if cache_hit:
            log.debug("Found previous job to copy (id: %i)" % cache_hit.base_job.id)
        else:
            def handle_output( name, output ):
                if output.parent:
                    parent_to_child_pairs.append( ( output.parent, name ) )
                    child_dataset_names.add( name )
                ## What is the following hack for? Need to document under what
                ## conditions can the following occur? (james@bx.psu.edu)
                # HACK: the output data has already been created
                #      this happens i.e. as a result of the async controller
                if name in incoming:
                    dataid = incoming[name]
                    data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataid )
                    assert data is not None
                    out_data[name] = data
                else:
                    ext = determine_output_format( output, wrapped_params.params, inp_data, input_ext )
                    data = trans.app.model.HistoryDatasetAssociation( extension=ext, create_dataset=True, sa_session=trans.sa_session )
                    if output.hidden:
                        data.visible = False
                    # Commit the dataset immediately so it gets database assigned unique id
                    trans.sa_session.add( data )
                    trans.sa_session.flush()
                    trans.app.security_agent.set_all_dataset_permissions( data.dataset, output_permissions )

                object_store_populator.set_object_store_id( data )

                # This may not be neccesary with the new parent/child associations
                data.designation = name
                # Copy metadata from one of the inputs if requested.

                # metadata source can be either a string referencing an input
                # or an actual object to copy.
                metadata_source = output.metadata_source
                if metadata_source:
                    if isinstance( metadata_source, basestring ):
                        metadata_source = inp_data[metadata_source]

                if metadata_source is not None:
                    data.init_meta( copy_from=metadata_source )
                else:
                    data.init_meta()
                # Take dbkey from LAST input
                data.dbkey = str(input_dbkey)
                # Set state
                # FIXME: shouldn't this be NEW until the job runner changes it?
                data.state = data.states.QUEUED
                data.blurb = "queued"
                # Set output label
                data.name = self.get_output_name( output, data, tool, on_text, trans, incoming, history, wrapped_params.params, job_params )
                # Store output
                out_data[ name ] = data
                if output.actions:
                    #Apply pre-job tool-output-dataset actions; e.g. setting metadata, changing format
                    output_action_params = dict( out_data )
                    output_action_params.update( incoming )
                    output.actions.apply_action( data, output_action_params )
                # Store all changes to database
                trans.sa_session.flush()
                return data

            # Keep track of parent / child relationships, we'll create all the
            # datasets first, then create the associations
            parent_to_child_pairs = []
            child_dataset_names = set()
            object_store_populator = ObjectStorePopulator( trans.app )

            for name, output in tool.outputs.items():
                if not filter_output(output, incoming):
                    if output.collection:
                        collections_manager = trans.app.dataset_collections_service

                        # As far as I can tell - this is always true - but just verify
                        assert set_output_history, "Cannot create dataset collection for this kind of tool."

                        elements = odict()
                        input_collections = dict( [ (k, v[0]) for k, v in inp_dataset_collections.iteritems() ] )
                        known_outputs = output.known_outputs( input_collections, collections_manager.type_registry )
                        # Just to echo TODO elsewhere - this should be restructured to allow
                        # nested collections.
                        for output_part_def in known_outputs:
                            effective_output_name = output_part_def.effective_output_name
                            element = handle_output( effective_output_name, output_part_def.output_def )
                            # Following hack causes dataset to no be added to history...
                            child_dataset_names.add( effective_output_name )

                            if set_output_history:
                                history.add_dataset( element, set_hid=set_output_hid )
                            trans.sa_session.add( element )
                            trans.sa_session.flush()

                            elements[ output_part_def.element_identifier ] = element

                        if output.dynamic_structure:
                            assert not elements  # known_outputs must have been empty
                            elements = collections_manager.ELEMENTS_UNINITIALIZED

                        if mapping_over_collection:
                            dc = collections_manager.create_dataset_collection(
                                trans,
                                collection_type=output.structure.collection_type,
                                elements=elements,
                            )
                            out_collections[ name ] = dc
                        else:
                            hdca_name = self.get_output_name( output, None, tool, on_text, trans, incoming, history, wrapped_params.params, job_params )
                            hdca = collections_manager.create(
                                trans,
                                history,
                                name=hdca_name,
                                collection_type=output.structure.collection_type,
                                elements=elements,
                            )
                            # name here is name of the output element - not name
                            # of the hdca.
                            out_collection_instances[ name ] = hdca
                    else:
                        handle_output( name, output )

            # Add all the top-level (non-child) datasets to the history unless otherwise specified
            for name in out_data.keys():
                if name not in child_dataset_names and name not in incoming:  # don't add children; or already existing datasets, i.e. async created
                    data = out_data[ name ]
                    if set_output_history:
                        history.add_dataset( data, set_hid=set_output_hid )
                    trans.sa_session.add( data )
                    trans.sa_session.flush()
            # Add all the children to their parents
            for parent_name, child_name in parent_to_child_pairs:
                parent_dataset = out_data[ parent_name ]
                child_dataset = out_data[ child_name ]
                parent_dataset.children.append( child_dataset )
####################################################################################################
        # Store data after custom code runs
        trans.sa_session.flush()
        # Create the job object
        job = trans.app.model.Job()

        if hasattr( trans, "get_galaxy_session" ):
            galaxy_session = trans.get_galaxy_session()
            # If we're submitting from the API, there won't be a session.
            if type( galaxy_session ) == trans.model.GalaxySession:
                job.session_id = galaxy_session.id
        if trans.user is not None:
            job.user_id = trans.user.id
        job.history_id = history.id
        job.tool_id = tool.id
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except:
            job.tool_version = "1.0.0"
        # FIXME: Don't need all of incoming here, just the defined parameters
        #        from the tool. We need to deal with tools that pass all post
        #        parameters to the command as a special case.
        for name, ( dataset_collection, reduced ) in inp_dataset_collections.iteritems():
            # TODO: Does this work if nested in repeat/conditional?
            if reduced:
                incoming[ name ] = "__collection_reduce__|%s" % dataset_collection.id
            # Should verify security? We check security of individual
            # datasets below?
            job.add_input_dataset_collection( name, dataset_collection )
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        current_user_roles = trans.get_current_user_roles()
        for name, dataset in inp_data.iteritems():
            if dataset:
                if not trans.app.security_agent.can_access_dataset( current_user_roles, dataset.dataset ):
                    raise "User does not have permission to use a dataset (%s) provided for input." % data.id
                job.add_input_dataset( name, dataset )
            else:
                job.add_input_dataset( name, None )

        if not cache_hit:
            for name, dataset in out_data.iteritems():
                job.add_output_dataset( name, dataset )
            for name, dataset_collection in out_collections.iteritems():
                job.add_implicit_output_dataset_collection( name, dataset_collection )
            for name, dataset_collection_instance in out_collection_instances.iteritems():
                job.add_output_dataset_collection( name, dataset_collection_instance )
            job.object_store_id = object_store_populator.object_store_id
            if job_params:
                job.params = dumps( job_params )
            cached = CachedJob(tool.id, tool.version, job=job)
            cached.add_inputs(inp_hs)
            cached.add_parameters(inc_hs)
            cached.add_outputs(out_data)
            trans.sa_session.add( cached )
        else:
            job.caching_details = cache_hit
            for out_ds in cache_hit.base_job.get_output_datasets():
                # copy dataset and set history
                hda = out_ds.dataset.copy(copy_children=True)
                # get rid of source tracking, we're pretending this has run
                hda.copied_from_history_dataset_association = None
                hda.copied_from_library_dataset_dataset_association = None
                # ensure that it hasn't
                hda.mark_undeleted(include_children=True)
                # relabel based on current history
                hda.name = self._get_default_data_name( hda, tool, on_text=on_text, trans=trans, incoming=incoming, history=history, params=wrapped_params.params, job_params=job_params )
                # set state (does this actually need to be done?)
                hda.state = data.states.QUEUED
                if set_output_history and not tool.outputs[out_ds.name].parent:
                    history.add_dataset(hda, set_hid=True)
                trans.sa_session.add(hda)
                trans.sa_session.flush()
                out_data[out_ds.name] = hda
                job.add_output_dataset(out_ds.name, hda)
        job.set_handler(tool.get_job_handler(job_params))
        trans.sa_session.add( job )

###################################################################################################
        # Now that we have a job id, we can remap any outputs if this is a rerun and the user chose to continue dependent jobs
        # This functionality requires tracking jobs in the database.
        if trans.app.config.track_jobs_in_database and rerun_remap_job_id is not None:
            try:
                old_job = trans.sa_session.query( trans.app.model.Job ).get(rerun_remap_job_id)
                assert old_job is not None, '(%s/%s): Old job id is invalid' % (rerun_remap_job_id, job.id)
                assert old_job.tool_id == job.tool_id, '(%s/%s): Old tool id (%s) does not match rerun tool id (%s)' % (old_job.id, job.id, old_job.tool_id, job.tool_id)
                if trans.user is not None:
                    assert old_job.user_id == trans.user.id, '(%s/%s): Old user id (%s) does not match rerun user id (%s)' % (old_job.id, job.id, old_job.user_id, trans.user.id)
                elif trans.user is None and type( galaxy_session ) == trans.model.GalaxySession:
                    assert old_job.session_id == galaxy_session.id, '(%s/%s): Old session id (%s) does not match rerun session id (%s)' % (old_job.id, job.id, old_job.session_id, galaxy_session.id)
                else:
                    raise Exception('(%s/%s): Remapping via the API is not (yet) supported' % (old_job.id, job.id))
                for jtod in old_job.output_datasets:
                    for (job_to_remap, jtid) in [(jtid.job, jtid) for jtid in jtod.dataset.dependent_jobs]:
                        if (trans.user is not None and job_to_remap.user_id == trans.user.id) or (trans.user is None and job_to_remap.session_id == galaxy_session.id):
                            if job_to_remap.state == job_to_remap.states.PAUSED:
                                job_to_remap.state = job_to_remap.states.NEW
                            for hda in [ dep_jtod.dataset for dep_jtod in job_to_remap.output_datasets ]:
                                if hda.state == hda.states.PAUSED:
                                    hda.state = hda.states.NEW
                                    hda.info = None
                            for p in job_to_remap.parameters:
                                if p.name == jtid.name and p.value == str(jtod.dataset.id):
                                    p.value = str(out_data[jtod.name].id)
                            jtid.dataset = out_data[jtod.name]
                            jtid.dataset.hid = jtod.dataset.hid
                            log.info('Job %s input HDA %s remapped to new HDA %s' % (job_to_remap.id, jtod.dataset.id, jtid.dataset.id))
                            trans.sa_session.add(job_to_remap)
                            trans.sa_session.add(jtid)
                    jtod.dataset.visible = False
                    trans.sa_session.add(jtod)
            except Exception, e:
                log.exception('Cannot remap rerun dependencies.')
        trans.sa_session.flush()
        # Some tools are not really executable, but jobs are still created for them ( for record keeping ).
        # Examples include tools that redirect to other applications ( epigraph ).  These special tools must
        # include something that can be retrieved from the params ( e.g., REDIRECT_URL ) to keep the job
        # from being queued.
        if 'REDIRECT_URL' in incoming:
            # Get the dataset - there should only be 1
            for name in inp_data.keys():
                dataset = inp_data[ name ]
            redirect_url = tool.parse_redirect_url( dataset, incoming )
            # GALAXY_URL should be include in the tool params to enable the external application
            # to send back to the current Galaxy instance
            GALAXY_URL = incoming.get( 'GALAXY_URL', None )
            assert GALAXY_URL is not None, "GALAXY_URL parameter missing in tool config."
            redirect_url += "&GALAXY_URL=%s" % GALAXY_URL
            # Job should not be queued, so set state to ok
            job.set_state( trans.app.model.Job.states.OK )
            job.info = "Redirected to: %s" % redirect_url
            trans.sa_session.add( job )
            trans.sa_session.flush()
            trans.response.send_redirect( url_for( controller='tool_runner', action='redirect', redirect_url=redirect_url ) )
        else:
            # Put the job in the queue if tracking in memory
            trans.app.job_queue.put( job.id, job.tool_id )
            trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
            return job, out_data

    def get_output_name( self, output, dataset, tool, on_text, trans, incoming, history, params, job_params ):
        if output.label:
            params['tool'] = tool
            params['on_string'] = on_text
            return fill_template( output.label, context=params )
        else:
            return self._get_default_data_name( dataset, tool, on_text=on_text, trans=trans, incoming=incoming, history=history, params=params, job_params=job_params )

    def _collapse_inputs( self, tool, inp_data ):
        # find and collapse multiple inputs: EXPERIMENTAL
        # TODO: Find better way to do this
        inp_with_multi = [name for name, param in tool.inputs.iteritems()
                            if isinstance(param, DataToolParameter) and param.multiple]
        # possibly make copy of inp_data and pop items, to speed up processing?
        collapsed_inp = dict()
        remaining_inputs = inp_data.copy()
            # check if the input dataset name starts with the multi string
            # tool duplicates, puts 'ds1' into dict as 'ds' as well.
            # Does this conflict with anything else?
            # Other option is use a set? Do any tools repeat the same thing
            # as a param for the one param?
        for inp in inp_with_multi:
            for name, val in remaining_inputs.items():
                if name.startswith(inp) and name != inp:
                    collapsed_inp.setdefault(inp, []).append(val)
                    del remaining_inputs[name]
        for name, val in remaining_inputs.iteritems():
            if name not in collapsed_inp:
                collapsed_inp[name] = val
        return collapsed_inp

