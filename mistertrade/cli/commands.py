import re

_command_name_pattern = re.compile("^[a-z0-9-]{3,}$")

class _Command(object):
  """ This class is used internally by the @command decorator to store command information on a method."""
  def __init__(self, name, kwargs, arguments):
    if not isinstance(name, str):
      raise TypeError("Parameter 'name' is invalid. Expected a str instead of {got_type}.".format(got_type=type(name).__name__))
    if not isinstance(kwargs, dict):
      raise TypeError("Parameter 'kwargs' is invalid. Expected a dict instead of {got_type}.".format(got_type=type(kwargs).__name__))
    if not isinstance(arguments, list):
      raise TypeError("Parameter 'arguments' is invalid. Expected a list instead of {got_type}.".format(got_type=type(arguments).__name__))
    if not _command_name_pattern.match(name):
      raise ValueError("Invalid command name '{name}'. Wrong format.".format(name=name))
    self.name = name
    self.kwargs = kwargs
    self.arguments = arguments

  def __call__(self, target, *args, **kwargs):
    method_name = self.name.lower().replace('-', '_')
    method = getattr(target, method_name, None)
    if not method:
      raise AttributeError("Can't call command '{name}'. Method {method_name} does not exist on {cls}.".format(name=self.name, method_name=method_name, cls=type(target).__name__))
    if not callable(method):
      raise TypeError("Can't call command '{name}'. Attribute {method_name} on {cls} is not a method.".format(name=self.name, method_name=method_name, cls=type(target).__name__))
    return method(*args, **kwargs)

def argument(*args, **kwargs):
  """Convenience function to properly format arguments to pass to the
  command decorator.
  """
  return ([*args], kwargs)

def command(*args, name=None, **kwargs):
  """Add this decorator to a method to expose it to the commands function.
  """

  def decorator(func):    
    # validate func parameter
    if not func or not callable(func):
      raise TypeError("Decorator @{} should be added to a method instead of {}.".format(command.__name__, type(func).__name__))

    # convert arguments tuple to list
    arguments = [*args] if args else []

    # set default name
    if not name:
      command_name = func.__name__.lower().replace('_', '-')
    else:
      command_name = name

    # set default description
    kwargs.setdefault('description', func.__doc__)

    # store the command on the function
    func.__command__ = _Command(command_name, kwargs, arguments)
    
    return func

  return decorator

def getcommand(cls, name):
  """Get a command by name, given the class and the command name."""

  # validate parameters
  if not isinstance(cls, type):
    raise TypeError("Parameter 'cls' should be a class instead of {}.".format(type(cls).__name__))
  if not isinstance(name, str):
    raise TypeError("Parameter 'name' should be a str instead of {}.".format(type(name).__name__))
  
  # derive method name
  method_name = name.lower().replace('-', '_')

  # find the command (also look in base classes)
  for base in [cls] + [*cls.__bases__]:
    try:
      return getattr(getattr(base, method_name), '__command__')
    except AttributeError:
      pass
  return None

def _getcommands(cls, *names):
  """Returns all the methods that have the @command decorator."""
  
  member_names = dir(cls)
  # klass = cls if instance(cls, type) else cls.__class__
  # for base in klass.__bases__:
  #   member_names += dir(base)
  # member_names = set(member_names)

  for name in member_names:
    try:
      cmd = getcommand(cls, name)
      if cmd and (not names or cmd.name in names):
        yield cmd
    except (ValueError, AttributeError):
      continue

def getcommands(cls, *names):
  return list(_getcommands(cls, *names))
