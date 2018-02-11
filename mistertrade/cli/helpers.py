import functools
import collections
import yaml

def table_str(*dicts, columns=None):

  # allow a single dict or a collection of dicts
  if len(dicts) == 1:
    if isinstance(dicts[0], dict):
      if columns is not None: raise ValueError("Parameter columns should be None when parameter dicts is a single dict.")
      # simply use yaml.dump when it's a single dict
      return yaml.dump(dicts[0], default_flow_style=True)
    elif isinstance(dicts[0], collections.Iterable):
      # use the first and only argument if it's a collection
      dicts = dicts[0]
  # check if dicts is a collection of dict objects
  if not isinstance(dicts, collections.Iterable) or any(not isinstance(dicts_item, dict) for dicts_item in dicts):
    raise TypeError("Parameter dicts should be a list of dict object.")

  # get a set of all keys in the dictionaries
  keys = set([key for item in dicts for key in item.keys()])

  # validate columns parameter
  if columns:
    if not isinstance(columns, dict):
      raise TypeError("Parameter columns should be a dict or None.")
    # columns shouldn't contain non-existing keys
    invalid_columns = set(columns.keys()).difference(keys)
    if invalid_columns: raise ValueError("Invalid columns. Keys don't exist: " + ','.join(invalid_columns) + "." + ("Valid keys are {}.".format(",".join(keys)) if keys else ''))
  else:
    # set empty defaults for all keys when columns parameter is not specified
    columns = {key: {} for key in keys}

  # merge columns with default values
  for key in columns:
    column = columns[key]
    column['key'] = key
    if 'title' not in column: column['title'] = key.replace('_', ' ')
    if 'align' not in column: column['align'] = '<'
    if 'format' not in column: column['format'] = ''
    if 'width' not in column:
      column['width'] = functools.reduce(lambda x,y: max(x, y), [len(format(item.get(key), column['format'])) for item in dicts] + [len(column['title'])])

  # sort columns by title
  columns = collections.OrderedDict(sorted(columns.items(), key=lambda t: t[1]['title']))

  # build header and row_format
  header = ""
  row_format = ""
  for key in columns:
    header += "{title:{align}{width}} ".format(**columns[key])
    row_format += "{{{key}:{align}{width}{format}}} ".format(**columns[key])

  # build the string
  result = ""
  result += header + '\n'
  for item in dicts:
    item = {key: (item[key] if not item[key] or not callable(item[key]) else item[key](item)) for key in item}
    result += row_format.format(**item) + '\n'

  return result

