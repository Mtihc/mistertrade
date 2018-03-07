import collections


def table_str(*data, **kwargs):
    """Prints a list of dicts as a table. 

    Positional arguments:
        data        -- the table data, a list of dict objects

    Keyword arguments:
        columns     -- a dict of column options

    Returns:
        the string representation of the data
    """

    if len(data) == 1:
        if isinstance(data[0], list) or isinstance(data[0], tuple):
            # use the first and only argument if it's a list or tuple
            data = data[0]
 
    # validate columns parameter
    columns = kwargs.get('columns')
    if columns is None:
        # when columns parameter is not specified,
        # set empty defaults for all keys.
        all_keys = set([key for item in data for key in item.keys()])
        columns = { key: {} for key in all_keys }
        del all_keys

    # merge columns defaults
    for key in columns:
        column = columns[key]
        column.setdefault('key', key)
        column.setdefault('title', key.replace('_', ' '))
        column.setdefault('align', '<')
        column.setdefault('format', '')

        if 'width' not in column:
            width = 0
            for item in data:
                value = item.get(key)
                width = max(width, len(format(value, column['format'])))
            width = max(width, len(column['title']))
            column['width'] = width
            del width

    # sort columns by title
    sort = lambda t: t[1].get('order', t[1]['title'])
    columns = collections.OrderedDict(sorted(columns.items(), key=sort))

    # build header and row_format
    header = ""
    row_format = ""
    for key in columns:
        header += "{title:{align}{width}} ".format(**columns[key])
        row_format += "{{{key}:{align}{width}{format}}} ".format(**columns[key])


    # build the string
    result = ""
    result += header + '\n'
    for item in data:
        result += row_format.format(**item) + '\n'

    return result
