"""
Helper functions for converting to and from hstore compatible
representations of data.
"""

import galaxy.model

def hstorify_dict(in_dict):
    """
    Returns a dictionary made safe for storage in hstore, ie both keys and
    values are strings.
    Does this in a Python 2.6 compatible manner.
    """
    return dict((str(k), hstore_stringify(v)) for k, v in in_dict.iteritems())

def hstore_stringify(obj, sort_lists=True):
    """
    Returns a string representation of the input object, ordered in a
    deterministic fashion, suitable for hstore comparison.
    Acts recursively for container objects (iterables and dicts).
    """
    # TODO: Investigate alternatives for stringifying; json.dumps conflicts
    # with postgresql quoting, escape characters multiply like rabbits.
    if isinstance(obj, basestring):
        return str(obj)
    if isinstance(obj, galaxy.model.DatasetInstance):
        return "dataset_%i" % obj.dataset_id
    if isinstance(obj, dict):
        # TODO: Investigate better alternatives for this
        return str(dict((str(k), hstore_stringify(v)) for k, v in sorted(obj.items())))
    # return to EAFP to check for iterable
    try:
        hs_seq_obj = [hstore_stringify(v) for v in obj]
    except TypeError:
        return str(obj)
    try:
        if sort_lists:
            hs_seq_obj.sort()
    except AttributeError:
        pass
    return str(hs_seq_obj)
