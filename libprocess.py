import gdb
import re
import itertools

class ansi:
    VIOLET = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'

    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    CLEAR = '\033[0m'

def red(s):
    return '\033[91m' + str(s) + '\033[0m'

def blue(s):
    return ansi.BLUE + str(s) + ansi.CLEAR

def yellow(s):
    return ansi.YELLOW + str(s) + ansi.CLEAR

def bold(s):
    return ansi.BOLD + str(s) + ansi.CLEAR




class ProcessCommand(gdb.Command):
  def __init__(self):
      super(ProcessCommand, self).__init__("process", gdb.COMMAND_STATUS)

  def invoke(self, arg, from_tty):
      print(bold("listing processes..."))

# heavy inspiration for the processmanager-printer from the sourceware stl printers

# Starting with the type ORIG, search for the member type NAME.  This
# handles searching upward through superclasses.  This is needed to
# work around http://sourceware.org/bugzilla/show_bug.cgi?id=13615.
def find_type(orig, name):
    typ = orig.strip_typedefs()
    while True:
        # Strip cv-qualifiers.  PR 67440.
        search = '%s::%s' % (typ.unqualified(), name)
        try:
            return gdb.lookup_type(search)
        except RuntimeError:
            pass
        # The type was not found, so try the superclass.  We only need
        # to check the first superclass, so we don't bother with
        # anything fancier here.
        field = typ.fields()[0]
        if not field.is_base_class:
            raise ValueError("Cannot find type %s::%s" % (str(orig), name))
        typ = field.type

class StoutHashmapIterator():
    def __init__(self, hash):
        self.node = hash['_M_before_begin']['_M_nxt']
        self.node_type = find_type(hash.type, '__node_type').pointer()

    def __iter__ (self):
        return self

    def __next__ (self):
        if self.node == 0:
            raise StopIteration
        elt = self.node.cast(self.node_type).dereference()
        self.node = elt['_M_nxt']
        valptr = elt['_M_storage'].address
        valptr = valptr.cast(elt.type.template_argument(0).pointer())
        return valptr.dereference()

class ProcessManagerPrinter:
    "Print a hashmap"

    def __init__ (self, val):
        self.manager = val
        self.val = val["processes"]["_M_h"]

    def __iter__(self):
        return StoutHashmapIterator(self.val)

    def to_string (self):
        res = blue('ProcessManager') + ' with ' + bold(str(self.val['_M_element_count'])) + ' running processes\n'
        for kv in self:
            res += " - {} at {}\n".format(yellow(kv['first']), kv['second'])
        return res 


class UpidPrinter():
  def __init__(self, val):
    self._val = val

  def to_string(self):
    return self.brief_string() # + @...

  def brief_string(self):
    return str(self._val["id"]["id"]["_M_ptr"].dereference())

class ProcessPrinter():
  def __init__(self, val):
    self._val = val

  def to_string(self):
    res = "\nProcess " + yellow(UpidPrinter(self._val["pid"]).brief_string())
    if self._val["manage"]:
      res += " (managed)"
    else:
      res += " (not managed)"
    res += "\n"

    res += bold("State: ") + str(self._val["state"]["_M_i"])

    return res


def process_lookup_function(val):
    lookup_tag = val.type.tag

    if lookup_tag == "process::ProcessBase":
        return ProcessPrinter(val)
    elif lookup_tag == "process::ProcessManager":
        return ProcessManagerPrinter(val)
    #elif lookup_tag == "process::UPID" or re.match("^PID<.*>$", lookup_tag):
    #    return UpidPrinter(val)

    return None

gdb.current_progspace().pretty_printers.insert(0, process_lookup_function)
  

#ProcessCommand()
