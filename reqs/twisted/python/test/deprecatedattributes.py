# Import reflect first, so that circular imports (between deprecate and
# reflect) don't cause headaches.
import reqs.twisted.python.reflect
from reqs.twisted.python.versions import Version
from reqs.twisted.python.deprecate import deprecatedModuleAttribute


# Known module-level attributes.
DEPRECATED_ATTRIBUTE = 42
ANOTHER_ATTRIBUTE = 'hello'


version = Version('Twisted', 8, 0, 0)
message = 'Oh noes!'


deprecatedModuleAttribute(
    version,
    message,
    __name__,
    'DEPRECATED_ATTRIBUTE')
