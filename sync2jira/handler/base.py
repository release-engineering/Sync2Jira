import logging

# Local Modules
import sync2jira.handler.github as gh
import sync2jira.handler.gitlab as gl

log = logging.getLogger("sync2jira")


def get_handler_for(suffix, topic, idx):
    """
    Function to check if a handler for given suffix is configured
    :param String suffix: Incoming suffix
    :param String topic: Topic of incoming message
    :param String idx: Id of incoming message
    :returns: Handler function if configured for suffix. Otherwise None.
    """
    if suffix.startswith("github"):
        return gh.get_handler_for(suffix, topic, idx)
    elif suffix.startswith("gitlab"):
        return gl.get_handler_for(suffix, topic, idx)
    log.info("Unsupported datasource %r", suffix)
    return None
